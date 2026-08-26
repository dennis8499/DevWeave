from __future__ import annotations

import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.codex_doctor import CodexDoctor
from devweave_v2.mcp_tools import AGENT_TOOLS
from devweave_v2.redaction import bounded_text


APPROVAL_METHODS = {
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
}
MAX_LINE_BYTES = 1_000_000
MAX_TRANSCRIPT_BYTES = 10_000_000
MAX_STDERR_BYTES = 262_144
LIVE_OPT_IN = "DEVWEAVE_E2E_ALLOW_LIVE"
CODEX_PATH_SETTING = "DEVWEAVE_CODEX_PATH"
SENTINEL_NAME = "DEVWEAVE_E2E_MUST_NOT_EXIST.txt"
WRITE_PROBE_COMMAND = (
    "python -c \"from pathlib import Path; "
    f"Path('{SENTINEL_NAME}').write_text('unsafe')\""
)
LIVE_OPERATION_BUDGET_SECONDS = 135
LIVE_CLEANUP_TIMEOUT_SECONDS = 20


def require_codex_path() -> Path:
    configured = os.environ.get(CODEX_PATH_SETTING)
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            raise RuntimeError(f"BLOCKED_LIVE_CODEX: {CODEX_PATH_SETTING} must be absolute")
        resolved = candidate.resolve()
    else:
        discovered = shutil.which("codex")
        if not discovered:
            raise RuntimeError(
                f"BLOCKED_LIVE_CODEX: set {CODEX_PATH_SETTING} to an explicit Codex executable or expose codex on PATH"
            )
        resolved = Path(discovered).resolve()
    if not resolved.is_file():
        raise RuntimeError("BLOCKED_LIVE_CODEX: configured Codex executable is not a file")
    return resolved


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True,
        text=True, encoding="utf-8", shell=False,
    )
    return result.stdout


class JsonlAppServer:
    def __init__(self, executable: Path) -> None:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            [str(executable), "app-server"], cwd=ROOT, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
            creationflags=flags,
        )
        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            raise RuntimeError("BLOCKED_LIVE_CODEX: app-server stdio pipes are unavailable")
        self.inbox: queue.Queue[dict[str, Any] | BaseException | None] = queue.Queue()
        self.messages: list[dict[str, Any]] = []
        self.approvals: list[dict[str, Any]] = []
        self.defer_approvals = False
        self.stderr = bytearray()
        self.total_bytes = 0
        self.next_id = 1
        self.write_lock = threading.Lock()
        self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self.stdout_thread.start()
        self.stderr_thread.start()

    def initialize(self, *, timeout: float = 30) -> dict[str, Any]:
        result = self.request("initialize", {
            "clientInfo": {"name": "devweave_e2e", "title": "DevWeave E2E", "version": "2.0.0"},
            "capabilities": {"experimentalApi": False},
        }, timeout=timeout)
        self.send({"method": "initialized", "params": {}})
        return result

    def request(self, method: str, params: Any, *, timeout: float = 120) -> dict[str, Any]:
        request_id = self.begin_request(method, params)
        return self.complete_request(request_id, method, timeout=timeout)

    def begin_request(self, method: str, params: Any) -> int:
        request_id = self.next_id
        self.next_id += 1
        self.send({"id": request_id, "method": method, "params": params})
        return request_id

    def complete_request(self, request_id: int, method: str, *, timeout: float = 120) -> dict[str, Any]:
        response = self.wait_for(
            lambda item: item.get("id") == request_id and "method" not in item,
            timeout=timeout,
        )
        if isinstance(response.get("error"), dict):
            error = response["error"]
            raise RuntimeError(f"app-server {method} failed: {error.get('code')} {error.get('message')}")
        result = response.get("result")
        if not isinstance(result, dict):
            return {}
        return result

    def wait_for(
        self,
        predicate: Callable[[dict[str, Any]], bool],
        *,
        timeout: float,
        after: int = 0,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        checked = after
        while True:
            while checked < len(self.messages):
                item = self.messages[checked]
                checked += 1
                if predicate(item):
                    return item
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("app-server response/event timed out")
            try:
                item = self.inbox.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError("app-server response/event timed out") from exc
            if isinstance(item, BaseException):
                raise RuntimeError(f"app-server transport failed: {item}") from item
            if item is None:
                stderr = bytes(self.stderr).decode("utf-8", errors="replace")[-4_096:]
                raise RuntimeError(f"app-server exited before the expected event: {stderr}")
            self.messages.append(item)
            self._handle_server_request(item)

    def send(self, value: dict[str, Any]) -> None:
        encoded = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > MAX_LINE_BYTES:
            raise RuntimeError("outbound app-server frame exceeds its bound")
        with self.write_lock:
            if self.process.stdin is None or self.process.stdin.closed:
                raise RuntimeError("app-server stdin is closed")
            self.process.stdin.write(encoded)
            self.process.stdin.flush()

    def close(self) -> None:
        try:
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
            self.process.wait(timeout=5)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        finally:
            self.stdout_thread.join(timeout=2)
            self.stderr_thread.join(timeout=2)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        try:
            while True:
                raw = self.process.stdout.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    self.inbox.put(None)
                    return
                if len(raw) > MAX_LINE_BYTES or not raw.endswith(b"\n"):
                    raise RuntimeError("inbound app-server frame exceeds its bound")
                self.total_bytes += len(raw)
                if self.total_bytes > MAX_TRANSCRIPT_BYTES:
                    raise RuntimeError("aggregate app-server transcript exceeds its bound")
                value = json.loads(raw.decode("utf-8"))
                if not isinstance(value, dict):
                    raise RuntimeError("app-server message is not an object")
                self.inbox.put(value)
        except BaseException as exc:
            self.inbox.put(exc)

    def _read_stderr(self) -> None:
        assert self.process.stderr is not None
        while len(self.stderr) < MAX_STDERR_BYTES:
            chunk = self.process.stderr.read(min(8_192, MAX_STDERR_BYTES - len(self.stderr)))
            if not chunk:
                return
            self.stderr.extend(chunk)

    def _handle_server_request(self, item: dict[str, Any]) -> None:
        method = item.get("method")
        if "id" not in item or not isinstance(method, str):
            return
        if method not in APPROVAL_METHODS:
            self.send({"id": item["id"], "error": {"code": -32601, "message": "Unsupported server request"}})
            raise RuntimeError(f"unexpected app-server request: {method}")
        self.approvals.append(item)
        if self.defer_approvals:
            return
        self.send({"id": item["id"], "result": {"decision": "decline"}})


def nested_id(value: dict[str, Any], key: str) -> str:
    nested = value.get(key)
    if isinstance(nested, dict) and isinstance(nested.get("id"), str):
        return nested["id"]
    return ""


def turn_completed(turn_id: str) -> Callable[[dict[str, Any]], bool]:
    def matches(item: dict[str, Any]) -> bool:
        params = item.get("params")
        return (
            item.get("method") == "turn/completed"
            and isinstance(params, dict)
            and nested_id(params, "turn") == turn_id
        )
    return matches


def protocol_diagnostic(messages: list[dict[str, Any]]) -> str:
    methods: dict[str, int] = {}
    item_types: dict[str, int] = {}
    turn_statuses: list[str] = []
    errors: list[dict[str, Any]] = []
    agent_messages: list[str] = []
    for message in messages:
        method = message.get("method")
        if isinstance(method, str):
            methods[method] = methods.get(method, 0) + 1
        params = message.get("params")
        if not isinstance(params, dict):
            continue
        item = params.get("item")
        if isinstance(item, dict) and isinstance(item.get("type"), str):
            item_type = item["type"]
            item_types[item_type] = item_types.get(item_type, 0) + 1
            if method == "item/completed" and item_type == "agentMessage" and len(agent_messages) < 4:
                for key in ("text", "content", "output", "message"):
                    if isinstance(item.get(key), str):
                        agent_messages.append(bounded_text(item[key], max_bytes=512)[0])
                        break
        if method == "turn/completed" and isinstance(params.get("turn"), dict):
            status = params["turn"].get("status")
            if isinstance(status, str):
                turn_statuses.append(status)
        if method in {"error", "warning", "configWarning"} and len(errors) < 12:
            diagnostic: dict[str, Any] = {"method": method}
            containers = (("", params), ("error_", params.get("error")))
            for prefix, container in containers:
                if not isinstance(container, dict):
                    continue
                for key in ("code", "message", "willRetry", "retryAfterMs"):
                    value = container.get(key)
                    if isinstance(value, str):
                        diagnostic[prefix + key] = bounded_text(value, max_bytes=512)[0]
                    elif isinstance(value, (bool, int, float)):
                        diagnostic[prefix + key] = value
            errors.append(diagnostic)
    return json.dumps(
        {
            "methods": methods,
            "item_types": item_types,
            "turn_statuses": turn_statuses[-8:],
            "errors": errors,
            "agent_messages": agent_messages,
        },
        ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    )[:4_096]


def report_phase(phase: str) -> str:
    print(
        json.dumps({"live_e2e_phase": phase}, sort_keys=True, separators=(",", ":")),
        file=sys.stderr,
        flush=True,
    )
    return phase


def operation_timeout(deadline: float, requested: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("live E2E global operation deadline exhausted")
    return min(requested, remaining)


class RealCodexAppServerTests(unittest.TestCase):
    def test_real_stdio_mcp_lifecycle_approval_and_detached_review(self) -> None:
        if os.environ.get(LIVE_OPT_IN) != "1":
            self.fail(f"BLOCKED_LIVE_CODEX: set {LIVE_OPT_IN}=1 only for an explicitly approved live certification run")
        if os.name != "nt":
            self.fail("BLOCKED_LIVE_CODEX: V2 live certification is Windows x64 only")
        codex = require_codex_path()
        before_status = git_output("status", "--porcelain=v1", "--untracked-files=all")
        source_head = git_output("rev-parse", "HEAD").strip()
        sentinel = ROOT / SENTINEL_NAME
        self.assertFalse(sentinel.exists(), "E2E sentinel already exists")
        deadline = time.monotonic() + LIVE_OPERATION_BUDGET_SECONDS
        doctor = CodexDoctor().probe(repository=ROOT, configured_path=str(codex))
        client = JsonlAppServer(codex)
        thread_id = ""
        summary: dict[str, Any] | None = None
        failure: Exception | None = None
        cleanup_error: Exception | None = None
        sentinel_cleanup_error: Exception | None = None
        unsafe_write = ""
        phase = report_phase("initialize")
        try:
            initialized = client.initialize(timeout=operation_timeout(deadline, 30))
            self.assertIsInstance(initialized.get("userAgent"), str)
            mcp_config = {
                "mcp_servers": {
                    "devweave": {
                        "command": str(Path(sys.executable).resolve()),
                        "args": ["-B", str(SCRIPT_ROOT / "devweave_v2_cli.py"), "--repo", str(ROOT), "mcp-serve"],
                        "required": True,
                        "startup_timeout_sec": 15,
                        "tool_timeout_sec": 360,
                        "enabled_tools": list(AGENT_TOOLS),
                    }
                }
            }
            phase = report_phase("thread_start")
            thread_result = client.request("thread/start", {
                "cwd": str(ROOT), "approvalPolicy": "untrusted", "approvalsReviewer": "user",
                "sandbox": "read-only",
                "ephemeral": False,
                "baseInstructions": "Run only bounded DevWeave protocol certification steps; never retain reasoning or secrets.",
                "config": mcp_config,
            }, timeout=operation_timeout(deadline, 60))
            thread_id = nested_id(thread_result, "thread")
            self.assertTrue(thread_id)
            phase = report_phase("mcp_status")
            status = client.request("mcpServerStatus/list", {
                "threadId": thread_id, "detail": "full", "limit": 100,
            }, timeout=operation_timeout(deadline, 60))
            servers = status.get("data")
            self.assertIsInstance(servers, list)
            devweave = next((item for item in servers if isinstance(item, dict) and item.get("name") == "devweave"), None)
            self.assertIsInstance(devweave, dict)
            self.assertEqual(tuple(sorted(devweave["tools"])), tuple(sorted(AGENT_TOOLS)))

            approval: dict[str, Any] | None = None
            approval_turn_id = ""
            approval_start = 0
            approval_attempts = 0
            for attempt in range(1, 3):
                approval_attempts = attempt
                approval_start = len(client.messages)
                phase = report_phase(f"approval_turn_start_{attempt}")
                approval_turn = client.request("turn/start", {
                    "threadId": thread_id,
                    "input": [{
                        "type": "text",
                        "text": (
                            "This is an authorized bounded approval transport probe. Immediately use the shell tool exactly "
                            f"once with this exact command: {WRITE_PROBE_COMMAND}. "
                            "Do not use another tool and do not reply before making the tool call. "
                            "After the expected denial, reply exactly DEVWEAVE_APPROVAL_DECLINED."
                        ),
                    }],
                    "approvalPolicy": "untrusted",
                    "approvalsReviewer": "user",
                    "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
                }, timeout=operation_timeout(deadline, 60))
                approval_turn_id = nested_id(approval_turn, "turn")
                self.assertTrue(approval_turn_id)
                phase = report_phase(f"approval_wait_{attempt}")
                outcome = client.wait_for(
                    lambda item: item.get("method") in APPROVAL_METHODS or turn_completed(approval_turn_id)(item),
                    timeout=operation_timeout(deadline, 180), after=approval_start,
                )
                if outcome.get("method") in APPROVAL_METHODS:
                    approval = outcome
                    break
            if approval is None:
                raise RuntimeError("bounded approval probe attempts completed without a native approval request")
            self.assertEqual(approval.get("method"), "item/commandExecution/requestApproval")
            phase = report_phase("approval_completion")
            client.wait_for(
                turn_completed(approval_turn_id),
                timeout=operation_timeout(deadline, 180),
                after=approval_start,
            )
            declined_command = False
            for message in client.messages[approval_start:]:
                params = message.get("params")
                item = params.get("item") if isinstance(params, dict) else None
                if (
                    message.get("method") == "item/completed"
                    and isinstance(item, dict)
                    and item.get("type") == "commandExecution"
                    and item.get("status") == "declined"
                ):
                    declined_command = True
            self.assertTrue(declined_command, "declined approval did not produce a declined command item")
            self.assertFalse(sentinel.exists(), "declined approval created the sentinel")

            phase = report_phase("thread_read")
            read = client.request(
                "thread/read",
                {"threadId": thread_id, "includeTurns": True},
                timeout=operation_timeout(deadline, 30),
            )
            self.assertEqual(nested_id(read, "thread"), thread_id)
            phase = report_phase("thread_resume")
            resumed = client.request("thread/resume", {
                "threadId": thread_id, "cwd": str(ROOT), "approvalPolicy": "untrusted",
                "approvalsReviewer": "user",
                "sandbox": "read-only", "config": mcp_config,
            }, timeout=operation_timeout(deadline, 60))
            self.assertEqual(nested_id(resumed, "thread"), thread_id)

            client.defer_approvals = True
            interrupt_start = 0
            interrupt_turn_id = ""
            interrupt_approval: dict[str, Any] | None = None
            interrupt_attempts = 0
            for attempt in range(1, 3):
                interrupt_attempts = attempt
                interrupt_start = len(client.messages)
                phase = report_phase(f"interrupt_turn_start_{attempt}")
                interrupt_turn = client.request("turn/start", {
                    "threadId": thread_id,
                    "input": [{
                        "type": "text",
                        "text": (
                            "This is an authorized bounded interrupt transport probe. Immediately use the shell tool exactly "
                            f"once with this exact command: {WRITE_PROBE_COMMAND}. "
                            "Do not use another tool and do not reply before making the tool call."
                        ),
                    }],
                    "approvalPolicy": "untrusted",
                    "approvalsReviewer": "user",
                    "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
                }, timeout=operation_timeout(deadline, 60))
                interrupt_turn_id = nested_id(interrupt_turn, "turn")
                self.assertTrue(interrupt_turn_id)
                phase = report_phase(f"interrupt_approval_wait_{attempt}")
                outcome = client.wait_for(
                    lambda item: item.get("method") in APPROVAL_METHODS or turn_completed(interrupt_turn_id)(item),
                    timeout=operation_timeout(deadline, 180), after=interrupt_start,
                )
                if outcome.get("method") in APPROVAL_METHODS:
                    interrupt_approval = outcome
                    break
            if interrupt_approval is None:
                raise RuntimeError("bounded interrupt probe attempts completed without a pending approval")
            self.assertEqual(interrupt_approval.get("method"), "item/commandExecution/requestApproval")
            phase = report_phase("steer_interrupt")
            steer_request_id = client.begin_request("turn/steer", {
                "threadId": thread_id, "expectedTurnId": interrupt_turn_id,
                "input": [{"type": "text", "text": "Acknowledge steering, but keep the response pending."}],
            })
            interrupt_request_id = client.begin_request("turn/interrupt", {
                "threadId": thread_id, "turnId": interrupt_turn_id,
            })
            client.complete_request(
                steer_request_id,
                "turn/steer",
                timeout=operation_timeout(deadline, 30),
            )
            client.complete_request(
                interrupt_request_id,
                "turn/interrupt",
                timeout=operation_timeout(deadline, 30),
            )
            interrupted = client.wait_for(
                turn_completed(interrupt_turn_id),
                timeout=operation_timeout(deadline, 60),
                after=interrupt_start,
            )
            client.defer_approvals = False
            self.assertEqual(interrupted["params"]["turn"].get("status"), "interrupted")

            review_start = len(client.messages)
            phase = report_phase("detached_review")
            expected_review = {
                "schema_version": 2,
                "result": "passed",
                "severity": "advisory",
                "source_fingerprint": "e" * 64,
                "round": 1,
                "findings": [],
            }
            review = client.request("review/start", {
                "threadId": thread_id,
                "delivery": "detached",
                "target": {
                    "type": "custom",
                    "instructions": (
                        "This is a bounded protocol certification only. Do not use tools or modify files. "
                        "Return exactly this JSON object with no Markdown fence or prose: "
                        + json.dumps(expected_review, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
                    ),
                },
            }, timeout=operation_timeout(deadline, 60))
            reviewer_thread_id = review.get("reviewThreadId")
            self.assertIsInstance(reviewer_thread_id, str)
            self.assertNotEqual(reviewer_thread_id, thread_id)
            review_turn_id = nested_id(review, "turn")
            self.assertTrue(review_turn_id)
            review_event = client.wait_for(
                lambda item: (
                    (
                        item.get("method") == "item/completed"
                        and isinstance(item.get("params"), dict)
                        and item["params"].get("threadId") == reviewer_thread_id
                        and isinstance(item["params"].get("item"), dict)
                        and item["params"]["item"].get("type") == "exitedReviewMode"
                    )
                    or turn_completed(review_turn_id)(item)
                ),
                timeout=operation_timeout(deadline, 240), after=review_start,
            )
            review_completion = "exitedReviewMode"
            if review_event.get("method") == "item/completed":
                review_text = review_event["params"]["item"].get("review")
                client.wait_for(
                    turn_completed(review_turn_id),
                    timeout=operation_timeout(deadline, 60),
                    after=review_start,
                )
            else:
                self.assertEqual(review_event["params"]["turn"].get("status"), "completed")
                review_completion = "authoritative_agent_message"
                review_text = ""
                for message in client.messages[review_start:]:
                    params = message.get("params")
                    item = params.get("item") if isinstance(params, dict) else None
                    if (
                        message.get("method") == "item/completed"
                        and isinstance(params, dict)
                        and params.get("threadId") == reviewer_thread_id
                        and params.get("turnId") == review_turn_id
                        and isinstance(item, dict)
                        and item.get("type") == "agentMessage"
                    ):
                        for key in ("text", "content", "output", "message"):
                            if isinstance(item.get(key), str):
                                review_text = item[key]
                                break
            self.assertIsInstance(review_text, str)
            self.assertTrue(review_text.strip())
            self.assertEqual(json.loads(review_text.strip()), expected_review)

            turn_status = interrupted["params"]["turn"].get("status")
            summary = {
                "ok": True,
                "schema_version": 2,
                "source_git_head": source_head,
                "codex_version": doctor["codex"]["version"],
                "codex_sha256": hashlib.sha256(codex.read_bytes()).hexdigest(),
                "schema_files": doctor["app_server"]["schema_files"],
                "mcp_tools": list(sorted(AGENT_TOOLS)),
                "approval_method": approval.get("method"),
                "interrupt_status": turn_status,
                "detached_review": True,
                "review_nonempty": True,
                "review_completion": review_completion,
                "review_strict_envelope": True,
                "messages_observed": len(client.messages),
                "approval_policy": "untrusted",
                "approvals_reviewer": "user",
                "approval_attempts": approval_attempts,
                "interrupt_attempts": interrupt_attempts,
            }
        except Exception as exc:
            failure = RuntimeError(
                f"{phase}: {exc}; protocol={protocol_diagnostic(client.messages)}; stderr_bytes={len(client.stderr)}"
            )
        finally:
            if sentinel.exists() or sentinel.is_symlink():
                try:
                    stat = sentinel.lstat()
                    unsafe_write = f"sentinel_created bytes={stat.st_size} symlink={sentinel.is_symlink()}"
                    if sentinel.is_file() or sentinel.is_symlink():
                        sentinel.unlink()
                except Exception as exc:
                    sentinel_cleanup_error = exc
            if thread_id:
                try:
                    client.request(
                        "thread/delete",
                        {"threadId": thread_id},
                        timeout=LIVE_CLEANUP_TIMEOUT_SECONDS,
                    )
                except Exception as exc:
                    cleanup_error = exc
            client.close()
        if failure is not None:
            cleanup = f"; synthetic thread cleanup failed: {cleanup_error}" if cleanup_error is not None else ""
            sentinel_failure = f"; {unsafe_write}" if unsafe_write else ""
            sentinel_cleanup = f"; sentinel cleanup failed: {sentinel_cleanup_error}" if sentinel_cleanup_error else ""
            self.fail(f"BLOCKED_LIVE_CODEX: {failure}{sentinel_failure}{cleanup}{sentinel_cleanup}")
        if unsafe_write:
            self.fail(f"BLOCKED_LIVE_CODEX: native approval was bypassed; {unsafe_write}")
        if sentinel_cleanup_error is not None:
            self.fail(f"BLOCKED_LIVE_CODEX: sentinel cleanup failed: {sentinel_cleanup_error}")
        if cleanup_error is not None:
            self.fail(f"BLOCKED_LIVE_CODEX: synthetic thread cleanup failed: {cleanup_error}")
        if summary is None:
            self.fail("BLOCKED_LIVE_CODEX: live run completed without a bounded summary")
        self.assertEqual(git_output("status", "--porcelain=v1", "--untracked-files=all"), before_status)
        self.assertFalse(sentinel.exists())
        summary["synthetic_thread_deleted"] = True
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()

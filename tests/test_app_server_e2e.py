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


APPROVAL_METHODS = {
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
}
MAX_LINE_BYTES = 1_000_000
MAX_TRANSCRIPT_BYTES = 10_000_000
MAX_STDERR_BYTES = 262_144
LIVE_OPT_IN = "DEVWEAVE_E2E_ALLOW_LIVE"
CODEX_PATH_SETTING = "DEVWEAVE_CODEX_PATH"


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
        self.stderr = bytearray()
        self.total_bytes = 0
        self.next_id = 1
        self.write_lock = threading.Lock()
        self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self.stdout_thread.start()
        self.stderr_thread.start()

    def initialize(self) -> dict[str, Any]:
        result = self.request("initialize", {
            "clientInfo": {"name": "devweave_e2e", "title": "DevWeave E2E", "version": "2.0.0"},
            "capabilities": {"experimentalApi": False},
        }, timeout=30)
        self.send({"method": "initialized", "params": {}})
        return result

    def request(self, method: str, params: Any, *, timeout: float = 120) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self.send({"id": request_id, "method": method, "params": params})
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


class RealCodexAppServerTests(unittest.TestCase):
    def test_real_stdio_mcp_lifecycle_approval_and_detached_review(self) -> None:
        if os.environ.get(LIVE_OPT_IN) != "1":
            self.fail(f"BLOCKED_LIVE_CODEX: set {LIVE_OPT_IN}=1 only for an explicitly approved live certification run")
        if os.name != "nt":
            self.fail("BLOCKED_LIVE_CODEX: V2 live certification is Windows x64 only")
        codex = require_codex_path()
        before_status = git_output("status", "--porcelain=v1", "--untracked-files=all")
        source_head = git_output("rev-parse", "HEAD").strip()
        sentinel = ROOT / "DEVWEAVE_E2E_MUST_NOT_EXIST.txt"
        self.assertFalse(sentinel.exists(), "E2E sentinel already exists")
        doctor = CodexDoctor().probe(repository=ROOT, configured_path=str(codex))
        client = JsonlAppServer(codex)
        thread_id = ""
        summary: dict[str, Any] | None = None
        failure: Exception | None = None
        cleanup_error: Exception | None = None
        try:
            initialized = client.initialize()
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
            thread_result = client.request("thread/start", {
                "cwd": str(ROOT), "approvalPolicy": "on-request", "sandbox": "read-only",
                "ephemeral": False,
                "baseInstructions": "Run only bounded DevWeave protocol certification steps; never retain reasoning or secrets.",
                "config": mcp_config,
            }, timeout=60)
            thread_id = nested_id(thread_result, "thread")
            self.assertTrue(thread_id)
            status = client.request("mcpServerStatus/list", {
                "threadId": thread_id, "detail": "full", "limit": 100,
            }, timeout=60)
            servers = status.get("data")
            self.assertIsInstance(servers, list)
            devweave = next((item for item in servers if isinstance(item, dict) and item.get("name") == "devweave"), None)
            self.assertIsInstance(devweave, dict)
            self.assertEqual(tuple(sorted(devweave["tools"])), tuple(sorted(AGENT_TOOLS)))

            approval_start = len(client.messages)
            approval_turn = client.request("turn/start", {
                "threadId": thread_id,
                "input": [{
                    "type": "text",
                    "text": (
                        "For this approval transport test, attempt exactly one shell command that would create "
                        "DEVWEAVE_E2E_MUST_NOT_EXIST.txt in the repository. Do not use apply_patch. "
                        "After the expected denial, reply exactly DEVWEAVE_APPROVAL_DECLINED."
                    ),
                }],
                "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
            }, timeout=60)
            approval_turn_id = nested_id(approval_turn, "turn")
            self.assertTrue(approval_turn_id)
            approval = client.wait_for(
                lambda item: item.get("method") in APPROVAL_METHODS,
                timeout=180, after=approval_start,
            )
            self.assertIn(approval.get("method"), APPROVAL_METHODS)
            client.wait_for(turn_completed(approval_turn_id), timeout=180, after=approval_start)
            self.assertFalse(sentinel.exists(), "declined approval created the sentinel")

            read = client.request("thread/read", {"threadId": thread_id, "includeTurns": True}, timeout=30)
            self.assertEqual(nested_id(read, "thread"), thread_id)
            resumed = client.request("thread/resume", {
                "threadId": thread_id, "cwd": str(ROOT), "approvalPolicy": "on-request",
                "sandbox": "read-only", "config": mcp_config,
            }, timeout=60)
            self.assertEqual(nested_id(resumed, "thread"), thread_id)

            interrupt_start = len(client.messages)
            interrupt_turn = client.request("turn/start", {
                "threadId": thread_id,
                "input": [{"type": "text", "text": "Begin a long analysis, wait for steering, and do not use tools."}],
                "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
            }, timeout=60)
            interrupt_turn_id = nested_id(interrupt_turn, "turn")
            self.assertTrue(interrupt_turn_id)
            client.request("turn/steer", {
                "threadId": thread_id, "expectedTurnId": interrupt_turn_id,
                "input": [{"type": "text", "text": "Acknowledge steering, but keep the response pending."}],
            }, timeout=30)
            client.request("turn/interrupt", {
                "threadId": thread_id, "turnId": interrupt_turn_id,
            }, timeout=30)
            interrupted = client.wait_for(turn_completed(interrupt_turn_id), timeout=60, after=interrupt_start)

            review_start = len(client.messages)
            review = client.request("review/start", {
                "threadId": thread_id,
                "delivery": "detached",
                "target": {
                    "type": "custom",
                    "instructions": (
                        "This is a bounded protocol certification only. Do not use tools or modify files. "
                        "Return exactly: ADVISORY [DEVWEAVE-E2E] DEVWEAVE_REVIEW_OK"
                    ),
                },
            }, timeout=60)
            reviewer_thread_id = review.get("reviewThreadId")
            self.assertIsInstance(reviewer_thread_id, str)
            self.assertNotEqual(reviewer_thread_id, thread_id)
            review_item = client.wait_for(
                lambda item: (
                    item.get("method") == "item/completed"
                    and isinstance(item.get("params"), dict)
                    and item["params"].get("threadId") == reviewer_thread_id
                    and isinstance(item["params"].get("item"), dict)
                    and item["params"]["item"].get("type") == "exitedReviewMode"
                ),
                timeout=240, after=review_start,
            )
            review_text = review_item["params"]["item"].get("review")
            self.assertIsInstance(review_text, str)
            self.assertTrue(review_text.strip())
            review_turn_id = nested_id(review, "turn")
            if review_turn_id:
                client.wait_for(turn_completed(review_turn_id), timeout=60, after=review_start)

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
                "messages_observed": len(client.messages),
            }
        except Exception as exc:
            failure = exc
        finally:
            if thread_id:
                try:
                    client.request("thread/delete", {"threadId": thread_id}, timeout=30)
                except Exception as exc:
                    cleanup_error = exc
            client.close()
        if failure is not None:
            cleanup = f"; synthetic thread cleanup failed: {cleanup_error}" if cleanup_error is not None else ""
            self.fail(f"BLOCKED_LIVE_CODEX: {failure}{cleanup}")
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

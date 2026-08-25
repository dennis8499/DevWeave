from __future__ import annotations

import hashlib
import hmac
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.codex_doctor import CodexDoctor, REQUIRED_APP_SERVER_DESCRIPTORS
from devweave_v2.errors import DevWeaveError, ErrorCode
from devweave_v2.git_port import GitAdapter
from devweave_v2.git_transaction import GitTransaction
from devweave_v2.host_bridge import HostBridgeSession, run_host_stdio
from devweave_v2.host_operations import HostOperationAdapter
from devweave_v2.run_service import RunService
from devweave_v2.verification_engine import ProcessResult


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
        text=True, encoding="utf-8", shell=False,
    )


class FakeCodexRunner:
    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, *, cwd: Path, timeout_seconds: int) -> ProcessResult:
        self.calls.append(tuple(argv))
        if argv[1:] == ("--version",):
            if self.mode == "version_failure":
                return ProcessResult(1, b"", b"failed", 1, False)
            return ProcessResult(0, b"codex-cli 9.9.9\n", b"", 1, False)
        if self.mode == "schema_failure":
            return ProcessResult(2, b"", b"failed", 1, False)
        output = Path(argv[argv.index("--out") + 1])
        output.mkdir(parents=True, exist_ok=True)
        if self.mode == "malformed_schema":
            (output / "protocol.json").write_text("not-json", encoding="utf-8")
        else:
            descriptors = list(REQUIRED_APP_SERVER_DESCRIPTORS)
            if self.mode == "missing_descriptor":
                descriptors.pop()
            (output / "protocol.json").write_text(json.dumps({"methods": descriptors}), encoding="utf-8")
        return ProcessResult(0, b"", b"", 1, False)


class CodexDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="devweave-v2-doctor-")
        self.repo = Path(self.temp.name)
        self.executable = self.repo / "codex.exe"
        self.executable.write_bytes(b"fake-codex-binary")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_path_and_configured_resolution_record_runtime_provenance(self) -> None:
        runner = FakeCodexRunner()
        from_path = CodexDoctor(runner=runner, which=lambda _: str(self.executable)).probe(repository=self.repo)
        configured = CodexDoctor(runner=runner).probe(repository=self.repo, configured_path=str(self.executable.resolve()))
        self.assertEqual(from_path["codex"]["source"], "path")
        self.assertEqual(configured["codex"]["source"], "configured")
        self.assertEqual(configured["codex"]["sha256"], hashlib.sha256(b"fake-codex-binary").hexdigest())
        self.assertFalse(configured["app_server"]["experimental_api"])
        self.assertTrue(all(call[0] == str(self.executable.resolve()) for call in runner.calls))
        self.assertFalse(any("download" in token or "http" in token for call in runner.calls for token in call))

    def test_missing_nonfile_relative_version_and_schema_fail_closed(self) -> None:
        with self.assertRaises(DevWeaveError) as missing:
            CodexDoctor(which=lambda _: None).probe(repository=self.repo)
        self.assertEqual(missing.exception.code, ErrorCode.CODEX_UNAVAILABLE)
        with self.assertRaises(DevWeaveError):
            CodexDoctor(runner=FakeCodexRunner()).probe(repository=self.repo, configured_path="relative/codex")
        directory = self.repo / "not-a-file"
        directory.mkdir()
        with self.assertRaises(DevWeaveError):
            CodexDoctor(runner=FakeCodexRunner()).probe(repository=self.repo, configured_path=str(directory.resolve()))
        for mode in ("version_failure", "schema_failure", "malformed_schema", "missing_descriptor"):
            with self.subTest(mode):
                with self.assertRaises(DevWeaveError) as failed:
                    CodexDoctor(runner=FakeCodexRunner(mode)).probe(repository=self.repo, configured_path=str(self.executable.resolve()))
                self.assertEqual(failed.exception.code, ErrorCode.CODEX_UNAVAILABLE)


class GitHostHarness:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="devweave-v2-host-git-")
        self.repo = Path(self.temp.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "DevWeave Test")
        git(self.repo, "config", "user.email", "devweave@example.test")
        (self.repo / "README.md").write_text("# fixture\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "base")

    def close(self) -> None:
        self.temp.cleanup()


class ReadyDoctor:
    def probe(self, *, repository: Path, configured_path: str | None = None) -> dict:
        return {"status": "ready", "configured": configured_path is not None}


class HostOperationTests(unittest.TestCase):
    def test_missing_codex_has_zero_run_or_branch_side_effect(self) -> None:
        harness = GitHostHarness()
        try:
            before = git(harness.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            adapter = HostOperationAdapter(harness.repo)
            draft = json.loads((ROOT / "fixtures" / "devweave_v2" / "run-plan-draft.json").read_text(encoding="utf-8"))
            with self.assertRaises(DevWeaveError) as failed:
                adapter.call("run_start", {"draft": draft, "slug": "slice", "codex_path": str((harness.repo / "missing.exe").resolve())})
            self.assertEqual(failed.exception.code, ErrorCode.CODEX_UNAVAILABLE)
            self.assertEqual(git(harness.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), before)
            self.assertFalse((harness.repo / "docs" / "exec-plans").exists())
            self.assertEqual(git(harness.repo, "branch", "--list", "devweave/*").stdout.strip(), "")
        finally:
            harness.close()

    def test_ready_doctor_starts_run_on_owned_branch(self) -> None:
        harness = GitHostHarness()
        try:
            service = RunService(harness.repo, clock=lambda: "2026-08-25T00:00:00Z")
            transaction = GitTransaction(harness.repo, GitAdapter(harness.repo))
            adapter = HostOperationAdapter(harness.repo, service=service, doctor=ReadyDoctor(), git=transaction)
            draft = json.loads((ROOT / "fixtures" / "devweave_v2" / "run-plan-draft.json").read_text(encoding="utf-8"))
            result = adapter.call("run_start", {"draft": draft, "slug": "slice"})
            self.assertEqual(result["run"]["run_id"], "run-fixture")
            self.assertEqual(git(harness.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "devweave/run-fixture-slice")
            self.assertEqual(git(harness.repo, "rev-parse", "main").stdout.strip(), result["run"]["base_ref"])
        finally:
            harness.close()


class DummyOperations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, method: str, params: dict) -> dict:
        self.calls.append((method, params))
        return {"method": method}


def handshake(session: HostBridgeSession, token: str = "t" * 64) -> tuple[dict, dict]:
    challenge = session.handle({"type": "hello", "token": token, "client_nonce": "c" * 32})
    message = f"client:{'c' * 32}:{challenge['challenge']}:{challenge['session_id']}".encode("utf-8")
    proof = hmac.new(token.encode("utf-8"), message, hashlib.sha256).hexdigest()
    ready = session.handle({"type": "proof", "client_proof": proof})
    return challenge, ready


class HostBridgeTests(unittest.TestCase):
    def test_challenge_response_and_host_request_do_not_echo_token(self) -> None:
        operations = DummyOperations()
        nonces = iter(("challenge" * 8, "session" * 8))
        session = HostBridgeSession(operations, nonce_factory=lambda _: next(nonces))
        challenge, ready = handshake(session)
        self.assertEqual(ready["type"], "ready")
        response = session.handle({"id": 1, "method": "gate_decide", "params": {}, "session_id": ready["session_id"]})
        self.assertTrue(response["ok"])
        transcript = json.dumps([challenge, ready, response])
        self.assertNotIn("t" * 64, transcript)
        replay = session.handle({"type": "hello", "token": "x" * 64, "client_nonce": "z" * 32})
        self.assertFalse(replay["ok"])

    def test_forged_proof_closes_session_and_eof_is_clean(self) -> None:
        session = HostBridgeSession(DummyOperations(), nonce_factory=lambda _: "n" * 64)
        session.handle({"type": "hello", "token": "t" * 64, "client_nonce": "c" * 32})
        rejected = session.handle({"type": "proof", "client_proof": "0" * 64})
        self.assertEqual(rejected["error"]["code"], "BRIDGE_AUTH")
        self.assertEqual(session.state, "closed")
        with tempfile.TemporaryDirectory(prefix="devweave-host-eof-") as directory:
            self.assertEqual(run_host_stdio(Path(directory), io.BytesIO(b""), io.BytesIO()), 0)

    def test_real_adapter_rejects_agent_method_and_role_field(self) -> None:
        with tempfile.TemporaryDirectory(prefix="devweave-host-deny-") as directory:
            adapter = HostOperationAdapter(Path(directory), doctor=ReadyDoctor())
            with self.assertRaises(DevWeaveError) as method:
                adapter.call("run_inspect", {"run_id": "run"})
            self.assertEqual(method.exception.code, ErrorCode.FORBIDDEN)
            with self.assertRaises(DevWeaveError) as role:
                adapter.call("run_cancel", {"run_id": "run", "expected_revision": 1, "mutation_id": "cancel", "role": "host"})
            self.assertEqual(role.exception.code, ErrorCode.UNKNOWN_FIELD)


class PublicCliProcessTests(unittest.TestCase):
    def test_check_success_and_doctor_failure_use_json_envelopes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="devweave-v2-cli-") as directory:
            repo = Path(directory)
            (repo / ".devweave").mkdir()
            (repo / ".codex").mkdir()
            (repo / ".devweave" / "project.json").write_bytes((ROOT / "fixtures" / "devweave_v2" / "project.json").read_bytes())
            (repo / ".codex" / "config.toml").write_bytes((ROOT / ".codex" / "config.toml").read_bytes())
            for relative in ("AGENTS.md", "ARCHITECTURE.md", "README.md"):
                shutil.copy2(ROOT / relative, repo / relative)
            shutil.copytree(ROOT / "docs", repo / "docs")
            skill = repo / ".agents" / "skills" / "devweave"
            (skill / "references").mkdir(parents=True)
            shutil.copy2(ROOT / ".agents" / "skills" / "devweave" / "SKILL.md", skill / "SKILL.md")
            for source in (ROOT / ".agents" / "skills" / "devweave" / "references").glob("*.md"):
                shutil.copy2(source, skill / "references" / source.name)
            contracts = repo / "vscode-extension" / "src" / "v2"
            contracts.mkdir(parents=True)
            shutil.copy2(ROOT / "vscode-extension" / "src" / "v2" / "contracts.ts", contracts / "contracts.ts")
            checked = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_ROOT / "devweave_v2_cli.py"), "--repo", str(repo), "check"],
                capture_output=True, text=True, encoding="utf-8", shell=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)["ok"])
            failed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_ROOT / "devweave_v2_cli.py"), "--repo", str(repo), "doctor", "--codex-path", str((repo / "missing.exe").resolve())],
                capture_output=True, text=True, encoding="utf-8", shell=False,
            )
            payload = json.loads(failed.stdout)
            self.assertEqual(failed.returncode, 3)
            self.assertEqual(payload["error"]["code"], ErrorCode.CODEX_UNAVAILABLE)
            self.assertEqual(list((repo / "docs" / "exec-plans" / "active").glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.mcp_server import MAX_MESSAGE_BYTES, McpSession, run_stdio
from devweave_v2.mcp_tools import AGENT_TOOLS, HOST_ONLY_OPERATIONS, McpToolAdapter, TOOL_DEFINITIONS
from devweave_v2.project_config import ProjectConfig, command_payload_with_digest
from devweave_v2.run_service import RunService
from devweave_v2.service_factory import build_run_service
from devweave_v2.verification_engine import ExecutableResolver, VerificationEngine


BASE_REF = "a" * 40


def initialize(request_id: int = 1, protocol: str = "2025-06-18") -> dict:
    return {
        "jsonrpc": "2.0", "id": request_id, "method": "initialize",
        "params": {"protocolVersion": protocol, "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
    }


class McpHarness:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="devweave-v2-mcp-")
        self.repo = Path(self.temp.name)
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "index.md").write_text("# Context\n", encoding="utf-8")
        self.service = RunService(self.repo, clock=lambda: "2026-08-25T00:00:00Z")
        draft = json.loads((ROOT / "fixtures" / "devweave_v2" / "run-plan-draft.json").read_text(encoding="utf-8"))
        self.plan = self.service.host().run_start(
            draft, base_branch="main", base_ref=BASE_REF, run_branch="devweave/run-fixture-slice"
        )
        self.session = McpSession(McpToolAdapter(self.service.agent()))
        self.session.handle(initialize())

    def close(self) -> None:
        self.temp.cleanup()

    def call(self, name: str, arguments: dict, request_id: int = 2) -> dict:
        response = self.session.handle({
            "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        assert response is not None
        return response


class McpProtocolTests(unittest.TestCase):
    def test_initialize_list_and_call_transcript(self) -> None:
        harness = McpHarness()
        try:
            listed = harness.session.handle({
                "jsonrpc": "2.0", "id": 2, "method": "tools/list",
                "params": {"cursor": None, "_meta": {"progressToken": 1}},
            })
            names = tuple(item["name"] for item in listed["result"]["tools"])
            self.assertEqual(names, AGENT_TOOLS)
            for request_id, params in (
                (20, {"cursor": "stale"}), (21, {"extra": True}), (22, []), (23, {"_meta": "invalid"}),
            ):
                rejected = harness.session.handle({
                    "jsonrpc": "2.0", "id": request_id, "method": "tools/list", "params": params,
                })
                self.assertEqual(rejected["error"]["code"], -32602)
            inspected = harness.call("run_inspect", {"run_id": "run-fixture"})
            self.assertFalse(inspected["result"]["isError"])
            self.assertEqual(inspected["result"]["structuredContent"]["run_id"], "run-fixture")
            context = harness.call("context_read", {"run_id": "run-fixture", "path": "docs/index.md"}, 3)
            self.assertIn("# Context", context["result"]["structuredContent"]["content"])
        finally:
            harness.close()

    def test_wrong_protocol_and_preinitialize_call_fail(self) -> None:
        harness = McpHarness()
        try:
            fresh = McpSession(McpToolAdapter(harness.service.agent()))
            rejected = fresh.handle(initialize(protocol="1999-01-01"))
            self.assertEqual(rejected["error"]["code"], -32602)
            premature = fresh.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            self.assertEqual(premature["error"]["code"], -32002)
        finally:
            harness.close()

    def test_unknown_tool_field_traversal_stale_and_host_impersonation_fail_closed(self) -> None:
        harness = McpHarness()
        try:
            unknown = harness.call("anything", {"run_id": "run-fixture"})
            self.assertTrue(unknown["result"]["isError"])
            extra = harness.call("run_inspect", {"run_id": "run-fixture", "role": "host"}, 3)
            self.assertTrue(extra["result"]["isError"])
            traversal = harness.call("context_read", {"run_id": "run-fixture", "path": "../secret.txt"}, 4)
            self.assertTrue(traversal["result"]["isError"])
            for index, host_name in enumerate(HOST_ONLY_OPERATIONS, start=10):
                denied = harness.call(host_name, {"run_id": "run-fixture"}, index)
                self.assertTrue(denied["result"]["isError"])
            stale = harness.call("completion_request", {
                "run_id": "run-fixture", "expected_revision": 99, "mutation_id": "stale-complete",
            }, 20)
            self.assertTrue(stale["result"]["isError"])
            self.assertEqual(harness.service.inspect("run-fixture")["revision"], 1)
        finally:
            harness.close()

    def test_tool_annotations_and_schemas_are_explicit(self) -> None:
        self.assertEqual(tuple(item["name"] for item in TOOL_DEFINITIONS), AGENT_TOOLS)
        for tool in TOOL_DEFINITIONS:
            self.assertFalse(tool["inputSchema"]["additionalProperties"])
            self.assertFalse(tool["annotations"]["openWorldHint"])
        read_only = {item["name"] for item in TOOL_DEFINITIONS if item["annotations"]["readOnlyHint"]}
        self.assertEqual(read_only, {"run_inspect", "context_read", "verification_read"})
        self.assertTrue(next(item for item in TOOL_DEFINITIONS if item["name"] == "verification_run")["annotations"]["destructiveHint"])

    def test_verification_tool_uses_frozen_engine_and_is_idempotent(self) -> None:
        harness = McpHarness()
        try:
            # This fixture begins high; approve its two planning gates.
            plan = harness.service.host().gate_decide("run-fixture", expected_revision=1, mutation_id="scope-ok", gate_id="scope", approve=True)
            plan = harness.service.host().gate_decide("run-fixture", expected_revision=2, mutation_id="design-ok", gate_id="design", approve=True)
            raw_command = command_payload_with_digest({
                "command_id": "unit", "argv": ["python", "-B", "-c", "print('ok')"], "cwd": ".",
                "affected_paths": [], "writes": "none", "outputs": [], "dependencies": [], "timeout_seconds": 5,
                "risk_profiles": ["high"], "expected_exit_codes": [0], "release_only": False,
            })
            project = ProjectConfig.from_dict({
                "schema_version": 2, "executables": {"python": {"candidates": ["python"]}},
                "verification_plan": {"schema_version": 2, "plan_id": "mcp-fixture", "commands": [raw_command]},
            })
            harness.service.verification_engine = VerificationEngine(
                harness.repo, project, resolver=ExecutableResolver({"python": Path(sys.executable)})
            )
            first = harness.call("verification_run", {
                "run_id": "run-fixture", "expected_revision": plan["revision"], "mutation_id": "verify-once",
            }, 30)["result"]["structuredContent"]
            second = harness.call("verification_run", {
                "run_id": "run-fixture", "expected_revision": plan["revision"], "mutation_id": "verify-once",
            }, 31)["result"]["structuredContent"]
            self.assertTrue(first["report"]["gate_eligible"])
            self.assertEqual(first["report"], second["report"])
            self.assertEqual(second["run"]["revision"], plan["revision"] + 1)
        finally:
            harness.close()

    def test_bounded_stdio_transcript_and_oversized_frame(self) -> None:
        harness = McpHarness()
        try:
            messages = [initialize(), {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}]
            stdin = io.BytesIO(b"".join((json.dumps(item) + "\n").encode("utf-8") for item in messages))
            stdout = io.BytesIO()
            # run_stdio constructs its own service; only protocol discovery is needed.
            run_stdio(harness.repo, stdin, stdout)
            output = [json.loads(line) for line in stdout.getvalue().splitlines()]
            self.assertEqual(len(output), 2)
            self.assertEqual(tuple(item["name"] for item in output[1]["result"]["tools"]), AGENT_TOOLS)
            oversized_out = io.BytesIO()
            run_stdio(harness.repo, io.BytesIO((b"x" * (MAX_MESSAGE_BYTES + 1)) + b"\n"), oversized_out)
            self.assertEqual(json.loads(oversized_out.getvalue())["error"]["code"], -32700)
        finally:
            harness.close()

    def test_stdio_production_composition_runs_release_verification(self) -> None:
        harness = McpHarness()
        try:
            release_command = command_payload_with_digest({
                "command_id": "release-check", "argv": ["python", "-B", "-c", "print('release')"], "cwd": ".",
                "affected_paths": [], "writes": "none", "outputs": [], "dependencies": [], "timeout_seconds": 5,
                "risk_profiles": ["high"], "expected_exit_codes": [0], "release_only": True,
            })
            project = {
                "schema_version": 2, "executables": {"python": {"candidates": ["python", "python3", "py"]}},
                "verification_plan": {"schema_version": 2, "plan_id": "stdio-production", "commands": [release_command]},
            }
            project_path = harness.repo / ".devweave" / "project.json"
            project_path.parent.mkdir(parents=True, exist_ok=True)
            project_path.write_text(json.dumps(project), encoding="utf-8")
            (harness.repo / ".gitignore").write_text(".devweave/runtime/\n", encoding="utf-8")
            for arguments in (
                ("init", "-b", "main"),
                ("config", "user.name", "DevWeave Test"),
                ("config", "user.email", "devweave@example.test"),
                ("add", "--", ".gitignore", ".devweave/project.json", "docs/index.md"),
                ("commit", "-m", "base"),
            ):
                subprocess.run(["git", "-C", str(harness.repo), *arguments], check=True, capture_output=True, shell=False)
            base_ref = subprocess.run(
                ["git", "-C", str(harness.repo), "rev-parse", "HEAD"], check=True, capture_output=True,
                text=True, encoding="utf-8", shell=False,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(harness.repo), "switch", "-c", "devweave/run-fixture-slice"],
                check=True, capture_output=True, shell=False,
            )
            harness.service.store.path_for("run-fixture").unlink()
            harness.service = build_run_service(harness.repo)
            draft = json.loads((ROOT / "fixtures" / "devweave_v2" / "run-plan-draft.json").read_text(encoding="utf-8"))
            harness.service.host().run_start(
                draft, base_branch="main", base_ref=base_ref, run_branch="devweave/run-fixture-slice"
            )
            plan = harness.service.host().gate_decide(
                "run-fixture", expected_revision=1, mutation_id="scope-production", gate_id="scope", approve=True
            )
            plan = harness.service.host().gate_decide(
                "run-fixture", expected_revision=2, mutation_id="design-production", gate_id="design", approve=True
            )
            messages = [
                initialize(),
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                {
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {
                        "name": "verification_run",
                        "arguments": {
                            "run_id": "run-fixture", "expected_revision": plan["revision"],
                            "mutation_id": "stdio-release", "release": True,
                        },
                    },
                },
            ]
            stdin = io.BytesIO(b"".join((json.dumps(item) + "\n").encode("utf-8") for item in messages))
            stdout = io.BytesIO()
            run_stdio(harness.repo, stdin, stdout)
            output = [json.loads(line) for line in stdout.getvalue().splitlines()]
            result = output[-1]["result"]
            self.assertFalse(result["isError"])
            report = result["structuredContent"]["report"]
            self.assertTrue(report["release"])
            self.assertEqual(report["selection"]["selected"], ["release-check"])
            self.assertEqual(result["structuredContent"]["run"]["verification"]["status"], "passed")
        finally:
            harness.close()


class McpConfigurationTests(unittest.TestCase):
    def test_project_config_requires_exact_devweave_tool_allowlist(self) -> None:
        text = (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.devweave]", text)
        self.assertIn("required = true", text)
        self.assertIn('command = "python"', text)
        for name in AGENT_TOOLS:
            self.assertEqual(text.count(f'"{name}"'), 1)
        for name in HOST_ONLY_OPERATIONS:
            self.assertNotIn(f'"{name}"', text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.errors import ContractError, ErrorCode
from devweave_v2.fingerprints import snapshot_digest, snapshot_tree
from devweave_v2.project_config import ProjectConfig, command_payload_with_digest
from devweave_v2.verification_contracts import RiskLevel
from devweave_v2.verification_engine import ExecutableResolver, VerificationEngine, evidence_is_current


PLAN_DIGEST = "b" * 64


def command(
    command_id: str,
    code: str,
    *,
    affected_paths: list[str] | None = None,
    writes: str = "none",
    outputs: list[str] | None = None,
    dependencies: list[str] | None = None,
    release_only: bool = False,
    timeout_seconds: int = 5,
) -> dict:
    return command_payload_with_digest({
        "command_id": command_id,
        "argv": ["python", "-B", "-c", code],
        "cwd": ".",
        "affected_paths": affected_paths or ["src/**"],
        "writes": writes,
        "outputs": outputs or [],
        "dependencies": dependencies or [],
        "timeout_seconds": timeout_seconds,
        "risk_profiles": ["low", "standard", "high"],
        "expected_exit_codes": [0],
        "release_only": release_only,
    })


def config(*commands: dict) -> ProjectConfig:
    return ProjectConfig.from_dict({
        "schema_version": 2,
        "executables": {"python": {"candidates": ["python", "python3", "py"]}},
        "verification_plan": {"schema_version": 2, "plan_id": "fixture", "commands": list(commands)},
    })


class VerificationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="devweave-v2-verify-")
        self.repo = Path(self.temp.name)
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.txt").write_text("base\n", encoding="utf-8")
        self.resolver = ExecutableResolver({"python": Path(sys.executable)})

    def tearDown(self) -> None:
        self.temp.cleanup()

    def engine(self, *commands: dict, limit: int = 65_536) -> VerificationEngine:
        return VerificationEngine(self.repo, config(*commands), resolver=self.resolver, diagnostic_limit_bytes=limit)

    def test_selection_uses_changed_paths_dependency_closure_and_release_policy(self) -> None:
        engine = self.engine(
            command("lint", "print('lint')", affected_paths=["src/**"]),
            command("unit", "print('unit')", affected_paths=["tests/**"], dependencies=["lint"]),
            command("release", "print('release')", affected_paths=["release/**"], release_only=True),
        )
        selected = engine.plan(profile=RiskLevel.HIGH, changed_paths=["tests/test_app.py"])
        self.assertEqual(set(selected.selected), {"lint", "unit"})
        self.assertEqual(selected.closure_added, ("lint",))
        self.assertEqual(selected.skipped, ("release",))
        released = engine.plan(profile=RiskLevel.HIGH, changed_paths=["release/manifest.json"], release=True)
        self.assertEqual(released.selected, ("release",))

    def test_readers_share_a_stage_and_writers_are_serial_barriers(self) -> None:
        engine = self.engine(
            command("read-a", "print('a')"),
            command("read-b", "print('b')"),
            command("writer-a", "print('w1')", writes="declared", outputs=["build/**"]),
            command("writer-b", "print('w2')", writes="declared", outputs=["dist/**"]),
        )
        stages = engine.plan(profile=RiskLevel.HIGH).stages
        self.assertEqual(stages[0], ("read-a", "read-b"))
        self.assertIn(("writer-a",), stages)
        self.assertIn(("writer-b",), stages)

    def test_zero_exit_read_only_command_is_current_and_records_runtime_provenance(self) -> None:
        definition = command("unit", "print('ok')")
        report = self.engine(definition).run(profile=RiskLevel.HIGH, plan_digest=PLAN_DIGEST)
        evidence = report["evidence"][0]
        current = snapshot_digest(snapshot_tree(self.repo))
        self.assertTrue(report["gate_eligible"])
        self.assertTrue(evidence_is_current(
            evidence, source_digest=current, plan_digest=PLAN_DIGEST,
            definition_digest=definition["definition_digest"],
        ))
        self.assertEqual(Path(evidence["executable"]["path"]), Path(sys.executable).resolve())
        self.assertEqual(len(evidence["executable"]["sha256"]), 64)
        self.assertEqual(evidence["usage"]["total_tokens"], None)
        self.assertFalse(evidence["usage"]["available"])

    def test_runtime_and_git_metadata_are_excluded_from_source_fingerprint(self) -> None:
        (self.repo / ".git").mkdir()
        (self.repo / ".git" / "index").write_text("one", encoding="utf-8")
        (self.repo / ".devweave" / "runtime").mkdir(parents=True)
        (self.repo / ".devweave" / "runtime" / "events.jsonl").write_text("one", encoding="utf-8")
        before = snapshot_digest(snapshot_tree(self.repo))
        (self.repo / ".git" / "index").write_text("two", encoding="utf-8")
        (self.repo / ".devweave" / "runtime" / "events.jsonl").write_text("two", encoding="utf-8")
        self.assertEqual(before, snapshot_digest(snapshot_tree(self.repo)))

    def test_nonzero_timeout_and_undeclared_effect_are_ineligible(self) -> None:
        cases = (
            command("nonzero", "raise SystemExit(7)"),
            command("timeout", "import time; time.sleep(2)", timeout_seconds=1),
            command("undeclared", "from pathlib import Path; Path('oops.txt').write_text('x')"),
        )
        for definition in cases:
            with self.subTest(definition["command_id"]):
                (self.repo / "oops.txt").unlink(missing_ok=True)
                report = self.engine(definition).run(profile=RiskLevel.HIGH, plan_digest=PLAN_DIGEST)
                evidence = report["evidence"][0]
                self.assertFalse(evidence["gate_eligible"])
        self.assertTrue(report["evidence"][0]["undeclared_paths"])

    def test_declared_writer_reconciles_output_and_dependency_failure_skips_downstream(self) -> None:
        writer = command(
            "writer", "from pathlib import Path; Path('build').mkdir(exist_ok=True); Path('build/out.txt').write_text('ok')",
            writes="declared", outputs=["build/**"],
        )
        success = self.engine(writer).run(profile=RiskLevel.HIGH, plan_digest=PLAN_DIGEST)
        self.assertTrue(success["gate_eligible"])
        self.assertEqual(success["evidence"][0]["changed_paths"], ["build/out.txt"])
        downstream = command("downstream", "print('must-not-run')", dependencies=["failure"])
        failed = self.engine(command("failure", "raise SystemExit(2)"), downstream).run(
            profile=RiskLevel.HIGH, plan_digest=PLAN_DIGEST
        )
        by_id = {item["command_id"]: item for item in failed["evidence"]}
        self.assertEqual(by_id["downstream"]["status"], "skipped_dependency")

    def test_stale_plan_command_or_source_invalidates_evidence(self) -> None:
        definition = command("unit", "print('ok')")
        evidence = self.engine(definition).run(profile=RiskLevel.HIGH, plan_digest=PLAN_DIGEST)["evidence"][0]
        current = evidence["output_digest"]
        self.assertFalse(evidence_is_current(evidence, source_digest=current, plan_digest="c" * 64, definition_digest=definition["definition_digest"]))
        self.assertFalse(evidence_is_current(evidence, source_digest="d" * 64, plan_digest=PLAN_DIGEST, definition_digest=definition["definition_digest"]))
        self.assertFalse(evidence_is_current(evidence, source_digest=current, plan_digest=PLAN_DIGEST, definition_digest="e" * 64))

    def test_diagnostics_are_redacted_and_bounded_without_usage_estimates(self) -> None:
        definition = command("logs", "print('api_key=super-secret-value ' + ('x' * 10000))")
        evidence = self.engine(definition, limit=256).run(profile=RiskLevel.HIGH, plan_digest=PLAN_DIGEST)["evidence"][0]
        self.assertNotIn("super-secret-value", evidence["stdout"])
        self.assertIn("<redacted>", evidence["stdout"])
        self.assertTrue(evidence["diagnostic_truncated"])
        self.assertLessEqual(len(evidence["stdout"].encode("utf-8")), 256)
        self.assertIsNone(evidence["usage"]["input_tokens"])


class ProjectConfigTests(unittest.TestCase):
    def test_golden_tracked_config_is_valid_and_machine_portable(self) -> None:
        path = ROOT / "fixtures" / "devweave_v2" / "project.json"
        raw_text = path.read_text(encoding="utf-8")
        parsed = ProjectConfig.from_dict(json.loads(raw_text))
        self.assertEqual(parsed.schema_version, 2)
        self.assertNotIn(str(Path(sys.executable).resolve()), raw_text)
        self.assertNotIn("resolved_executable", raw_text)
        self.assertNotIn("executable_sha256", raw_text)

    def test_tracked_config_rejects_absolute_executable_and_stale_hash_fields(self) -> None:
        raw = {
            "schema_version": 2,
            "executables": {"python": {"candidates": [str(Path(sys.executable).resolve())]}},
            "verification_plan": {"schema_version": 2, "plan_id": "fixture", "commands": [command("unit", "print('x')")]},
        }
        with self.assertRaises(ContractError) as absolute:
            ProjectConfig.from_dict(raw)
        self.assertEqual(absolute.exception.code, ErrorCode.FORBIDDEN)
        raw["executables"] = {"python": {"candidates": ["python"], "sha256": "a" * 64}}
        with self.assertRaises(ContractError) as unknown:
            ProjectConfig.from_dict(raw)
        self.assertEqual(unknown.exception.code, ErrorCode.UNKNOWN_FIELD)

    def test_definition_digest_and_cycles_fail_closed(self) -> None:
        stale = command("unit", "print('x')")
        stale["argv"][-1] = "print('changed')"
        with self.assertRaises(ContractError) as digest:
            config(stale)
        self.assertEqual(digest.exception.code, ErrorCode.CONFLICT)
        first = command("first", "print('1')", dependencies=["second"])
        second = command("second", "print('2')", dependencies=["first"])
        with self.assertRaises(ContractError) as cycle:
            config(first, second)
        self.assertEqual(cycle.exception.code, ErrorCode.INVALID_VALUE)


if __name__ == "__main__":
    unittest.main()

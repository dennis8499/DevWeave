from __future__ import annotations

import sys
import unittest
from pathlib import Path

from devweave_test_support import REPOSITORY_ROOT, RepositoryHarness, core

SCRIPT_ROOT = REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import command_policy as policy


def decision_payload(
    *,
    command: dict | None = None,
    argv: list[str] | None = None,
    phase: str = "implementation",
    gate_status: str = "approved",
    session_bound: bool = True,
    execution_channel: str = "bash",
    release_stage: str | None = None,
    cwd: str = ".",
) -> dict:
    return {
        "work_item": {"id": "fixture-work", "risk": "high"},
        "phase": phase,
        "gate_status": gate_status,
        "session_bound": session_bound,
        "command": command,
        "argv": argv or [],
        "cwd": cwd,
        "writes": (command or {}).get("writes", "none"),
        "outputs": (command or {}).get("outputs", []),
        "affected_paths": (command or {}).get("affected_paths", []),
        "release_stage": release_stage,
        "dependency_closure": [],
        "current_policy_digest": "policy-current",
        "execution_channel": execution_channel,
    }


class CommandPolicyTests(unittest.TestCase):
    def _prepare_g2_with_commands(
        self,
        harness: RepositoryHarness,
        commands: list[dict] | None = None,
    ) -> dict:
        state = harness.start()
        harness.fill_requirements(state["id"])
        core.set_scope(harness.repo, state["id"], ["src/**"], "限制在 fixture source 範圍。")
        if commands:
            for command in commands:
                harness.configure_command(
                    command["id"],
                    argv=command["argv"],
                    required_for=tuple(command.get("required_for", ())),
                    depends_on=tuple(command.get("depends_on", ())),
                    affected_paths=tuple(command.get("affected_paths", ())) or None,
                    writes=command.get("writes"),
                    outputs=tuple(command.get("outputs", ())) or None,
                    release_only=command.get("release_only", False),
                )
        core.approve_gate(harness.repo, state["id"], "scope", "Test Approver")
        harness.fill_design(state["id"])
        return core.approve_gate(harness.repo, state["id"], "build", "Test Approver")

    def test_read_only_parser_fails_closed_for_shell_injection_and_output_flags(self) -> None:
        unsafe = (
            "git status & echo SHOULD_NOT_RUN",
            "git status $(echo SHOULD_NOT_RUN)",
            "git status `echo SHOULD_NOT_RUN`",
            "git diff --output=.devweave/cache/guard-probe.txt",
            "git status --unknown-helper",
            "Get-Content . & Write-Output SHOULD_NOT_RUN",
            "Get-Content . $(Write-Output SHOULD_NOT_RUN)",
            "Get-ChildItem . | Out-File .devweave/cache/probe.txt",
        )
        for payload in unsafe:
            with self.subTest(payload=payload):
                result = policy.evaluate_read_only(payload)
                self.assertFalse(result.allowed)

    def test_known_safe_read_only_forms_remain_allowed(self) -> None:
        safe = (
            "git status --short",
            "git diff --no-ext-diff --no-textconv",
            "git branch --show-current",
            "rg --files",
            "Get-Content README.md",
            "Test-Path README.md",
        )
        for payload in safe:
            with self.subTest(payload=payload):
                result = policy.evaluate_read_only(payload)
                self.assertTrue(result.allowed, result.reason_code)

    def test_configured_command_requires_devweave_executor(self) -> None:
        command = {
            "id": "extension-package",
            "argv": ["npm.cmd", "run", "package"],
            "cwd": "vscode-extension",
            "writes": "tracked-artifact",
            "outputs": ["vscode-extension/dist"],
            "release_only": True,
            "timeout_seconds": 300,
        }
        result = policy.evaluate(
            decision_payload(
                command=command,
                argv=command["argv"],
                cwd="vscode-extension",
                execution_channel="bash",
                release_stage="release",
            )
        )
        self.assertFalse(result.allowed)
        self.assertEqual("configured_command_requires_executor", result.reason_code)

    def test_pre_g2_writer_is_denied_even_through_executor(self) -> None:
        command = {
            "id": "build",
            "argv": [sys.executable, "-c", "print('build')"],
            "cwd": ".",
            "writes": "generated",
            "outputs": ["dist"],
        }
        result = policy.evaluate(
            decision_payload(
                command=command,
                argv=command["argv"],
                execution_channel="devweave_executor",
                gate_status="pending",
            )
        )
        self.assertFalse(result.allowed)
        self.assertEqual("writes_require_g2", result.reason_code)

    def test_command_definition_digest_changes_when_policy_changes(self) -> None:
        command = {
            "id": "check",
            "argv": [sys.executable, "-c", "print('ok')"],
            "cwd": ".",
            "writes": "none",
            "outputs": [],
            "timeout_seconds": 30,
        }
        original = policy.command_definition_digest(command)
        changed = dict(command, timeout_seconds=31)
        self.assertNotEqual(original, policy.command_definition_digest(changed))

    def test_effective_plan_has_one_frozen_selection_basis(self) -> None:
        project = {
            "command_policy_version": 2,
            "commands": [
                {
                    "id": "build",
                    "argv": [sys.executable, "-c", "print('build')"],
                    "cwd": ".",
                    "writes": "generated",
                    "outputs": ["dist"],
                    "required_for": ["standard"],
                },
                {
                    "id": "test",
                    "argv": [sys.executable, "-c", "print('test')"],
                    "cwd": ".",
                    "writes": "none",
                    "outputs": [],
                    "depends_on": ["release"],
                    "required_for": ["standard"],
                },
                {
                    "id": "release",
                    "argv": [sys.executable, "-c", "print('release')"],
                    "cwd": ".",
                    "writes": "tracked-artifact",
                    "outputs": ["dist"],
                    "release_only": True,
                    "required_for": ["standard"],
                },
            ],
            "verification_profiles": {"standard": ["build", "test", "release"]},
        }
        plan = policy.build_effective_plan(
            project,
            {"id": "fixture-work", "risk": "standard", "phase": "implementation"},
            profile="standard",
            affected_paths=["src/app.txt"],
        )
        self.assertTrue(plan["plan_id"])
        self.assertTrue(plan["plan_digest"])
        self.assertEqual(plan["project_policy_digest"], policy.policy_digest(project))
        self.assertEqual(plan["selected_commands"], [])
        skipped = {item["id"]: item["reason"] for item in plan["skipped"]}
        self.assertEqual("release-only-dependency:release", skipped["test"])
        self.assertEqual("release-only", skipped["release"])

    def test_nonzero_any_and_undeclared_effects_are_not_gate_eligible(self) -> None:
        plan = {
            "plan_id": "plan-1",
            "plan_digest": "plan-digest",
            "project_policy_digest": "policy-digest",
            "commands": {
                "check": {
                    "definition_digest": "command-digest",
                    "expected_success_exit_codes": [0],
                    "writes": "none",
                    "outputs": [],
                }
            },
        }
        common = {
            "plan_id": "plan-1",
            "plan_digest": "plan-digest",
            "project_policy_digest": "policy-digest",
            "command_id": "check",
            "command_definition_digest": "command-digest",
            "source_fingerprint": "source-current",
            "current_source_fingerprint": "source-current",
            "status": "passed",
            "exit_code": 0,
            "actual_changed_paths": [],
            "declared_outputs": [],
            "execution_channel": "devweave_executor",
            "expectation": "zero",
        }
        self.assertTrue(
            policy.derive_evidence_eligibility(plan, dict(common, evidence_kind="verification"))["gate_eligible"]
        )
        self.assertFalse(
            policy.derive_evidence_eligibility(
                plan,
                dict(common, exit_code=7, expectation="nonzero"),
            )["gate_eligible"]
        )
        self.assertFalse(
            policy.derive_evidence_eligibility(
                plan,
                dict(common, expectation="any"),
            )["gate_eligible"]
        )
        self.assertFalse(
            policy.derive_evidence_eligibility(
                plan,
                dict(common, actual_changed_paths=["src/undeclared.txt"]),
            )["gate_eligible"]
        )

    def test_g2_approval_freezes_plan_and_evidence_binds_to_it(self) -> None:
        with RepositoryHarness() as harness:
            command = [sys.executable, "-c", "print('frozen plan')"]
            state = self._prepare_g2_with_commands(
                harness,
                [{"id": "frozen-check", "argv": command, "required_for": ("standard",)}],
            )
            plan = state["verification_plan"]
            self.assertTrue(plan["plan_id"])
            self.assertEqual(
                core.load_project(harness.repo)["command_policy_version"],
                plan["policy_version"],
            )
            evidence = core.run_verification(
                harness.repo,
                state["id"],
                command_id="frozen-check",
                kind="regression",
                covers=["AC-001"],
                tasks=["TASK-001"],
            )
            self.assertEqual(plan["plan_digest"], evidence["effective_plan_digest"])
            self.assertTrue(evidence["gate_eligible"])

    def test_expectation_match_is_recorded_but_never_gate_eligible(self) -> None:
        with RepositoryHarness() as harness:
            state = self._prepare_g2_with_commands(
                harness,
                [
                    {
                        "id": "expected-failure",
                        "argv": [sys.executable, "-c", "raise SystemExit(7)"],
                        "required_for": (),
                    }
                ],
            )
            evidence = core.run_verification(
                harness.repo,
                state["id"],
                command_id="expected-failure",
                kind="diagnostic",
                expectation="nonzero",
            )
            self.assertEqual("passed", evidence["status"])
            self.assertFalse(evidence["gate_eligible"])
            self.assertEqual("expectation_not_zero_only", evidence["eligibility_reason"])

    def test_policy_drift_stales_existing_evidence(self) -> None:
        with RepositoryHarness() as harness:
            state = self._prepare_g2_with_commands(
                harness,
                [{"id": "drift-check", "argv": [sys.executable, "-c", "print('drift')"]}],
            )
            evidence = core.run_verification(
                harness.repo,
                state["id"],
                command_id="drift-check",
                kind="regression",
                covers=["AC-001"],
                tasks=["TASK-001"],
            )
            project = core.load_project(harness.repo)
            for item in project["commands"]:
                if item["id"] == "drift-check":
                    item["timeout_seconds"] += 1
            core.atomic_write_json(core.project_path(harness.repo), project)
            updated = core.sync_state(harness.repo, state["id"])
            self.assertTrue(updated["verification_plan"]["stale"])
            self.assertTrue(updated["evidence"][evidence["id"]]["stale"])
            self.assertIsNone(updated["last_verification"])

    def test_writer_stage_completes_before_read_only_test(self) -> None:
        with RepositoryHarness() as harness:
            writer = [
                sys.executable,
                "-c",
                "from pathlib import Path; import time; time.sleep(.15); Path('dist').mkdir(); Path('dist/ready.txt').write_text('ready')",
            ]
            reader = [
                sys.executable,
                "-c",
                "from pathlib import Path; raise SystemExit(0 if Path('dist/ready.txt').is_file() else 9)",
            ]
            state = self._prepare_g2_with_commands(
                harness,
                [
                    {
                        "id": "build-output",
                        "argv": writer,
                        "required_for": ("standard",),
                        "writes": "generated",
                        "outputs": ("dist",),
                    },
                    {
                        "id": "read-output",
                        "argv": reader,
                        "required_for": ("standard",),
                        "writes": "none",
                    },
                ],
            )
            result = core.run_verification_profile(
                harness.repo,
                state["id"],
                profile="standard",
                kind="regression",
                max_parallel=2,
            )
            records = {item["command_id"]: item for item in result["batch"]["commands"]}
            self.assertTrue(result["ok"], result)
            self.assertEqual(
                core.load_state(harness.repo, state["id"])["verification_plan"]["plan_digest"],
                result["batch"]["selection"]["effective_plan_digest"],
            )
            self.assertLess(
                records["build-output"]["evidence"]["execution_sequence"],
                records["read-output"]["evidence"]["execution_sequence"],
            )

    def test_g3_rejects_expectation_evidence_for_required_command(self) -> None:
        with RepositoryHarness() as harness:
            state = self._prepare_g2_with_commands(
                harness,
                [
                    {
                        "id": "required-check",
                        "argv": [sys.executable, "-c", "raise SystemExit(7)"],
                        "required_for": ("standard",),
                    }
                ],
            )
            harness.implement(state["id"], "expectation-only evidence")
            diagnostic = core.run_verification(
                harness.repo,
                state["id"],
                command_id="required-check",
                kind="regression",
                expectation="nonzero",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            acceptance = core.add_evidence(
                harness.repo,
                state["id"],
                kind="acceptance",
                status="passed",
                summary="人工驗收仍通過，但不能取代 required command。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
                observed_result="success",
            )
            core.set_baseline_updates(harness.repo, state["id"], [], "基線不需更新。")
            harness.fill_acceptance(state["id"], [diagnostic["id"], acceptance["id"]])
            report = core.validate_work(
                harness.repo,
                core.load_state(harness.repo, state["id"]),
                "acceptance",
            )
            self.assertTrue(
                any("no current passing evidence" in error for error in report.errors),
                report.errors,
            )

    def test_g3_accepts_release_only_dependency_skip_from_frozen_plan(self) -> None:
        with RepositoryHarness() as harness:
            state = self._prepare_g2_with_commands(
                harness,
                [
                    {
                        "id": "release-package",
                        "argv": [sys.executable, "-c", "print('release')"],
                        "required_for": ("standard",),
                        "writes": "tracked-artifact",
                        "outputs": ("dist",),
                        "release_only": True,
                    },
                    {
                        "id": "release-smoke",
                        "argv": [sys.executable, "-c", "print('smoke')"],
                        "required_for": ("standard",),
                        "depends_on": ("release-package",),
                    },
                ],
            )
            harness.implement(state["id"], "release-only dependency parity", review=False)
            current = core.load_state(harness.repo, state["id"])
            skipped = {
                item["id"]: item["reason"]
                for item in current["verification_plan"]["skipped"]
            }
            self.assertEqual(
                "release-only-dependency:release-package",
                skipped["release-smoke"],
            )
            report = core.validate_work(harness.repo, current, "acceptance")
            self.assertFalse(
                any(
                    "Required verification command is not in the Effective Verification Plan: release-smoke"
                    in error
                    for error in report.errors
                ),
                report.errors,
            )

    def test_typed_policy_mutation_stales_post_g2_work(self) -> None:
        with RepositoryHarness() as harness:
            state = self._prepare_g2_with_commands(
                harness,
                [{"id": "mutable-check", "argv": [sys.executable, "-c", "print('mutable')"]}],
            )
            project = core.load_project(harness.repo)
            previous = policy.policy_digest(project)
            for item in project["commands"]:
                if item["id"] == "mutable-check":
                    item["timeout_seconds"] += 1
            core.atomic_write_json(core.project_path(harness.repo), project)
            current = policy.policy_digest(core.load_project(harness.repo))
            invalidated = core.invalidate_active_verification_plans(
                harness.repo,
                previous_policy_digest=previous,
                current_policy_digest=current,
            )
            self.assertEqual([state["id"]], invalidated)
            updated = core.load_state(harness.repo, state["id"])
            self.assertTrue(updated["verification_plan"]["stale"])
            self.assertEqual("design", updated["phase"])


if __name__ == "__main__":
    unittest.main()

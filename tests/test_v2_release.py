from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.cutover import (  # noqa: E402
    CutoverFinalizer,
    LEGACY_TRANSITION_STATE_PATH,
    TRANSITION_COMPLETION_PATH,
    TRANSITION_RUN_ID,
    _git_files,
    _is_legacy,
    canonical_file_sha256,
    generate_manifest,
    write_manifest,
)
from devweave_v2.canonical import dumps  # noqa: E402
from devweave_v2.errors import DevWeaveError, ErrorCode  # noqa: E402
from devweave_v2.plan_contracts import RunPlanDraft  # noqa: E402
from devweave_v2.project_config import ProjectConfig  # noqa: E402
from devweave_v2.run_state import new_exec_plan, validate_exec_plan  # noqa: E402
from devweave_v2.transition_record import WORK_ROOT, record_transition_completion  # noqa: E402


class CutoverFinalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="devweave-cutover-")
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        self._write_fixture()
        self._git("init", "-q")
        self._git("config", "user.email", "devweave@example.invalid")
        self._git("config", "user.name", "DevWeave Test")
        self._git("add", "-A")
        self._git("commit", "-qm", "legacy fixture")
        self.base_ref = self._git("rev-parse", "HEAD").strip()
        self._git("checkout", "-qb", "devweave/transition-fixture")
        self._bind_completion_to_git()
        self.manifest_path = self.repository / "docs" / "generated" / "v2-cutover-manifest.json"
        write_manifest(self.manifest_path, generate_manifest(self.repository, base_ref=self.base_ref))

    def test_fresh_apply_and_retry_converge_without_legacy_paths(self) -> None:
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        self.assertEqual("ready", finalizer.check()["status"])
        with self.assertRaisesRegex(RuntimeError, "Injected cutover failure"):
            finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256, fail_after=2)

        retried = finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual("applied", retried["status"])
        self.assertEqual("already_applied", finalizer.check()["status"])
        self.assertEqual(
            "final agents\n",
            (self.repository / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "final skill\n",
            (self.repository / ".agents/skills/devweave/SKILL.md").read_text(encoding="utf-8"),
        )
        archived = self.repository / TRANSITION_COMPLETION_PATH
        self.assertTrue(archived.is_file())
        self.assertEqual("completed", validate_exec_plan(json.loads(archived.read_text(encoding="utf-8")))["status"])
        installed = json.loads((self.repository / ".devweave/project.json").read_text(encoding="utf-8"))
        self.assertEqual(2, installed["schema_version"])
        for relative in _git_files(self.repository):
            if _is_legacy(relative):
                self.assertFalse((self.repository / relative).exists(), relative)

        again = finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual({"status": "already_applied", "manifest_sha256": finalizer.manifest_sha256, "mutations": 0}, again)

    def test_hash_drift_fails_before_any_mutation(self) -> None:
        old_agents = (self.repository / "AGENTS.md").read_bytes()
        (self.repository / "wiki/index.md").write_text("drift\n", encoding="utf-8")
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual(ErrorCode.CONFLICT, caught.exception.code)
        self.assertEqual(old_agents, (self.repository / "AGENTS.md").read_bytes())
        self.assertTrue((self.repository / ".agents/skills/grill-me/SKILL.md").exists())

    def test_manifest_hash_and_explicit_approval_are_both_required(self) -> None:
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.apply(approved_manifest_sha256="0" * 64)
        self.assertEqual(ErrorCode.FORBIDDEN, caught.exception.code)
        self.assertEqual("old agents\n", (self.repository / "AGENTS.md").read_text(encoding="utf-8"))

        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        raw["base_ref"] = "f" * 40
        self.manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(DevWeaveError) as tampered:
            CutoverFinalizer(self.repository, self.manifest_path)
        self.assertEqual(ErrorCode.CONFLICT, tampered.exception.code)

    def test_new_legacy_path_after_manifest_is_rejected(self) -> None:
        added = self.repository / "wiki" / "late.md"
        added.write_text("late legacy truth\n", encoding="utf-8")
        self._git("add", "wiki/late.md")
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.check()
        self.assertEqual(ErrorCode.CONFLICT, caught.exception.code)
        self.assertTrue(added.exists())

    def test_only_exact_managed_knowledge_deletions_may_precede_manifest(self) -> None:
        overview = self.repository / "wiki/overview.md"
        overview_hash = canonical_file_sha256(overview)
        overview.unlink()

        manifest = generate_manifest(self.repository, base_ref=self.base_ref)
        deletion = next(
            item for item in manifest["deletions"] if item["path"] == "wiki/overview.md"
        )
        self.assertEqual(overview_hash, deletion["sha256"])
        write_manifest(self.manifest_path, manifest)
        report = CutoverFinalizer(self.repository, self.manifest_path).check()
        self.assertEqual(1, report["completed_deletions"])

        (self.repository / "wiki/index.md").unlink()
        with self.assertRaises(DevWeaveError) as caught:
            generate_manifest(self.repository, base_ref=self.base_ref)
        self.assertEqual(ErrorCode.NOT_FOUND, caught.exception.code)

    def test_apply_requires_hash_bound_completed_transition_record(self) -> None:
        (self.repository / TRANSITION_COMPLETION_PATH).unlink()
        self._git("add", TRANSITION_COMPLETION_PATH)
        self._git("commit", "-qm", "remove completion proof")
        write_manifest(self.manifest_path, generate_manifest(self.repository, base_ref=self.base_ref))
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        self.assertFalse(finalizer.check()["completion_record_ready"])
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual(ErrorCode.BLOCKED, caught.exception.code)
        self.assertEqual("old agents\n", (self.repository / "AGENTS.md").read_text(encoding="utf-8"))

    def test_retained_completion_record_drift_fails_before_mutation(self) -> None:
        path = self.repository / TRANSITION_COMPLETION_PATH
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual(ErrorCode.CONFLICT, caught.exception.code)
        self.assertEqual("old agents\n", (self.repository / "AGENTS.md").read_text(encoding="utf-8"))

    def test_changed_head_fails_before_mutation(self) -> None:
        changed = self.repository / "docs" / "head-drift.md"
        changed.parent.mkdir(parents=True, exist_ok=True)
        changed.write_text("new head\n", encoding="utf-8")
        self._git("add", "docs/head-drift.md")
        self._git("commit", "-qm", "move prepared head")
        self._assert_preflight_conflict_without_mutation()

    def test_changed_branch_fails_before_mutation(self) -> None:
        self._git("checkout", "-qb", "devweave/wrong-cutover-branch")
        self._assert_preflight_conflict_without_mutation()

    def test_moved_base_branch_fails_before_mutation(self) -> None:
        self._git("checkout", "-qb", "base-drift")
        changed = self.repository / "base-drift.txt"
        changed.write_text("moved base\n", encoding="utf-8")
        self._git("add", "base-drift.txt")
        self._git("commit", "-qm", "move base")
        moved = self._git("rev-parse", "HEAD").strip()
        self._git("checkout", "devweave/transition-fixture")
        self._git("branch", "-f", "master", moved)
        self._assert_preflight_conflict_without_mutation()

    def test_unrelated_dirty_path_fails_before_mutation(self) -> None:
        (self.repository / "unrelated.txt").write_text("not in manifest\n", encoding="utf-8")
        self._assert_preflight_conflict_without_mutation()

    def _assert_preflight_conflict_without_mutation(self) -> None:
        before = (self.repository / "AGENTS.md").read_bytes()
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual(ErrorCode.CONFLICT, caught.exception.code)
        self.assertEqual(before, (self.repository / "AGENTS.md").read_bytes())

    def _write_fixture(self) -> None:
        files = {
            "AGENTS.md": "old agents\n",
            ".devweave/project.json": '{"schema_version":1}\n',
            ".devweave/baseline/product.md": "old baseline\n",
            ".devweave/work-items/old/state.json": "{}\n",
            "wiki/index.md": "old wiki\n",
            "wiki/overview.md": "old overview\n",
            ".agents/skills/devweave/SKILL.md": "old skill\n",
            ".agents/skills/devweave/references/contracts.md": "old reference\n",
            ".agents/skills/devweave/scripts/devweave.py": "# old launcher\n",
            ".agents/skills/devweave/assets/v2-cutover/AGENTS.md": "final agents\n",
            ".agents/skills/devweave/assets/v2-cutover/project.json": '{"schema_version":2}\n',
            ".agents/skills/devweave/assets/v2-skill/SKILL.md": "final skill\n",
            ".agents/skills/devweave/assets/v2-skill/references/planning.md": "planning\n",
            ".agents/skills/devweave/assets/v2-skill/references/implementation.md": "implementation\n",
            ".agents/skills/devweave/assets/v2-skill/references/verification.md": "verification\n",
            ".agents/skills/grill-me/SKILL.md": "legacy companion\n",
            "skills-lock.json": "{}\n",
            "tests/devweave_test_support.py": "# old support\n",
            "tests/test_cli.py": "# old test\n",
            "tests/test_v2_contracts.py": "# v2 test\n",
            "vscode-extension/src/clipboard.ts": "export const old = true;\n",
            "vscode-extension/src/extension.ts": "export const current = true;\n",
            "vscode-extension/test/unit/wiki-search.test.ts": "// old test\n",
            "vscode-extension/test/unit/security.test.ts": "// v2 test\n",
            "vscode-extension/devweave-control-center-0.2.3.vsix": "legacy binary\x00",
        }
        for relative, content in files.items():
            path = self.repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
        draft_raw = json.loads((REPOSITORY_ROOT / "fixtures/devweave_v2/run-plan-draft.json").read_text(encoding="utf-8"))
        draft_raw["run_id"] = TRANSITION_RUN_ID
        draft = RunPlanDraft.from_dict(draft_raw)
        plan = new_exec_plan(
            draft,
            base_branch="master",
            base_ref="a" * 40,
            run_branch="devweave/transition-fixture",
            now="2026-08-25T00:00:00Z",
        )
        for gate in plan["gates"].values():
            gate.update(
                {
                    "status": "approved",
                    "fingerprint": plan["definition_fingerprint"],
                    "approved_revision": 1,
                    "decided_at": "2026-08-25T00:00:00Z",
                }
            )
        for task in plan["tasks"].values():
            task.update({"status": "completed", "progress": "verified", "commit_ref": "a" * 40})
        plan.update(
            {
                "status": "completed",
                "phase": "closed",
                "verification": {
                    "status": "passed",
                    "evidence_ids": ["VER-1"],
                    "current_report_id": "transition",
                    "reports": {
                        "transition": {
                            "base_branch": "master",
                            "base_ref": "a" * 40,
                            "repository_head": "a" * 40,
                            "run_branch": "devweave/transition-fixture",
                            "source_head": "a" * 40,
                            "source_digest": "c" * 64,
                            "source_fingerprint": "c" * 64,
                        }
                    },
                },
                "review": {
                    "mode": "detached_fix_reverify", "max_rounds": 3, "round": 1,
                    "status": "passed", "finding_ids": [], "source_fingerprint": "c" * 64,
                    "reviewer_thread_id": "reviewer-fixture", "review_turn_id": "turn-fixture",
                },
                "completion_requested": True,
            }
        )
        completed = self.repository / TRANSITION_COMPLETION_PATH
        completed.parent.mkdir(parents=True, exist_ok=True)
        completed.write_text(dumps(validate_exec_plan(plan)), encoding="utf-8")

    def _bind_completion_to_git(self) -> None:
        completed = self.repository / TRANSITION_COMPLETION_PATH
        plan = json.loads(completed.read_text(encoding="utf-8"))
        plan["base_ref"] = self.base_ref
        for task in plan["tasks"].values():
            task["commit_ref"] = self.base_ref
        report = plan["verification"]["reports"]["transition"]
        report.update(
            {
                "base_ref": self.base_ref,
                "repository_head": self.base_ref,
                "source_head": self.base_ref,
            }
        )
        completed.write_text(dumps(validate_exec_plan(plan)), encoding="utf-8")
        state = self.repository / LEGACY_TRANSITION_STATE_PATH
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(
            dumps(
                {
                    "id": TRANSITION_RUN_ID,
                    "base_source": {"branch": "master", "head": self.base_ref},
                    "last_verification": {"source_fingerprint": "c" * 64},
                }
            ),
            encoding="utf-8",
        )

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.repository, check=True, capture_output=True,
            text=True, encoding="utf-8", shell=False,
        )
        return result.stdout


class TransitionCompletionRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="devweave-transition-record-")
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        source_work = REPOSITORY_ROOT / WORK_ROOT
        target_work = self.repository / WORK_ROOT
        target_work.mkdir(parents=True)
        for name in ("requirements.md", "design.md", "plan.md", "acceptance.md"):
            shutil.copy2(source_work / name, target_work / name)
        staged = self.repository / ".agents/skills/devweave/assets/v2-cutover/project.json"
        staged.parent.mkdir(parents=True)
        shutil.copy2(REPOSITORY_ROOT / ".agents/skills/devweave/assets/v2-cutover/project.json", staged)
        generated = self.repository / "docs/generated"
        generated.mkdir(parents=True)
        shutil.copy2(REPOSITORY_ROOT / "docs/generated/v1-export.json", generated / "v1-export.json")
        shutil.copy2(REPOSITORY_ROOT / "docs/generated/v1-export.md", generated / "v1-export.md")

        state = json.loads((source_work / "state.json").read_text(encoding="utf-8"))
        state["status"] = "closed"
        state["base_source"].update({"branch": "master", "head": "a" * 40})
        state["knowledge_review"].update({"disposition": "no-update", "rationale": "V2 docs are canonical."})
        for gate in state["gates"].values():
            gate.update({"status": "approved", "approved_at": "2026-08-25T00:00:00Z", "approved_by": "user"})
        for task in state["tasks"].values():
            task.update({"status": "completed", "completed_at": "2026-08-25T00:00:00Z", "note": "verified"})
        source_head = "b" * 40
        acceptance_ids = [f"AC-{index:03d}" for index in range(1, 23)]
        state["evidence"] = {
            "EVID-VERIFY": {
                "id": "EVID-VERIFY", "kind": "verification", "status": "passed", "stale": False,
                "binds_current_source": True, "git_head": source_head, "source_fingerprint": "c" * 64,
                "observed_result": "success", "covers": acceptance_ids,
            },
            "EVID-REVIEW": {
                "id": "EVID-REVIEW", "kind": "review", "status": "passed", "stale": False,
                "binds_current_source": True, "git_head": source_head, "source_fingerprint": "c" * 64,
                "review": {
                    "context_mode": "isolated_read_only", "result": "passed", "reviewer_id": "reviewer-1",
                    "report_sha256": "d" * 64, "covers": acceptance_ids, "findings": [
                        {"id": "FIND-1", "severity": "advisory", "title": "Bounded residual", "evidence": "fixture"}
                    ],
                },
            },
        }
        state["last_verification"] = {
            "at": "2026-08-25T00:00:00Z", "evidence_id": "EVID-VERIFY", "source_fingerprint": "c" * 64,
        }
        (target_work / "state.json").write_text(dumps(state), encoding="utf-8")
        self._git("init", "-q")
        self._git("config", "user.email", "devweave@example.invalid")
        self._git("config", "user.name", "DevWeave Test")
        self._git("checkout", "-qb", "devweave/20260825-163914-app-server-harness")
        self._git("add", "-A")
        self._git("commit", "-qm", "closed transition fixture")
        self.source_head = source_head

    def test_closed_transition_projects_to_strict_completed_exec_plan(self) -> None:
        result = record_transition_completion(
            self.repository,
            work_id=TRANSITION_RUN_ID,
            expected_source_head=self.source_head,
        )
        self.assertEqual("recorded", result["status"])
        target = self.repository / TRANSITION_COMPLETION_PATH
        plan = validate_exec_plan(json.loads(target.read_text(encoding="utf-8")))
        self.assertEqual(("completed", "closed", "high"), (plan["status"], plan["phase"], plan["risk"]))
        self.assertEqual(12, len(plan["tasks"]))
        self.assertEqual(22, len(plan["plan"]["acceptance_criteria"]))
        self.assertEqual(["EVID-VERIFY", "EVID-REVIEW"], plan["verification"]["evidence_ids"])
        self.assertEqual(["FIND-1"], plan["review"]["finding_ids"])

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.repository, check=True, capture_output=True,
            text=True, encoding="utf-8", shell=False,
        )
        return result.stdout


class RepositoryReleaseContractTests(unittest.TestCase):
    def test_staged_project_is_strict_schema_v2_with_release_dag(self) -> None:
        staged = REPOSITORY_ROOT / ".agents/skills/devweave/assets/v2-cutover/project.json"
        path = staged if staged.is_file() else REPOSITORY_ROOT / ".devweave/project.json"
        config = ProjectConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
        command_ids = {command.command_id for command in config.verification_plan.commands}
        self.assertEqual(
            {
                "repository-check", "python-v2", "extension-typecheck", "extension-tests",
                "extension-build", "extension-package", "extension-smoke", "app-server-e2e",
            },
            command_ids,
        )
        self.assertTrue(next(item for item in config.verification_plan.commands if item.command_id == "extension-package").release_only)
        self.assertTrue(next(item for item in config.verification_plan.commands if item.command_id == "app-server-e2e").release_only)

    def test_repository_can_generate_a_hash_bound_ready_manifest(self) -> None:
        tracked_manifest = json.loads(
            (REPOSITORY_ROOT / "docs/generated/v2-cutover-manifest.json").read_text(encoding="utf-8")
        )
        cache_root = REPOSITORY_ROOT / ".devweave" / "cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="release-contract-", dir=cache_root) as temporary:
            manifest_path = Path(temporary) / "v2-cutover-manifest.json"
            write_manifest(
                manifest_path,
                generate_manifest(REPOSITORY_ROOT, base_ref=tracked_manifest["base_ref"]),
            )
            report = CutoverFinalizer(REPOSITORY_ROOT, manifest_path).check()
        self.assertIn(report["status"], {"ready", "already_applied"})
        if report["status"] == "ready":
            self.assertEqual(6, report["pending_replacements"])
            self.assertGreater(report["pending_deletions"], 600)
            self.assertFalse(report["completion_record_ready"])
        else:
            self.assertEqual(6, report["completed_replacements"])
            self.assertGreater(report["completed_deletions"], 600)
            self.assertTrue(report["completion_record_ready"])


if __name__ == "__main__":
    unittest.main()

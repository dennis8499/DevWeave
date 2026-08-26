from __future__ import annotations

import hashlib
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

from devweave_v2.errors import DevWeaveError, ErrorCode
from devweave_v2.canonical import dumps
from devweave_v2.git_port import GitAdapter
from devweave_v2.git_transaction import GitTransaction
from devweave_v2.plan_store import PlanStore
from devweave_v2.run_git_coordinator import RunGitCoordinator
from devweave_v2.run_service import RunService
from devweave_v2.v1_export import V1Exporter


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=check, capture_output=True,
        text=True, encoding="utf-8", shell=False,
    )


class GitHarness:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="devweave-v2-git-")
        self.repo = Path(self.temp.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "DevWeave Test")
        git(self.repo, "config", "user.email", "devweave@example.test")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.txt").write_text("base\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(".devweave/runtime/\n", encoding="utf-8")
        git(self.repo, "add", "--", "src/app.txt", ".gitignore")
        git(self.repo, "commit", "-m", "base")
        self.adapter = GitAdapter(self.repo)
        self.transaction = GitTransaction(self.repo, self.adapter)

    def close(self) -> None:
        self.temp.cleanup()


class GitTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = GitHarness()

    def tearDown(self) -> None:
        self.h.close()

    def test_clean_preflight_creates_same_checkout_branch_and_keeps_base_ref(self) -> None:
        result = self.h.transaction.start_branch(run_id="run-001", slug="vertical-slice")
        self.assertEqual(self.h.adapter.branch(), result["run_branch"])
        self.assertEqual(self.h.adapter.resolve_ref("main"), result["base_ref"])
        self.assertNotEqual(self.h.adapter.branch(), "main")
        forbidden = {"push", "merge", "reset", "worktree", "pull"}
        self.assertFalse(any(call and call[0] in forbidden for call in self.h.adapter.invocations))

    def test_dirty_tracked_and_untracked_preflight_fail_closed(self) -> None:
        (self.h.repo / "src" / "app.txt").write_text("dirty\n", encoding="utf-8")
        (self.h.repo / "extra.txt").write_text("untracked\n", encoding="utf-8")
        with self.assertRaises(DevWeaveError) as blocked:
            self.h.transaction.preflight(run_id="run-001", slug="slice")
        self.assertEqual(blocked.exception.code, ErrorCode.BLOCKED)
        self.assertEqual(self.h.adapter.branch(), "main")

    def test_detached_head_and_branch_collision_are_blocked(self) -> None:
        head = self.h.adapter.head()
        git(self.h.repo, "checkout", "--detach", head)
        with self.assertRaises(DevWeaveError) as detached:
            self.h.transaction.preflight(run_id="run-001", slug="slice")
        self.assertEqual(detached.exception.code, ErrorCode.BLOCKED)
        git(self.h.repo, "switch", "main")
        git(self.h.repo, "branch", "devweave/run-001-slice")
        with self.assertRaises(DevWeaveError) as collision:
            self.h.transaction.preflight(run_id="run-001", slug="slice")
        self.assertEqual(collision.exception.code, ErrorCode.CONFLICT)

    def test_scoped_commit_blocks_unrelated_diff_and_preserves_base(self) -> None:
        info = self.h.transaction.start_branch(run_id="run-001", slug="slice")
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        (self.h.repo / "unrelated.txt").write_text("no\n", encoding="utf-8")
        with self.assertRaises(DevWeaveError) as unrelated:
            self.h.transaction.commit_slice(
                run_id="run-001", task_id="TASK-001", declared_paths=("src/**",), **info
            )
        self.assertEqual(unrelated.exception.code, ErrorCode.BLOCKED)
        (self.h.repo / "unrelated.txt").unlink()
        commit = self.h.transaction.commit_slice(
            run_id="run-001", task_id="TASK-001", declared_paths=("src/**",), **info
        )
        self.assertEqual(commit, self.h.adapter.head())
        self.assertEqual(self.h.adapter.resolve_ref("main"), info["base_ref"])

    def test_base_ref_drift_blocks_commit_without_staging_slice(self) -> None:
        info = self.h.transaction.start_branch(run_id="run-001", slug="slice")
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        git(self.h.repo, "branch", "-f", "main", "HEAD~0")
        # Force the base ref to a distinct commit using a temporary orphan-free commit.
        git(self.h.repo, "switch", "main")
        (self.h.repo / "base-only.txt").write_text("move\n", encoding="utf-8")
        git(self.h.repo, "add", "base-only.txt")
        git(self.h.repo, "commit", "-m", "move base")
        git(self.h.repo, "switch", info["run_branch"])
        with self.assertRaises(DevWeaveError) as drift:
            self.h.transaction.commit_slice(
                run_id="run-001", task_id="TASK-001", declared_paths=("src/**",), **info
            )
        self.assertEqual(drift.exception.code, ErrorCode.CONFLICT)
        self.assertEqual(self.h.adapter.staged_paths(), ())


class ProductionGitCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = GitHarness()
        self.info = self.h.transaction.start_branch(run_id="run-fixture", slug="slice")
        self.coordinator = RunGitCoordinator(self.h.repo, self.h.transaction)

    def tearDown(self) -> None:
        self.h.close()

    def start_service(
        self,
        *,
        store: PlanStore | None = None,
        coordinator: RunGitCoordinator | None = None,
    ) -> tuple[RunService, dict]:
        service = RunService(
            self.h.repo,
            store=store,
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=coordinator or self.coordinator,
        )
        draft = json.loads((ROOT / "fixtures" / "devweave_v2" / "run-plan-draft.json").read_text(encoding="utf-8"))
        draft["risk"] = "low"
        plan = service.host().run_start(draft, **self.info)
        plan = service.host().gate_decide(
            plan["run_id"], expected_revision=1, mutation_id="approve", gate_id="plan", approve=True
        )
        return service, plan

    def test_task_completion_commits_only_declared_slice_and_binds_commit(self) -> None:
        service, plan = self.start_service()
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        completed = service.agent().task_update(
            plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )
        commit_ref = completed["tasks"]["TASK-001"]["commit_ref"]
        commit_sha = self.h.adapter.resolve_ref(commit_ref)
        self.assertEqual(commit_sha, self.h.adapter.head())
        self.assertEqual(self.h.adapter.resolve_ref("main"), self.info["base_ref"])
        self.assertEqual(
            self.h.adapter.diff_paths(self.info["base_ref"]),
            ("docs/exec-plans/active/run-fixture.json", "src/app.txt"),
        )
        self.assertEqual(self.coordinator.changed_paths(completed), ("src/app.txt",))
        self.assertEqual(
            self.h.adapter.read_tree_file(commit_ref, "docs/exec-plans/active/run-fixture.json"),
            dumps(completed).encode("utf-8"),
        )
        journal = json.loads(
            (self.h.repo / ".devweave/runtime/run-fixture/task-commits/complete-task.json").read_text(encoding="utf-8")
        )
        self.assertEqual(journal["status"], "finalized")
        self.assertEqual(journal["checkpoint_ref"], commit_ref)
        self.assertEqual(journal["commit_sha"], commit_sha)

    def test_post_transition_plan_crash_retries_with_exactly_one_checkpoint_commit(self) -> None:
        armed = False

        def fault(stage: str, path: Path) -> None:
            if armed and stage == "after_replace":
                raise RuntimeError("crash-after-state")

        store = PlanStore(self.h.repo, fault_hook=fault)
        service, plan = self.start_service(store=store)
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        head_before_checkpoint = self.h.adapter.head()
        armed = True
        with self.assertRaisesRegex(RuntimeError, "crash-after-state"):
            service.agent().task_update(
                plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
            )
        self.assertEqual(self.h.adapter.head(), head_before_checkpoint)
        armed = False
        recovered = service.agent().task_update(
            plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )
        checkpoint_ref = recovered["tasks"]["TASK-001"]["commit_ref"]
        committed_head = self.h.adapter.resolve_ref(checkpoint_ref)
        self.assertEqual(self.h.adapter.head(), committed_head)
        self.assertEqual(self.h.adapter.parent(committed_head), head_before_checkpoint)

    def test_recovery_rejects_same_message_commit_that_escapes_journaled_slice(self) -> None:
        armed = {"value": False}

        def fault(stage: str, path: Path) -> None:
            if armed["value"] and stage == "after_replace":
                raise RuntimeError("crash-after-state")

        service, plan = self.start_service(store=PlanStore(self.h.repo, fault_hook=fault))
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        armed["value"] = True
        with self.assertRaisesRegex(RuntimeError, "crash-after-state"):
            service.agent().task_update(
                plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
            )
        (self.h.repo / "outside.txt").write_text("not-owned\n", encoding="utf-8")
        git(self.h.repo, "add", "--all")
        git(self.h.repo, "commit", "-m", "devweave(run-fixture): checkpoint task TASK-001")

        restarted = RunService(
            self.h.repo,
            store=PlanStore(self.h.repo),
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=RunGitCoordinator(self.h.repo, GitTransaction(self.h.repo, GitAdapter(self.h.repo))),
        )
        with self.assertRaises(DevWeaveError) as rejected:
            restarted.host().run_resume(plan["run_id"])
        self.assertEqual(rejected.exception.code, ErrorCode.CONFLICT)

    def _assert_checkpoint_fault_recovery(self, fault_stage: str) -> None:
        armed = {"value": False}

        def fault(stage: str, path: Path) -> None:
            if armed["value"] and stage == fault_stage:
                raise RuntimeError(f"crash-{stage}")

        coordinator = RunGitCoordinator(self.h.repo, self.h.transaction, fault_hook=fault)
        service, plan = self.start_service(coordinator=coordinator)
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        before_head = self.h.adapter.head()
        armed["value"] = True
        with self.assertRaisesRegex(RuntimeError, f"crash-{fault_stage}"):
            service.agent().task_update(
                plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
            )
        armed["value"] = False

        later = self.h.repo / "src" / "later.txt"
        later.write_text("later\n", encoding="utf-8")
        git(self.h.repo, "add", "--", "src/later.txt")
        git(self.h.repo, "commit", "-m", "later run commit")

        restarted_coordinator = RunGitCoordinator(self.h.repo, GitTransaction(self.h.repo, GitAdapter(self.h.repo)))
        restarted = RunService(
            self.h.repo,
            store=PlanStore(self.h.repo),
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=restarted_coordinator,
        )
        recovered = restarted.host().run_resume(plan["run_id"])
        checkpoint_ref = recovered["tasks"]["TASK-001"]["commit_ref"]
        checkpoint_sha = restarted_coordinator.git.resolve_ref(checkpoint_ref)
        self.assertEqual(restarted_coordinator.git.parent(checkpoint_sha), before_head)
        self.assertEqual(
            restarted_coordinator.git.read_tree_file(
                checkpoint_ref, "docs/exec-plans/active/run-fixture.json"
            ),
            dumps(recovered).encode("utf-8"),
        )
        messages = git(self.h.repo, "log", "--format=%s", f"{before_head}..HEAD").stdout.splitlines()
        self.assertEqual(messages.count("devweave(run-fixture): checkpoint task TASK-001"), 1)
        journal = json.loads(
            (self.h.repo / ".devweave/runtime/run-fixture/task-commits/complete-task.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(journal["status"], "finalized")
        self.assertEqual(journal["commit_sha"], checkpoint_sha)
        self.assertEqual(restarted_coordinator.git.status(), ())

    def test_checkpoint_commit_fault_recovers_after_head_advances(self) -> None:
        self._assert_checkpoint_fault_recovery("after_checkpoint_commit")

    def test_checkpoint_ref_fault_recovers_after_head_advances(self) -> None:
        self._assert_checkpoint_fault_recovery("after_checkpoint_ref")

    def test_checkpoint_journal_fault_recovers_after_head_advances(self) -> None:
        self._assert_checkpoint_fault_recovery("after_checkpoint_journal")

    def test_resume_restores_missing_active_plan_from_latest_checkpoint(self) -> None:
        service, plan = self.start_service()
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        completed = service.agent().task_update(
            plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )
        active = self.h.repo / "docs/exec-plans/active/run-fixture.json"
        active.unlink()
        restarted = RunService(
            self.h.repo,
            store=PlanStore(self.h.repo),
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=RunGitCoordinator(self.h.repo, GitTransaction(self.h.repo, GitAdapter(self.h.repo))),
        )
        recovered = restarted.host().run_resume(plan["run_id"])
        self.assertEqual(recovered, completed)
        self.assertEqual(active.read_bytes(), dumps(completed).encode("utf-8"))
        self.assertEqual(git(self.h.repo, "status", "--porcelain=v1").stdout, "")

    def test_planning_gate_checkpoint_contains_the_authoritative_decision(self) -> None:
        _, plan = self.start_service()
        gate_ref = plan["gates"]["plan"]["commit_ref"]
        self.assertEqual(self.h.adapter.resolve_ref(gate_ref), self.h.adapter.head())
        recorded = json.loads(
            self.h.adapter.read_tree_file(gate_ref, "docs/exec-plans/active/run-fixture.json").decode("utf-8")
        )
        self.assertEqual(recorded, plan)
        self.assertEqual(recorded["gates"]["plan"]["status"], "approved")
        self.assertEqual(recorded["gates"]["plan"]["commit_ref"], gate_ref)
        self.assertEqual(self.h.adapter.status(), ())

    def test_acceptance_archives_a_recoverable_plan_and_leaves_clean_next_run_preflight(self) -> None:
        service, plan = self.start_service()
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )

        class AlwaysCurrent:
            @staticmethod
            def report_is_current(*args, **kwargs) -> bool:
                return True

        service.verification_engine = AlwaysCurrent()  # type: ignore[assignment]

        def record_verification(candidate: dict) -> None:
            candidate["verification"] = {
                "status": "passed",
                "evidence_ids": ["EVID-1"],
                "current_report_id": "manual",
                "reports": {"manual": {"source_digest": "b" * 64}},
            }

        plan = service.mutate(plan["run_id"], 4, "record-current-verification", record_verification)
        plan = service.agent().completion_request(plan["run_id"], expected_revision=5, mutation_id="request-completion")
        completed = service.host().gate_decide(
            plan["run_id"], expected_revision=6, mutation_id="accept-run", gate_id="acceptance", approve=True
        )
        archive_ref = completed["archive_ref"]
        archive_path = "docs/exec-plans/completed/run-fixture.json"
        self.assertEqual(self.h.adapter.resolve_ref(archive_ref), self.h.adapter.head())
        self.assertEqual(self.h.adapter.read_tree_file(archive_ref, archive_path), dumps(completed).encode("utf-8"))
        self.assertTrue((self.h.repo / archive_path).is_file())
        self.assertFalse((self.h.repo / "docs/exec-plans/active/run-fixture.json").exists())
        self.assertEqual(self.h.adapter.status(), ())
        next_run = self.h.transaction.preflight(run_id="run-next", slug="next-slice")
        self.assertEqual(next_run["base_ref"], self.h.adapter.head())

        (self.h.repo / archive_path).unlink()
        restarted = RunService(
            self.h.repo,
            store=PlanStore(self.h.repo),
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=RunGitCoordinator(self.h.repo, GitTransaction(self.h.repo, GitAdapter(self.h.repo))),
        )
        recovered = restarted.host().run_resume(plan["run_id"])
        self.assertEqual(recovered, completed)
        self.assertEqual((self.h.repo / archive_path).read_bytes(), dumps(completed).encode("utf-8"))
        self.assertEqual(git(self.h.repo, "status", "--porcelain=v1").stdout, "")

    def test_archive_move_fault_is_reconciled_on_restart(self) -> None:
        armed = {"value": False}

        def fault(stage: str, path: Path) -> None:
            if armed["value"] and stage == "after_complete_move":
                raise RuntimeError("crash-after-archive-move")

        service, plan = self.start_service(store=PlanStore(self.h.repo, fault_hook=fault))
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )

        class AlwaysCurrent:
            @staticmethod
            def report_is_current(*args, **kwargs) -> bool:
                return True

        service.verification_engine = AlwaysCurrent()  # type: ignore[assignment]

        def record_verification(candidate: dict) -> None:
            candidate["verification"] = {
                "status": "passed",
                "evidence_ids": ["EVID-1"],
                "current_report_id": "manual",
                "reports": {"manual": {"source_digest": "b" * 64}},
            }

        plan = service.mutate(plan["run_id"], 4, "record-current-verification", record_verification)
        plan = service.agent().completion_request(plan["run_id"], expected_revision=5, mutation_id="request-completion")
        armed["value"] = True
        with self.assertRaisesRegex(RuntimeError, "crash-after-archive-move"):
            service.host().gate_decide(
                plan["run_id"], expected_revision=6, mutation_id="accept-run", gate_id="acceptance", approve=True
            )
        armed["value"] = False

        restarted_coordinator = RunGitCoordinator(self.h.repo, GitTransaction(self.h.repo, GitAdapter(self.h.repo)))
        restarted = RunService(
            self.h.repo,
            store=PlanStore(self.h.repo),
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=restarted_coordinator,
        )
        completed = restarted.host().run_resume(plan["run_id"])
        archive_path = self.h.repo / "docs/exec-plans/completed/run-fixture.json"
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(
            restarted_coordinator.git.read_tree_file(completed["archive_ref"], archive_path.relative_to(self.h.repo).as_posix()),
            dumps(completed).encode("utf-8"),
        )
        journal = json.loads(
            (self.h.repo / ".devweave/runtime/run-fixture/gate-commits/accept-run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(journal["status"], "finalized")
        self.assertEqual(restarted_coordinator.git.status(), ())

    def test_completed_state_replace_fault_archives_before_recovered_checkpoint(self) -> None:
        armed = {"value": False}

        def fault(stage: str, path: Path) -> None:
            if armed["value"] and stage == "after_replace":
                raise RuntimeError("crash-after-completed-state")

        service, plan = self.start_service(store=PlanStore(self.h.repo, fault_hook=fault))
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )

        class AlwaysCurrent:
            @staticmethod
            def report_is_current(*args, **kwargs) -> bool:
                return True

        service.verification_engine = AlwaysCurrent()  # type: ignore[assignment]

        def record_verification(candidate: dict) -> None:
            candidate["verification"] = {
                "status": "passed",
                "evidence_ids": ["EVID-1"],
                "current_report_id": "manual",
                "reports": {"manual": {"source_digest": "b" * 64}},
            }

        plan = service.mutate(plan["run_id"], 4, "record-current-verification", record_verification)
        plan = service.agent().completion_request(plan["run_id"], expected_revision=5, mutation_id="request-completion")
        before_acceptance = self.h.adapter.head()
        armed["value"] = True
        with self.assertRaisesRegex(RuntimeError, "crash-after-completed-state"):
            service.host().gate_decide(
                plan["run_id"], expected_revision=6, mutation_id="accept-run", gate_id="acceptance", approve=True
            )
        armed["value"] = False

        active_path = self.h.repo / "docs/exec-plans/active/run-fixture.json"
        completed_path = self.h.repo / "docs/exec-plans/completed/run-fixture.json"
        interrupted = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(interrupted["status"], "completed")
        self.assertFalse(completed_path.exists())
        self.assertEqual(self.h.adapter.head(), before_acceptance)

        restarted_coordinator = RunGitCoordinator(self.h.repo, GitTransaction(self.h.repo, GitAdapter(self.h.repo)))
        restarted = RunService(
            self.h.repo,
            store=PlanStore(self.h.repo),
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=restarted_coordinator,
        )
        completed = restarted.host().run_resume(plan["run_id"])
        checkpoint_sha = restarted_coordinator.git.resolve_ref(completed["archive_ref"])
        self.assertEqual(restarted_coordinator.git.parent(checkpoint_sha), before_acceptance)
        self.assertFalse(active_path.exists())
        self.assertEqual(completed_path.read_bytes(), dumps(completed).encode("utf-8"))
        self.assertEqual(
            restarted_coordinator.git.read_tree_file(completed["archive_ref"], completed_path.relative_to(self.h.repo).as_posix()),
            dumps(completed).encode("utf-8"),
        )
        journal_path = self.h.repo / ".devweave/runtime/run-fixture/gate-commits/accept-run.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "finalized")
        self.assertEqual(journal["commit_sha"], checkpoint_sha)
        self.assertEqual(journal["control_path"], "docs/exec-plans/completed/run-fixture.json")
        self.assertEqual(journal["plan_digest"], hashlib.sha256(dumps(completed).encode("utf-8")).hexdigest())
        messages = git(self.h.repo, "log", "--format=%s", f"{before_acceptance}..HEAD").stdout.splitlines()
        self.assertEqual(messages.count("devweave(run-fixture): checkpoint gate acceptance"), 1)
        self.assertEqual(restarted_coordinator.git.status(), ())

        head_after_recovery = restarted_coordinator.git.head()
        resumed_again = restarted.host().run_resume(plan["run_id"])
        self.assertEqual(resumed_again, completed)
        self.assertEqual(restarted_coordinator.git.head(), head_after_recovery)
        self.assertEqual(restarted_coordinator.git.status(), ())
        repeated_messages = git(self.h.repo, "log", "--format=%s", f"{before_acceptance}..HEAD").stdout.splitlines()
        self.assertEqual(repeated_messages.count("devweave(run-fixture): checkpoint gate acceptance"), 1)

    def test_unrelated_dirty_path_and_wrong_checkout_block_mutation_or_resume(self) -> None:
        service, plan = self.start_service()
        (self.h.repo / "outside.txt").write_text("no\n", encoding="utf-8")
        with self.assertRaises(DevWeaveError) as unrelated:
            service.agent().task_update(
                plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
            )
        self.assertEqual(unrelated.exception.code, ErrorCode.BLOCKED)
        (self.h.repo / "outside.txt").unlink()
        git(self.h.repo, "switch", "main")
        with self.assertRaises(DevWeaveError) as checkout:
            service.host().run_resume(plan["run_id"])
        self.assertEqual(checkout.exception.code, ErrorCode.CONFLICT)


class V1ExportTests(unittest.TestCase):
    def test_repository_v1_export_is_byte_stable_and_counts_recorded_history(self) -> None:
        recorded_base_ref = "3662d8622b46a1cab6931da988db3c4280def783"
        adapter = GitAdapter(ROOT)
        exporter = V1Exporter(adapter)
        before = git(ROOT, "status", "--porcelain=v1", "--untracked-files=all").stdout
        with tempfile.TemporaryDirectory(prefix="devweave-v1-export-a-") as first_dir, tempfile.TemporaryDirectory(prefix="devweave-v1-export-b-") as second_dir:
            first = exporter.write(recorded_base_ref, Path(first_dir))
            second = exporter.write(recorded_base_ref, Path(second_dir))
            self.assertEqual(first[0].read_bytes(), second[0].read_bytes())
            self.assertEqual(first[1].read_bytes(), second[1].read_bytes())
            payload = json.loads(first[0].read_text(encoding="utf-8"))
        after = git(ROOT, "status", "--porcelain=v1", "--untracked-files=all").stdout
        self.assertEqual(before, after)
        self.assertEqual(payload["summary"]["work_items"], 21)
        self.assertEqual(payload["summary"]["closed_work_items"], 21)
        self.assertEqual(payload["summary"]["evidence_files"], 411)
        self.assertFalse(payload["recovery"]["raw_data_copied"])
        self.assertEqual(payload["resolved_source_ref"], recorded_base_ref)


if __name__ == "__main__":
    unittest.main()

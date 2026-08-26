from __future__ import annotations

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

    def start_service(self, *, store: PlanStore | None = None) -> tuple[RunService, dict]:
        service = RunService(
            self.h.repo,
            store=store,
            clock=lambda: "2026-08-25T00:00:00Z",
            git_coordinator=self.coordinator,
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
        recovered = json.loads(self.h.adapter.read_tree_file(archive_ref, archive_path).decode("utf-8"))
        self.assertEqual(recovered, completed)

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

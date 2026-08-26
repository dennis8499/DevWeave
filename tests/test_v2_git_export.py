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
        self.assertEqual(commit_ref, self.h.adapter.head())
        self.assertEqual(self.h.adapter.resolve_ref("main"), self.info["base_ref"])
        self.assertEqual(self.h.adapter.diff_paths(self.info["base_ref"]), ("src/app.txt",))
        journal = json.loads(
            (self.h.repo / ".devweave/runtime/run-fixture/task-commits/complete-task.json").read_text(encoding="utf-8")
        )
        self.assertEqual(journal["status"], "finalized")

    def test_commit_then_plan_crash_retries_without_a_second_commit(self) -> None:
        armed = False

        def fault(stage: str, path: Path) -> None:
            if armed and stage == "before_replace":
                raise RuntimeError("crash-after-commit")

        store = PlanStore(self.h.repo, fault_hook=fault)
        service, plan = self.start_service(store=store)
        plan = service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        (self.h.repo / "src" / "app.txt").write_text("slice\n", encoding="utf-8")
        armed = True
        with self.assertRaisesRegex(RuntimeError, "crash-after-commit"):
            service.agent().task_update(
                plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
            )
        committed_head = self.h.adapter.head()
        armed = False
        recovered = service.agent().task_update(
            plan["run_id"], expected_revision=3, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )
        self.assertEqual(recovered["tasks"]["TASK-001"]["commit_ref"], committed_head)
        self.assertEqual(self.h.adapter.head(), committed_head)

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

"""Production Git ownership and crash-recoverable canonical checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Sequence, TYPE_CHECKING

from .canonical import dumps
from .checkpoint_proof import CheckpointProof
from .contract_utils import identifier
from .errors import DevWeaveError, ErrorCode
from .git_port import GitStatusEntry, path_matches
from .git_transaction import GitTransaction

if TYPE_CHECKING:
    from .plan_store import PlanStore

FaultHook = Callable[[str, Path], None]


class RunGitCoordinator:
    def __init__(
        self,
        repository: Path,
        transaction: GitTransaction,
        *,
        fault_hook: FaultHook | None = None,
    ) -> None:
        self.repository = repository.resolve()
        self.transaction = transaction
        self.git = transaction.git
        self.proof = CheckpointProof(self.git)
        self.runtime_root = self.repository / ".devweave" / "runtime"
        self._fault_hook = fault_hook

    def assert_run(
        self,
        plan: dict[str, Any],
        *,
        extra_paths: Sequence[str] = (),
        require_clean: bool = False,
    ) -> None:
        self.transaction.assert_run(
            run_branch=plan["run_branch"],
            base_branch=plan["base_branch"],
            base_ref=plan["base_ref"],
        )
        entries = self._source_status()
        if require_clean and entries:
            raise DevWeaveError(ErrorCode.BLOCKED, "This lifecycle operation requires a clean checkout.")
        governed = tuple(extra_paths) or self._active_task_paths(plan)
        allowed = (*governed, *self._control_paths(plan))
        changed = sorted({path for item in entries for path in (item.path, item.original_path) if path})
        unrelated = [path for path in changed if not path_matches(path, allowed)]
        if unrelated:
            raise DevWeaveError(
                ErrorCode.BLOCKED,
                "Working-tree changes escape the current task or canonical control paths.",
                {"paths": unrelated[:128]},
            )

    def changed_paths(self, plan: dict[str, Any]) -> tuple[str, ...]:
        self.assert_run(plan)
        controls = set(self._control_paths(plan))
        committed = {path for path in self.git.diff_paths(plan["base_ref"]) if path not in controls}
        dirty = {
            path
            for item in self._source_status()
            for path in (item.path, item.original_path)
            if path and path not in controls
        }
        return tuple(sorted(committed | dirty))

    def assert_resume_target(self, run_id: str) -> None:
        safe_run = identifier(run_id, "run_id")
        branches: set[str] = set()
        start_path = self.runtime_root / "start-journals" / f"{safe_run}.json"
        start = self._load_journal(start_path)
        if start is not None and isinstance(start.get("run_branch"), str):
            branches.add(start["run_branch"])
        run_root = self.runtime_root / safe_run
        for folder in ("task-commits", "gate-commits"):
            for path in (run_root / folder).glob("*.json"):
                journal = self._load_journal(path)
                if journal is not None and isinstance(journal.get("run_branch"), str):
                    branches.add(journal["run_branch"])
        if len(branches) > 1:
            raise DevWeaveError(ErrorCode.CONFLICT, "Run recovery journals disagree about the owned branch.")
        if branches and self.git.branch() not in branches:
            raise DevWeaveError(ErrorCode.CONFLICT, "Current checkout is not owned by the requested run.")

    def recover_run(self, run_id: str, store: "PlanStore") -> dict[str, Any]:
        """Reconcile every durable intent before returning or mutating authority state."""
        safe_run = identifier(run_id, "run_id")
        self.assert_resume_target(safe_run)
        journals = self._journal_items(safe_run)
        try:
            plan = store.load(safe_run)
        except DevWeaveError as exc:
            if exc.code != ErrorCode.NOT_FOUND:
                raise
            candidates: list[dict[str, Any]] = []
            for _, item in journals:
                if item.get("status") == "aborted":
                    continue
                commit = self.proof.existing_commit(item)
                if commit is not None:
                    candidates.append(self.proof.snapshot(item, commit)[0])
            if not candidates:
                raise
            plan = store.restore_missing(self._latest_snapshot(candidates))
        for path, journal in journals:
            status = journal.get("status")
            if status == "aborted":
                if journal.get("mutation_id") in plan["applied_mutations"]:
                    raise DevWeaveError(ErrorCode.CONFLICT, "An aborted checkpoint mutation is authoritative.")
                continue
            if (
                journal.get("kind") == "gate"
                and journal.get("subject_id") == "acceptance"
                and plan["status"] == "completed"
            ):
                # A crash may occur after the completed state replaces the active
                # plan but before gate_decide moves it into the completed archive.
                # Restore lifecycle placement before proving or creating the commit.
                store.complete(safe_run)
                plan = store.load(safe_run)
            commit = self.proof.existing_commit(journal)
            if status == "intent" and commit is None and journal.get("mutation_id") not in plan["applied_mutations"]:
                journal["status"] = "aborted"
                self._write_journal(path, journal)
                continue
            if status == "intent":
                control_path = self._completed_plan_path(plan) if plan["status"] == "completed" else self._active_plan_path(plan)
                checkpoint_ref = self._commit_checkpoint(plan, journal, control_path=control_path)
                self._finalize(safe_run, journal["kind"], journal["mutation_id"], checkpoint_ref)
            elif status == "committed":
                self.proof.validate_committed(journal)
                self._finalize(safe_run, journal["kind"], journal["mutation_id"], journal["checkpoint_ref"])
            elif status == "finalized":
                self.proof.validate_committed(journal)
            else:
                raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint journal status is invalid.")
            plan = store.load(safe_run)
        self.assert_run(plan)
        self.validate_plan_checkpoints(plan)
        return plan

    def validate_plan_checkpoints(self, plan: dict[str, Any]) -> None:
        journals = [item for _, item in self._journal_items(plan["run_id"])]
        by_ref: dict[str, dict[str, Any]] = {}
        snapshots: list[dict[str, Any]] = []
        for journal in journals:
            if journal.get("status") == "aborted":
                continue
            if journal.get("status") != "finalized":
                raise DevWeaveError(ErrorCode.CONFLICT, "Run has an unreconciled checkpoint journal.")
            self.proof.validate_committed(journal)
            snapshots.append(self.proof.snapshot(journal, journal["commit_sha"])[0])
            by_ref[journal["checkpoint_ref"]] = journal
        for task_id, task in plan["tasks"].items():
            if task["status"] == "completed":
                journal = by_ref.get(task["commit_ref"])
                if journal is None or (journal["kind"], journal["subject_id"]) != ("task", task_id):
                    raise DevWeaveError(ErrorCode.CONFLICT, "Completed task lacks finalized checkpoint proof.")
        for gate_id, gate in plan["gates"].items():
            if gate["status"] != "pending":
                journal = by_ref.get(gate["commit_ref"])
                if journal is None or (journal["kind"], journal["subject_id"]) != ("gate", gate_id):
                    raise DevWeaveError(ErrorCode.CONFLICT, "Decided gate lacks finalized checkpoint proof.")
        if plan["status"] == "completed":
            archive = by_ref.get(plan["archive_ref"])
            if archive is None or (archive["kind"], archive["subject_id"]) != ("gate", "acceptance"):
                raise DevWeaveError(ErrorCode.CONFLICT, "Completed run lacks finalized archive proof.")
        if snapshots:
            latest = self._latest_snapshot(snapshots)
            if plan["revision"] < latest["revision"] or (
                plan["revision"] == latest["revision"] and dumps(plan) != dumps(latest)
            ):
                raise DevWeaveError(ErrorCode.CONFLICT, "Working ExecPlan is older than or differs from its latest checkpoint.")

    @staticmethod
    def _latest_snapshot(candidates: Sequence[dict[str, Any]]) -> dict[str, Any]:
        revision = max(item["revision"] for item in candidates)
        latest = [item for item in candidates if item["revision"] == revision]
        canonical = {dumps(item) for item in latest}
        if len(canonical) != 1:
            raise DevWeaveError(ErrorCode.CONFLICT, "Latest checkpoint snapshots disagree at one revision.")
        return latest[0]

    def prepare_task(
        self,
        plan: dict[str, Any],
        *,
        task_id: str,
        mutation_id: str,
        expected_revision: int,
    ) -> str:
        safe_task = identifier(task_id, "task_id")
        task = plan["tasks"].get(safe_task)
        if task is None:
            raise DevWeaveError(ErrorCode.NOT_FOUND, "Task was not found.")
        if task["status"] != "in_progress":
            raise DevWeaveError(ErrorCode.CONFLICT, "Production task completion requires an in-progress task.")
        declarations = tuple(task["definition"]["declared_paths"])
        self.assert_run(plan, extra_paths=declarations)
        return self._prepare(
            plan,
            kind="task",
            subject_id=safe_task,
            mutation_id=mutation_id,
            expected_revision=expected_revision,
            message=f"devweave({plan['run_id']}): checkpoint task {safe_task}",
            allowed_paths=(*declarations, self._active_plan_path(plan)),
        )

    def checkpoint_task(
        self,
        plan: dict[str, Any],
        *,
        task_id: str,
        mutation_id: str,
        expected_revision: int,
    ) -> str:
        safe_task = identifier(task_id, "task_id")
        task = plan["tasks"].get(safe_task)
        if task is None or task["status"] != "completed":
            raise DevWeaveError(ErrorCode.CONFLICT, "Task checkpoint requires durable completed state.")
        journal = self._required_journal(plan["run_id"], "task", mutation_id)
        self._assert_journal(journal, plan, "task", safe_task, mutation_id, expected_revision)
        checkpoint_ref = journal["checkpoint_ref"]
        if task["commit_ref"] != checkpoint_ref:
            raise DevWeaveError(ErrorCode.CONFLICT, "Completed task does not name its deterministic checkpoint.")
        return self._commit_checkpoint(plan, journal, control_path=self._active_plan_path(plan))

    def finalize_task(self, run_id: str, mutation_id: str, checkpoint_ref: str) -> None:
        self._finalize(run_id, "task", mutation_id, checkpoint_ref)

    def prepare_gate(
        self,
        plan: dict[str, Any],
        *,
        gate_id: str,
        mutation_id: str,
        expected_revision: int,
    ) -> str:
        safe_gate = identifier(gate_id, "gate_id")
        if safe_gate not in plan["gates"] and not (safe_gate == "acceptance" and plan["risk"] == "low"):
            raise DevWeaveError(ErrorCode.INVALID_VALUE, "Gate is not required by current risk policy.")
        self.assert_run(plan, extra_paths=self._control_paths(plan))
        return self._prepare(
            plan,
            kind="gate",
            subject_id=safe_gate,
            mutation_id=mutation_id,
            expected_revision=expected_revision,
            message=f"devweave({plan['run_id']}): checkpoint gate {safe_gate}",
            allowed_paths=self._control_paths(plan),
        )

    def checkpoint_gate(
        self,
        plan: dict[str, Any],
        *,
        gate_id: str,
        mutation_id: str,
        expected_revision: int,
    ) -> str:
        safe_gate = identifier(gate_id, "gate_id")
        journal = self._required_journal(plan["run_id"], "gate", mutation_id)
        self._assert_journal(journal, plan, "gate", safe_gate, mutation_id, expected_revision)
        checkpoint_ref = journal["checkpoint_ref"]
        gate = plan["gates"].get(safe_gate)
        if gate is not None and gate["commit_ref"] != checkpoint_ref:
            raise DevWeaveError(ErrorCode.CONFLICT, "Decided gate does not name its deterministic checkpoint.")
        if plan["status"] == "completed" and plan["archive_ref"] != checkpoint_ref:
            raise DevWeaveError(ErrorCode.CONFLICT, "Completed run does not name its archive checkpoint.")
        control_path = self._completed_plan_path(plan) if plan["status"] == "completed" else self._active_plan_path(plan)
        return self._commit_checkpoint(plan, journal, control_path=control_path)

    def finalize_gate(self, run_id: str, mutation_id: str, checkpoint_ref: str) -> None:
        self._finalize(run_id, "gate", mutation_id, checkpoint_ref)

    def _prepare(
        self,
        plan: dict[str, Any],
        *,
        kind: str,
        subject_id: str,
        mutation_id: str,
        expected_revision: int,
        message: str,
        allowed_paths: Sequence[str],
    ) -> str:
        safe_mutation = identifier(mutation_id, "mutation_id")
        checkpoint_ref = self._checkpoint_ref(plan["run_id"], safe_mutation)
        journal_path = self._journal_path(plan["run_id"], kind, safe_mutation)
        expected = {
            "schema_version": 2,
            "kind": kind,
            "run_id": plan["run_id"],
            "subject_id": subject_id,
            "mutation_id": safe_mutation,
            "expected_revision": expected_revision,
            "run_branch": plan["run_branch"],
            "base_branch": plan["base_branch"],
            "base_ref": plan["base_ref"],
            "before_head": self.git.head(),
            "message": message,
            "allowed_paths": list(allowed_paths),
            "checkpoint_ref": checkpoint_ref,
            "status": "intent",
            "commit_sha": "",
            "control_path": "",
            "plan_digest": "",
        }
        journal = self._load_journal(journal_path)
        if journal is None:
            self._write_journal(journal_path, expected)
        elif journal.get("status") == "aborted":
            self._write_journal(journal_path, expected)
        else:
            self._assert_journal(journal, plan, kind, subject_id, safe_mutation, expected_revision)
            for field in ("message", "allowed_paths", "checkpoint_ref"):
                if journal.get(field) != expected[field]:
                    raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint journal does not match the retry.")
        return checkpoint_ref

    def _commit_checkpoint(self, plan: dict[str, Any], journal: dict[str, Any], *, control_path: str) -> str:
        checkpoint_ref = journal["checkpoint_ref"]
        if journal.get("status") in {"committed", "finalized"}:
            self.proof.validate_committed(journal)
            return checkpoint_ref

        commit_sha = self.proof.existing_commit(journal)
        if commit_sha is None:
            before_head = journal.get("before_head")
            if not isinstance(before_head, str) or self.git.head() != before_head:
                raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint journal cannot reconcile the current HEAD.")
            if (
                journal["mutation_id"] not in plan["applied_mutations"]
                or plan["revision"] != journal["expected_revision"] + 1
            ):
                raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint intent has no exact post-transition state.")
            commit_sha = self.transaction.commit_checkpoint(
                run_id=plan["run_id"],
                run_branch=plan["run_branch"],
                base_branch=plan["base_branch"],
                base_ref=plan["base_ref"],
                allowed_paths=tuple(journal["allowed_paths"]),
                message=journal["message"],
            )
            self._fault("after_checkpoint_commit", self._journal_path(plan["run_id"], journal["kind"], journal["mutation_id"]))
        snapshot, stored_path, stored_digest = self.proof.snapshot(journal, commit_sha)
        if plan["revision"] < snapshot["revision"] or journal["mutation_id"] not in plan["applied_mutations"]:
            raise DevWeaveError(ErrorCode.CONFLICT, "Working ExecPlan does not contain the checkpoint mutation.")
        if plan["revision"] == snapshot["revision"] and dumps(plan) != dumps(snapshot):
            raise DevWeaveError(ErrorCode.CONFLICT, "Working ExecPlan differs from its checkpoint state.")
        self.git.update_ref(checkpoint_ref, commit_sha)
        self._fault("after_checkpoint_ref", self._journal_path(plan["run_id"], journal["kind"], journal["mutation_id"]))
        if stored_path != control_path and plan["revision"] == snapshot["revision"]:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint control path differs from the lifecycle transition.")
        journal.update({
            "status": "committed",
            "commit_sha": commit_sha,
            "control_path": stored_path,
            "plan_digest": stored_digest,
        })
        journal_path = self._journal_path(plan["run_id"], journal["kind"], journal["mutation_id"])
        self._write_journal(journal_path, journal)
        self._fault("after_checkpoint_journal", journal_path)
        return checkpoint_ref

    def _finalize(self, run_id: str, kind: str, mutation_id: str, checkpoint_ref: str) -> None:
        path = self._journal_path(run_id, kind, mutation_id)
        journal = self._load_journal(path)
        if journal is None or journal.get("checkpoint_ref") != checkpoint_ref or journal.get("status") not in {"committed", "finalized"}:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint journal is unavailable during finalization.")
        journal["status"] = "finalized"
        self._write_journal(path, journal)

    def _assert_journal(
        self,
        journal: dict[str, Any],
        plan: dict[str, Any],
        kind: str,
        subject_id: str,
        mutation_id: str,
        expected_revision: int,
    ) -> None:
        expected = {
            "schema_version": 2,
            "kind": kind,
            "run_id": plan["run_id"],
            "subject_id": subject_id,
            "mutation_id": identifier(mutation_id, "mutation_id"),
            "expected_revision": expected_revision,
            "run_branch": plan["run_branch"],
            "base_branch": plan["base_branch"],
            "base_ref": plan["base_ref"],
            "checkpoint_ref": self._checkpoint_ref(plan["run_id"], mutation_id),
        }
        if any(journal.get(field) != value for field, value in expected.items()):
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint journal does not match the lifecycle mutation.")
        if journal.get("status") not in {"intent", "committed", "finalized", "aborted"}:
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint journal status is invalid.")

    def _required_journal(self, run_id: str, kind: str, mutation_id: str) -> dict[str, Any]:
        journal = self._load_journal(self._journal_path(run_id, kind, mutation_id))
        if journal is None:
            raise DevWeaveError(ErrorCode.CONFLICT, "Durable checkpoint intent is missing.")
        return journal

    def _source_status(self) -> tuple[GitStatusEntry, ...]:
        return tuple(self.git.status())

    @staticmethod
    def _active_plan_path(plan: dict[str, Any]) -> str:
        return f"docs/exec-plans/active/{plan['run_id']}.json"

    @staticmethod
    def _completed_plan_path(plan: dict[str, Any]) -> str:
        return f"docs/exec-plans/completed/{plan['run_id']}.json"

    @classmethod
    def _control_paths(cls, plan: dict[str, Any]) -> tuple[str, str]:
        return cls._active_plan_path(plan), cls._completed_plan_path(plan)

    @staticmethod
    def _active_task_paths(plan: dict[str, Any]) -> tuple[str, ...]:
        pending = plan.get("pending_decision")
        decision_blocked = (
            pending.get("blocking_task_id")
            if isinstance(pending, dict) and pending.get("previous_task_status") == "in_progress"
            else None
        )
        active = [
            tuple(value["definition"]["declared_paths"])
            for task_id, value in plan["tasks"].items()
            if value["status"] == "in_progress" or (value["status"] == "blocked" and task_id == decision_blocked)
        ]
        if len(active) > 1:
            raise DevWeaveError(ErrorCode.CONFLICT, "Only one task may be in progress in a writable run.")
        return active[0] if active else ()

    @staticmethod
    def _checkpoint_ref(run_id: str, mutation_id: str) -> str:
        run_token = hashlib.sha256(identifier(run_id, "run_id").encode("utf-8")).hexdigest()[:16]
        mutation_token = hashlib.sha256(identifier(mutation_id, "mutation_id").encode("utf-8")).hexdigest()[:16]
        return f"refs/devweave/checkpoints/{run_token}/{mutation_token}"

    def _journal_path(self, run_id: str, kind: str, mutation_id: str) -> Path:
        folder = "task-commits" if kind == "task" else "gate-commits"
        return self.runtime_root / identifier(run_id, "run_id") / folder / f"{identifier(mutation_id, 'mutation_id')}.json"

    def _journal_items(self, run_id: str) -> tuple[tuple[Path, dict[str, Any]], ...]:
        run_root = self.runtime_root / identifier(run_id, "run_id")
        result: list[tuple[Path, dict[str, Any]]] = []
        for folder in ("task-commits", "gate-commits"):
            for path in (run_root / folder).glob("*.json"):
                journal = self._load_journal(path)
                if journal is not None:
                    result.append((path, journal))
        return tuple(sorted(result, key=lambda item: (item[1].get("expected_revision", -1), item[0].as_posix())))

    def _fault(self, stage: str, path: Path) -> None:
        if self._fault_hook is not None:
            self._fault_hook(stage, path)

    @staticmethod
    def _load_journal(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint journal is malformed.") from exc
        if not isinstance(value, dict):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "Checkpoint journal must be an object.")
        return value

    @staticmethod
    def _write_journal(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(dumps(value).encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

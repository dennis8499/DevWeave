"""Production Git ownership and crash-recoverable canonical checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Sequence

from .canonical import dumps
from .contract_utils import identifier
from .errors import DevWeaveError, ErrorCode
from .git_port import GitStatusEntry, path_matches
from .git_transaction import GitTransaction


class RunGitCoordinator:
    def __init__(self, repository: Path, transaction: GitTransaction) -> None:
        self.repository = repository.resolve()
        self.transaction = transaction
        self.git = transaction.git
        self.runtime_root = self.repository / ".devweave" / "runtime"

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
        else:
            self._assert_journal(journal, plan, kind, subject_id, safe_mutation, expected_revision)
            for field in ("message", "allowed_paths", "checkpoint_ref"):
                if journal.get(field) != expected[field]:
                    raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint journal does not match the retry.")
        return checkpoint_ref

    def _commit_checkpoint(self, plan: dict[str, Any], journal: dict[str, Any], *, control_path: str) -> str:
        checkpoint_ref = journal["checkpoint_ref"]
        if journal.get("status") in {"committed", "finalized"}:
            commit_sha = journal.get("commit_sha")
            if not isinstance(commit_sha, str) or not self.git.is_ancestor(commit_sha, self.git.head()):
                raise DevWeaveError(ErrorCode.CONFLICT, "Committed checkpoint is not in current run history.")
            if self.git.resolve_ref(checkpoint_ref) != commit_sha:
                raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint ref no longer matches its journal.")
            stored_path = journal.get("control_path")
            stored_digest = journal.get("plan_digest")
            if not isinstance(stored_path, str) or not isinstance(stored_digest, str):
                raise DevWeaveError(ErrorCode.INVALID_JSON, "Committed checkpoint journal lacks its plan binding.")
            self._assert_checkpoint_digest(commit_sha, stored_path, stored_digest)
            return checkpoint_ref

        before_head = journal.get("before_head")
        if not isinstance(before_head, str):
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint journal has no valid starting HEAD.")
        current_head = self.git.head()
        if current_head == before_head:
            commit_sha = self.transaction.commit_checkpoint(
                run_id=plan["run_id"],
                run_branch=plan["run_branch"],
                base_branch=plan["base_branch"],
                base_ref=plan["base_ref"],
                allowed_paths=tuple(journal["allowed_paths"]),
                message=journal["message"],
            )
        elif self.git.parent(current_head) == before_head and self.git.commit_message(current_head) == journal["message"]:
            commit_sha = current_head
        else:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint journal cannot reconcile the current HEAD.")
        self.git.update_ref(checkpoint_ref, commit_sha)
        self._assert_checkpoint_content(plan, commit_sha, control_path)
        journal.update({
            "status": "committed",
            "commit_sha": commit_sha,
            "control_path": control_path,
            "plan_digest": hashlib.sha256(dumps(plan).encode("utf-8")).hexdigest(),
        })
        self._write_journal(self._journal_path(plan["run_id"], journal["kind"], journal["mutation_id"]), journal)
        return checkpoint_ref

    def _assert_checkpoint_content(self, plan: dict[str, Any], commit_sha: str, control_path: str) -> None:
        expected = dumps(plan).encode("utf-8")
        try:
            actual = self.git.read_tree_file(commit_sha, control_path)
        except DevWeaveError as exc:
            raise DevWeaveError(
                ErrorCode.CONFLICT,
                "Checkpoint commit does not contain the post-transition canonical ExecPlan.",
                {"path": control_path},
            ) from exc
        if actual != expected:
            raise DevWeaveError(
                ErrorCode.CONFLICT,
                "Checkpoint ExecPlan bytes differ from authoritative post-transition state.",
                {"path": control_path},
            )

    def _assert_checkpoint_digest(self, commit_sha: str, control_path: str, expected_digest: str) -> None:
        if len(expected_digest) != 64 or any(character not in "0123456789abcdef" for character in expected_digest):
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint journal plan digest is invalid.")
        try:
            actual = self.git.read_tree_file(commit_sha, control_path)
        except DevWeaveError as exc:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint commit lost its canonical ExecPlan.") from exc
        if hashlib.sha256(actual).hexdigest() != expected_digest:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint commit no longer matches its journal plan digest.")

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
        if journal.get("status") not in {"intent", "committed", "finalized"}:
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

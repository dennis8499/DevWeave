"""Production Git ownership checks and retry-safe task slice commits."""

from __future__ import annotations

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
        entries = self._source_status(plan)
        if require_clean and entries:
            raise DevWeaveError(ErrorCode.BLOCKED, "This lifecycle operation requires a clean source checkout.")
        allowed = tuple(extra_paths) or self._active_task_paths(plan)
        changed = sorted({path for item in entries for path in (item.path, item.original_path) if path})
        unrelated = [path for path in changed if not path_matches(path, allowed)]
        if unrelated:
            raise DevWeaveError(
                ErrorCode.BLOCKED,
                "Working-tree changes escape the current task or verification declaration.",
                {"paths": unrelated[:128]},
            )

    def changed_paths(self, plan: dict[str, Any]) -> tuple[str, ...]:
        self.assert_run(plan)
        committed = set(self.git.diff_paths(plan["base_ref"]))
        dirty = {
            path
            for item in self._source_status(plan)
            for path in (item.path, item.original_path)
            if path
        }
        return tuple(sorted(committed | dirty))

    def complete_task(self, plan: dict[str, Any], *, task_id: str, mutation_id: str) -> str:
        safe_task = identifier(task_id, "task_id")
        safe_mutation = identifier(mutation_id, "mutation_id")
        task = plan["tasks"].get(safe_task)
        if task is None:
            raise DevWeaveError(ErrorCode.NOT_FOUND, "Task was not found.")
        if task["status"] != "in_progress":
            raise DevWeaveError(ErrorCode.CONFLICT, "Production task completion requires an in-progress task.")
        declarations = tuple(task["definition"]["declared_paths"])
        self.assert_run(plan, extra_paths=declarations)
        journal_path = self._journal_path(plan["run_id"], safe_mutation)
        expected = {
            "schema_version": 2,
            "run_id": plan["run_id"],
            "task_id": safe_task,
            "mutation_id": safe_mutation,
            "expected_revision": plan["revision"],
            "before_head": self.git.head(),
            "message": f"devweave({plan['run_id']}): complete {safe_task}",
            "declared_paths": list(declarations),
            "status": "intent",
            "commit_ref": "",
        }
        journal = self._load_journal(journal_path)
        if journal is None:
            journal = expected
            self._write_journal(journal_path, journal)
        else:
            for field in ("schema_version", "run_id", "task_id", "mutation_id", "expected_revision", "message", "declared_paths"):
                if journal.get(field) != expected[field]:
                    raise DevWeaveError(ErrorCode.CONFLICT, "Task commit journal does not match the retry.")
        if journal.get("status") in {"committed", "finalized"}:
            commit_ref = journal.get("commit_ref")
            if not isinstance(commit_ref, str) or self.git.head() != commit_ref:
                raise DevWeaveError(ErrorCode.CONFLICT, "Committed task journal no longer matches HEAD.")
            return commit_ref
        before_head = journal.get("before_head")
        if not isinstance(before_head, str):
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Task commit journal has no valid starting HEAD.")
        current_head = self.git.head()
        if current_head == before_head:
            commit_ref = self.transaction.commit_slice(
                run_id=plan["run_id"],
                task_id=safe_task,
                run_branch=plan["run_branch"],
                base_branch=plan["base_branch"],
                base_ref=plan["base_ref"],
                declared_paths=declarations,
                ignored_paths=(self._active_plan_path(plan),),
            )
        elif self.git.parent(current_head) == before_head and self.git.commit_message(current_head) == journal["message"]:
            commit_ref = current_head
        else:
            raise DevWeaveError(ErrorCode.CONFLICT, "Task commit journal cannot reconcile the current HEAD.")
        journal.update({"status": "committed", "commit_ref": commit_ref})
        self._write_journal(journal_path, journal)
        return commit_ref

    def finalize_task(self, run_id: str, mutation_id: str, commit_ref: str) -> None:
        path = self._journal_path(run_id, mutation_id)
        journal = self._load_journal(path)
        if journal is None or journal.get("commit_ref") != commit_ref:
            raise DevWeaveError(ErrorCode.CONFLICT, "Task commit journal is unavailable during finalization.")
        journal["status"] = "finalized"
        self._write_journal(path, journal)

    def _source_status(self, plan: dict[str, Any]) -> tuple[GitStatusEntry, ...]:
        control_path = self._active_plan_path(plan)
        return tuple(
            item for item in self.git.status()
            if item.path != control_path and item.original_path != control_path
        )

    @staticmethod
    def _active_plan_path(plan: dict[str, Any]) -> str:
        return f"docs/exec-plans/active/{plan['run_id']}.json"

    @staticmethod
    def _active_task_paths(plan: dict[str, Any]) -> tuple[str, ...]:
        active = [
            tuple(value["definition"]["declared_paths"])
            for value in plan["tasks"].values()
            if value["status"] == "in_progress"
        ]
        if len(active) > 1:
            raise DevWeaveError(ErrorCode.CONFLICT, "Only one task may be in progress in a writable run.")
        return active[0] if active else ()

    def _journal_path(self, run_id: str, mutation_id: str) -> Path:
        return self.runtime_root / identifier(run_id, "run_id") / "task-commits" / f"{identifier(mutation_id, 'mutation_id')}.json"

    @staticmethod
    def _load_journal(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Task commit journal is malformed.") from exc
        if not isinstance(value, dict):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "Task commit journal must be an object.")
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

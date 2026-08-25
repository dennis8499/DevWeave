"""Atomic canonical ExecPlan persistence with optimistic concurrency."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

from .canonical import dumps
from .contract_utils import identifier
from .errors import DevWeaveError, ErrorCode
from .run_state import validate_exec_plan

Mutation = Callable[[dict[str, Any]], None]
FaultHook = Callable[[str, Path], None]


class PlanStore:
    """Owns durable plan replacement; callers never write plan JSON directly."""

    def __init__(self, repository: Path, *, fault_hook: FaultHook | None = None) -> None:
        self.repository = repository.resolve()
        self.active_root = self.repository / "docs" / "exec-plans" / "active"
        self.completed_root = self.repository / "docs" / "exec-plans" / "completed"
        self._fault_hook = fault_hook
        self._lock = threading.RLock()

    def path_for(self, run_id: str, *, completed: bool = False) -> Path:
        safe_id = identifier(run_id, "run_id")
        root = self.completed_root if completed else self.active_root
        return root / f"{safe_id}.json"

    def exists(self, run_id: str) -> bool:
        return self.path_for(run_id).is_file() or self.path_for(run_id, completed=True).is_file()

    def create(self, plan: dict[str, Any]) -> dict[str, Any]:
        validated = validate_exec_plan(copy.deepcopy(plan))
        path = self.path_for(validated["run_id"])
        with self._lock:
            if self.exists(validated["run_id"]):
                raise DevWeaveError(ErrorCode.CONFLICT, "Run already exists.", {"run_id": validated["run_id"]})
            self._atomic_replace(path, validated)
        return copy.deepcopy(validated)

    def load(self, run_id: str) -> dict[str, Any]:
        path = self.path_for(run_id)
        if not path.is_file():
            completed = self.path_for(run_id, completed=True)
            if completed.is_file():
                path = completed
            else:
                raise DevWeaveError(ErrorCode.NOT_FOUND, "Run was not found.", {"run_id": run_id})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Canonical ExecPlan cannot be read.", {"run_id": run_id}) from exc
        return copy.deepcopy(validate_exec_plan(raw))

    def mutate(
        self,
        run_id: str,
        *,
        expected_revision: int,
        mutation_id: str,
        now: str,
        mutation: Mutation,
    ) -> dict[str, Any]:
        key = identifier(mutation_id, "mutation_id")
        with self._lock:
            current = self.load(run_id)
            if key in current["applied_mutations"]:
                return current
            if current["revision"] != expected_revision:
                raise DevWeaveError(
                    ErrorCode.STALE_REVISION,
                    "Mutation expected a stale run revision.",
                    {"expected": expected_revision, "actual": current["revision"], "run_id": run_id},
                )
            candidate = copy.deepcopy(current)
            mutation(candidate)
            candidate["revision"] = expected_revision + 1
            candidate["updated_at"] = now
            candidate["applied_mutations"].append(key)
            if len(candidate["applied_mutations"]) > 512:
                candidate["applied_mutations"] = candidate["applied_mutations"][-512:]
            validated = validate_exec_plan(candidate)
            self._atomic_replace(self.path_for(run_id), validated)
            return copy.deepcopy(validated)

    def complete(self, run_id: str) -> Path:
        with self._lock:
            plan = self.load(run_id)
            if plan["status"] != "completed":
                raise DevWeaveError(ErrorCode.CONFLICT, "Only completed runs can be archived.")
            source = self.path_for(run_id)
            target = self.path_for(run_id, completed=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.read_bytes() == source.read_bytes():
                    source.unlink()
                    return target
                raise DevWeaveError(ErrorCode.CONFLICT, "Completed run archive already exists.")
            os.replace(source, target)
            return target

    def _atomic_replace(self, path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = dumps(value).encode("utf-8")
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            if self._fault_hook:
                self._fault_hook("before_replace", path)
            os.replace(temporary, path)
            temporary = None
            if self._fault_hook:
                self._fault_hook("after_replace", path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

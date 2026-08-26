"""Crash-recovery journal for the branch-before-plan run-start boundary."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .canonical import dumps
from .contract_utils import identifier
from .errors import DevWeaveError, ErrorCode


class RunStartJournal:
    def __init__(self, repository: Path) -> None:
        self.root = repository.resolve() / ".devweave" / "runtime" / "start-journals"

    def path_for(self, run_id: str) -> Path:
        return self.root / f"{identifier(run_id, 'run_id')}.json"

    def load(self, run_id: str) -> dict[str, Any] | None:
        path = self.path_for(run_id)
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Run-start recovery journal is malformed.") from exc
        if not isinstance(value, dict):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "Run-start recovery journal must be an object.")
        return value

    def begin(self, value: dict[str, Any]) -> dict[str, Any]:
        existing = self.load(value["run_id"])
        if existing is not None:
            return existing
        self._write(self.path_for(value["run_id"]), value)
        return value

    def mark(self, value: dict[str, Any], status: str) -> dict[str, Any]:
        updated = dict(value)
        updated["status"] = status
        self._write(self.path_for(updated["run_id"]), updated)
        return updated

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> None:
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

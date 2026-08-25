"""Ignored full verification reports; canonical plans retain bounded summaries."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .canonical import dumps
from .contract_utils import identifier
from .errors import DevWeaveError, ErrorCode


class VerificationReportStore:
    def __init__(self, repository: Path, *, max_bytes: int = 5_000_000) -> None:
        self.repository = repository.resolve()
        self.root = self.repository / ".devweave" / "runtime"
        self.max_bytes = max_bytes

    def path_for(self, run_id: str, mutation_id: str) -> Path:
        return self.root / identifier(run_id, "run_id") / "verification" / f"{identifier(mutation_id, 'mutation_id')}.json"

    def load(self, run_id: str, mutation_id: str) -> dict[str, Any] | None:
        path = self.path_for(run_id, mutation_id)
        if not path.is_file():
            return None
        raw = path.read_bytes()
        if len(raw) > self.max_bytes:
            raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Stored verification report exceeds its limit.")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Stored verification report is malformed.") from exc
        if not isinstance(value, dict):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "Stored verification report must be an object.")
        return value

    def save_once(self, run_id: str, mutation_id: str, report: dict[str, Any]) -> dict[str, Any]:
        existing = self.load(run_id, mutation_id)
        if existing is not None:
            return existing
        path = self.path_for(run_id, mutation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = dumps(report).encode("utf-8")
        if len(encoded) > self.max_bytes:
            raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Verification report exceeds its storage limit.")
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return report

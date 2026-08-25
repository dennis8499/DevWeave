"""Stable, machine-readable DevWeave V2 errors."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Mapping


class ErrorCode(StrEnum):
    INVALID_ARGUMENT = "DEVWEAVE_INVALID_ARGUMENT"
    INVALID_JSON = "DEVWEAVE_INVALID_JSON"
    INVALID_TYPE = "DEVWEAVE_INVALID_TYPE"
    INVALID_VALUE = "DEVWEAVE_INVALID_VALUE"
    UNKNOWN_FIELD = "DEVWEAVE_UNKNOWN_FIELD"
    REQUIRED_FIELD = "DEVWEAVE_REQUIRED_FIELD"
    SCHEMA_VERSION = "DEVWEAVE_SCHEMA_VERSION"
    BOUND_EXCEEDED = "DEVWEAVE_BOUND_EXCEEDED"
    PATH_OUTSIDE_REPOSITORY = "DEVWEAVE_PATH_OUTSIDE_REPOSITORY"
    NOT_FOUND = "DEVWEAVE_NOT_FOUND"
    CONFLICT = "DEVWEAVE_CONFLICT"
    STALE_REVISION = "DEVWEAVE_STALE_REVISION"
    FORBIDDEN = "DEVWEAVE_FORBIDDEN"
    GATE_REQUIRED = "DEVWEAVE_GATE_REQUIRED"
    BLOCKED = "DEVWEAVE_BLOCKED"
    COMMAND_FAILED = "DEVWEAVE_COMMAND_FAILED"
    PROTOCOL_ERROR = "DEVWEAVE_PROTOCOL_ERROR"
    CODEX_UNAVAILABLE = "DEVWEAVE_CODEX_UNAVAILABLE"
    NOT_IMPLEMENTED = "DEVWEAVE_NOT_IMPLEMENTED"
    INTERNAL = "DEVWEAVE_INTERNAL"


class DevWeaveError(Exception):
    """Expected domain failure safe to expose through a bounded envelope."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


class ContractError(DevWeaveError):
    """A public contract failed strict validation."""

"""Canonical JSON utilities used for fingerprints and durable state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import ContractError, ErrorCode


def primitive(value: Any) -> Any:
    """Convert supported typed values to deterministic JSON primitives."""
    if is_dataclass(value):
        return primitive(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [primitive(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ContractError(
        ErrorCode.INVALID_TYPE,
        "Value cannot be represented by the canonical JSON contract.",
        {"python_type": type(value).__name__},
    )


def dumps(value: Any) -> str:
    """Serialize with stable key ordering, UTF-8 text, and a final newline."""
    try:
        encoded = json.dumps(
            primitive(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContractError(
            ErrorCode.INVALID_JSON,
            "Value is not valid canonical JSON.",
        ) from exc
    return encoded + "\n"


def loads(text: str, *, max_bytes: int = 1_000_000) -> Any:
    raw = text.encode("utf-8")
    if len(raw) > max_bytes:
        raise ContractError(
            ErrorCode.BOUND_EXCEEDED,
            "JSON payload exceeds the configured byte limit.",
            {"actual_bytes": len(raw), "max_bytes": max_bytes},
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractError(
            ErrorCode.INVALID_JSON,
            "Payload is not valid JSON.",
            {"line": exc.lineno, "column": exc.colno},
        ) from exc


def sha256(value: Any) -> str:
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def write_bytes(path: Path, value: Any) -> bytes:
    """Return canonical bytes for adapters that own an atomic write."""
    del path  # The storage adapter owns path containment and replacement.
    return dumps(value).encode("utf-8")

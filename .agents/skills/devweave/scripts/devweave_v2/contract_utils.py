"""Strict validators shared by public schema implementations."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping, TypeVar

from .errors import ContractError, ErrorCode
from .version import SCHEMA_VERSION

MAX_TEXT = 8_192
MAX_ITEMS = 256
MAX_PATH = 512
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
TEnum = TypeVar("TEnum", bound=Enum)


def strict_object(
    value: Any,
    *,
    name: str,
    required: Iterable[str],
    optional: Iterable[str] = (),
    versioned: bool = False,
) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(
            ErrorCode.INVALID_TYPE,
            f"{name} must be a JSON object.",
            {"field": name},
        )
    required_set = set(required)
    if versioned:
        required_set.add("schema_version")
    allowed = required_set | set(optional)
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(
            ErrorCode.UNKNOWN_FIELD,
            f"{name} contains unknown fields.",
            {"field": name, "unknown_fields": unknown},
        )
    missing = sorted(required_set - set(value))
    if missing:
        raise ContractError(
            ErrorCode.REQUIRED_FIELD,
            f"{name} is missing required fields.",
            {"field": name, "missing_fields": missing},
        )
    if versioned:
        version = integer(value["schema_version"], f"{name}.schema_version", minimum=0)
        if version != SCHEMA_VERSION:
            raise ContractError(
                ErrorCode.SCHEMA_VERSION,
                f"{name} requires schema_version {SCHEMA_VERSION}.",
                {"actual": version, "expected": SCHEMA_VERSION},
            )
    return value


def text(
    value: Any,
    field: str,
    *,
    minimum: int = 1,
    maximum: int = MAX_TEXT,
) -> str:
    if not isinstance(value, str):
        raise ContractError(ErrorCode.INVALID_TYPE, f"{field} must be a string.", {"field": field})
    size = len(value)
    if size < minimum or size > maximum:
        raise ContractError(
            ErrorCode.BOUND_EXCEEDED,
            f"{field} length is outside its allowed bounds.",
            {"field": field, "actual": size, "minimum": minimum, "maximum": maximum},
        )
    return value


def identifier(value: Any, field: str) -> str:
    result = text(value, field, maximum=128)
    if not IDENTIFIER.fullmatch(result):
        raise ContractError(
            ErrorCode.INVALID_VALUE,
            f"{field} is not a valid identifier.",
            {"field": field},
        )
    return result


def integer(value: Any, field: str, *, minimum: int = 0, maximum: int = 2**31 - 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(ErrorCode.INVALID_TYPE, f"{field} must be an integer.", {"field": field})
    if value < minimum or value > maximum:
        raise ContractError(
            ErrorCode.BOUND_EXCEEDED,
            f"{field} is outside its allowed bounds.",
            {"field": field, "actual": value, "minimum": minimum, "maximum": maximum},
        )
    return value


def boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(ErrorCode.INVALID_TYPE, f"{field} must be a boolean.", {"field": field})
    return value


def sequence(value: Any, field: str, *, minimum: int = 0, maximum: int = MAX_ITEMS) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(ErrorCode.INVALID_TYPE, f"{field} must be an array.", {"field": field})
    if len(value) < minimum or len(value) > maximum:
        raise ContractError(
            ErrorCode.BOUND_EXCEEDED,
            f"{field} item count is outside its allowed bounds.",
            {"field": field, "actual": len(value), "minimum": minimum, "maximum": maximum},
        )
    return value


def strings(value: Any, field: str, *, minimum: int = 0, maximum: int = MAX_ITEMS) -> tuple[str, ...]:
    items = sequence(value, field, minimum=minimum, maximum=maximum)
    result = tuple(text(item, f"{field}[{index}]") for index, item in enumerate(items))
    if len(set(result)) != len(result):
        raise ContractError(ErrorCode.INVALID_VALUE, f"{field} must not contain duplicates.", {"field": field})
    return result


def enum_value(value: Any, field: str, enum_type: type[TEnum]) -> TEnum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(
            ErrorCode.INVALID_VALUE,
            f"{field} has an unsupported value.",
            {"field": field, "allowed": [item.value for item in enum_type]},
        ) from exc


def relative_path(value: Any, field: str) -> str:
    result = text(value, field, maximum=MAX_PATH).replace("\\", "/")
    path = PurePosixPath(result)
    if path.is_absolute() or not result or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError(
            ErrorCode.PATH_OUTSIDE_REPOSITORY,
            f"{field} must be a normalized repository-relative path.",
            {"field": field},
        )
    return path.as_posix()


def relative_paths(value: Any, field: str, *, minimum: int = 0) -> tuple[str, ...]:
    items = sequence(value, field, minimum=minimum)
    result = tuple(relative_path(item, f"{field}[{index}]") for index, item in enumerate(items))
    if len(set(result)) != len(result):
        raise ContractError(ErrorCode.INVALID_VALUE, f"{field} must not contain duplicates.", {"field": field})
    return result

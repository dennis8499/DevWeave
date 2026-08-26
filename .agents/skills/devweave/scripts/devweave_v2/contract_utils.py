"""Strict validators shared by public schema implementations."""

from __future__ import annotations

import re
import stat
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, TypeVar

from .errors import ContractError, ErrorCode
from .version import SCHEMA_VERSION

MAX_TEXT = 8_192
MAX_ITEMS = 256
MAX_PATH = 512
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
TEnum = TypeVar("TEnum", bound=Enum)

# Implementation-task authority must never overlap repository control, runtime
# authority, Codex composition, or canonical ExecPlan storage. Ancestors are
# protected too because a directory/** sandbox root cannot subtract a child.
PROTECTED_TASK_AUTHORITY_PATHS = (
    ".git",
    ".devweave",
    ".codex",
    ".agents/skills/devweave",
    "docs/exec-plans",
)


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


def task_declared_paths(value: Any, field: str, *, minimum: int = 0) -> tuple[str, ...]:
    result = relative_paths(value, field, minimum=minimum)
    for index, declaration in enumerate(result):
        if _intersects_task_authority(declaration):
            raise ContractError(
                ErrorCode.FORBIDDEN,
                f"{field}[{index}] intersects a host-authority path.",
                {"field": f"{field}[{index}]", "path": declaration},
            )
    return result


def validate_task_declared_paths_for_repository(
    declarations: Iterable[str],
    repository: Path,
    *,
    field: str,
) -> None:
    """Reject declarations whose physical fixed prefix reaches host authority."""
    lexical_repository = Path(repository)
    if not lexical_repository.is_absolute():
        lexical_repository = lexical_repository.absolute()
    try:
        repository_stat = lexical_repository.lstat()
        physical_repository = lexical_repository.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ContractError(
            ErrorCode.PATH_OUTSIDE_REPOSITORY,
            "Task declarations require an accessible physical repository root.",
            {"field": field},
        ) from exc
    if not stat.S_ISDIR(repository_stat.st_mode) or _is_reparse_point(repository_stat):
        raise ContractError(
            ErrorCode.FORBIDDEN,
            "Task declarations cannot use a reparse-point repository root.",
            {"field": field},
        )

    for index, declaration in enumerate(declarations):
        static_parts = _task_declaration_static_parts(declaration)
        if not static_parts:
            raise ContractError(
                ErrorCode.FORBIDDEN,
                f"{field}[{index}] has no safe fixed repository prefix.",
                {"field": f"{field}[{index}]", "path": declaration},
            )
        physical_cursor = physical_repository
        lexical_cursor = lexical_repository
        unresolved: tuple[str, ...] = ()
        for offset, part in enumerate(static_parts):
            candidate = lexical_cursor / part
            try:
                candidate_stat = candidate.lstat()
            except FileNotFoundError:
                unresolved = static_parts[offset:]
                break
            except OSError as exc:
                raise ContractError(
                    ErrorCode.FORBIDDEN,
                    f"{field}[{index}] cannot be resolved safely.",
                    {"field": f"{field}[{index}]", "path": declaration},
                ) from exc
            if _is_reparse_point(candidate_stat):
                raise ContractError(
                    ErrorCode.FORBIDDEN,
                    f"{field}[{index}] traverses a symlink or junction.",
                    {"field": f"{field}[{index}]", "path": declaration},
                )
            try:
                physical_cursor = candidate.resolve(strict=True)
                physical_cursor.relative_to(physical_repository)
            except (OSError, RuntimeError, ValueError) as exc:
                raise ContractError(
                    ErrorCode.PATH_OUTSIDE_REPOSITORY,
                    f"{field}[{index}] resolves outside the repository.",
                    {"field": f"{field}[{index}]", "path": declaration},
                ) from exc
            lexical_cursor = candidate

        physical_candidate = physical_cursor.joinpath(*unresolved)
        try:
            physical_relative = physical_candidate.relative_to(physical_repository).as_posix()
        except ValueError as exc:
            raise ContractError(
                ErrorCode.PATH_OUTSIDE_REPOSITORY,
                f"{field}[{index}] resolves outside the repository.",
                {"field": f"{field}[{index}]", "path": declaration},
            ) from exc
        if not physical_relative or _intersects_task_authority(physical_relative):
            raise ContractError(
                ErrorCode.FORBIDDEN,
                f"{field}[{index}] physically intersects a host-authority path.",
                {
                    "field": f"{field}[{index}]",
                    "path": declaration,
                    "physical_path": physical_relative,
                },
            )


def _intersects_task_authority(declaration: str) -> bool:
    static_parts = [part.casefold() for part in _task_declaration_static_parts(declaration)]
    # A pattern without a fixed directory prefix can match every protected root.
    if not static_parts:
        return True
    static = "/".join(static_parts)
    for protected in PROTECTED_TASK_AUTHORITY_PATHS:
        folded = protected.casefold()
        if static == folded or static.startswith(f"{folded}/") or folded.startswith(f"{static}/"):
            return True
    return False


def _task_declaration_static_parts(declaration: str) -> tuple[str, ...]:
    result: list[str] = []
    for part in declaration.split("/"):
        if any(character in part for character in "*?["):
            break
        result.append(part)
    return tuple(result)


def _is_reparse_point(value: object) -> bool:
    mode = int(getattr(value, "st_mode", 0))
    attributes = int(getattr(value, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    return stat.S_ISLNK(mode) or bool(attributes & reparse_flag)

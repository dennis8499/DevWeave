"""Verification and review public contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .contract_utils import (
    boolean,
    enum_value,
    identifier,
    integer,
    relative_path,
    relative_paths,
    sequence,
    strict_object,
    strings,
    text,
)
from .version import SCHEMA_VERSION


class RiskLevel(StrEnum):
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"


class FindingSeverity(StrEnum):
    ADVISORY = "advisory"
    WARNING = "warning"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"


@dataclass(frozen=True, slots=True)
class VerificationCommand:
    command_id: str
    argv: tuple[str, ...]
    cwd: str
    affected_paths: tuple[str, ...]
    writes: str
    outputs: tuple[str, ...]
    dependencies: tuple[str, ...]
    timeout_seconds: int
    risk_profiles: tuple[RiskLevel, ...]
    expected_exit_codes: tuple[int, ...]
    release_only: bool
    definition_digest: str

    @classmethod
    def from_dict(cls, raw: Any) -> "VerificationCommand":
        data = strict_object(
            raw,
            name="VerificationCommand",
            required=(
                "command_id", "argv", "cwd", "affected_paths", "writes", "outputs",
                "dependencies", "timeout_seconds", "risk_profiles", "expected_exit_codes",
                "release_only", "definition_digest",
            ),
        )
        argv = strings(data["argv"], "VerificationCommand.argv", minimum=1, maximum=64)
        profiles = tuple(
            enum_value(item, f"VerificationCommand.risk_profiles[{index}]", RiskLevel)
            for index, item in enumerate(sequence(data["risk_profiles"], "VerificationCommand.risk_profiles", minimum=1, maximum=3))
        )
        exit_codes = tuple(
            integer(item, f"VerificationCommand.expected_exit_codes[{index}]", minimum=0, maximum=255)
            for index, item in enumerate(sequence(data["expected_exit_codes"], "VerificationCommand.expected_exit_codes", minimum=1, maximum=16))
        )
        return cls(
            command_id=identifier(data["command_id"], "VerificationCommand.command_id"),
            argv=argv,
            cwd=relative_path(data["cwd"], "VerificationCommand.cwd") if data["cwd"] != "." else ".",
            affected_paths=relative_paths(data["affected_paths"], "VerificationCommand.affected_paths"),
            writes=_writes(data["writes"]),
            outputs=relative_paths(data["outputs"], "VerificationCommand.outputs"),
            dependencies=strings(data["dependencies"], "VerificationCommand.dependencies"),
            timeout_seconds=integer(data["timeout_seconds"], "VerificationCommand.timeout_seconds", minimum=1, maximum=3600),
            risk_profiles=profiles,
            expected_exit_codes=exit_codes,
            release_only=boolean(data["release_only"], "VerificationCommand.release_only"),
            definition_digest=text(data["definition_digest"], "VerificationCommand.definition_digest", minimum=64, maximum=64),
        )


def _writes(value: Any) -> str:
    result = text(value, "VerificationCommand.writes", maximum=32)
    if result not in {"none", "declared"}:
        from .errors import ContractError, ErrorCode
        raise ContractError(ErrorCode.INVALID_VALUE, "VerificationCommand.writes must be none or declared.")
    return result


@dataclass(frozen=True, slots=True)
class VerificationPlan:
    schema_version: int
    plan_id: str
    commands: tuple[VerificationCommand, ...]

    @classmethod
    def from_dict(cls, raw: Any) -> "VerificationPlan":
        data = strict_object(raw, name="VerificationPlan", required=("plan_id", "commands"), versioned=True)
        commands = tuple(
            VerificationCommand.from_dict(item)
            for item in sequence(data["commands"], "VerificationPlan.commands", maximum=128)
        )
        ids = [item.command_id for item in commands]
        if len(ids) != len(set(ids)):
            from .errors import ContractError, ErrorCode
            raise ContractError(ErrorCode.INVALID_VALUE, "VerificationPlan command ids must be unique.")
        return cls(SCHEMA_VERSION, identifier(data["plan_id"], "VerificationPlan.plan_id"), commands)


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    schema_version: int
    finding_id: str
    severity: FindingSeverity
    summary: str
    paths: tuple[str, ...]
    requirement_ids: tuple[str, ...]
    acceptance_ids: tuple[str, ...]
    task_ids: tuple[str, ...]
    status: FindingStatus
    round: int

    @classmethod
    def from_dict(cls, raw: Any) -> "ReviewFinding":
        data = strict_object(
            raw,
            name="ReviewFinding",
            required=("finding_id", "severity", "summary", "paths", "requirement_ids", "acceptance_ids", "task_ids", "status", "round"),
            versioned=True,
        )
        return cls(
            SCHEMA_VERSION,
            identifier(data["finding_id"], "ReviewFinding.finding_id"),
            enum_value(data["severity"], "ReviewFinding.severity", FindingSeverity),
            text(data["summary"], "ReviewFinding.summary"),
            relative_paths(data["paths"], "ReviewFinding.paths"),
            strings(data["requirement_ids"], "ReviewFinding.requirement_ids"),
            strings(data["acceptance_ids"], "ReviewFinding.acceptance_ids"),
            strings(data["task_ids"], "ReviewFinding.task_ids"),
            enum_value(data["status"], "ReviewFinding.status", FindingStatus),
            integer(data["round"], "ReviewFinding.round", minimum=1, maximum=3),
        )

"""Schema-v2 tracked project configuration without machine-specific provenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from .canonical import sha256
from .contract_utils import identifier, sequence, strict_object, strings
from .errors import ContractError, ErrorCode
from .verification_contracts import VerificationCommand, VerificationPlan
from .version import SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class ExecutableDefinition:
    executable_id: str
    candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    schema_version: int
    executables: tuple[ExecutableDefinition, ...]
    verification_plan: VerificationPlan

    @classmethod
    def from_dict(cls, raw: Any) -> "ProjectConfig":
        data = strict_object(raw, name="ProjectConfig", required=("executables", "verification_plan"), versioned=True)
        if not isinstance(data["executables"], dict):
            raise ContractError(ErrorCode.INVALID_TYPE, "ProjectConfig.executables must be an object.")
        definitions: list[ExecutableDefinition] = []
        for executable_id, value in sorted(data["executables"].items()):
            safe_id = identifier(executable_id, "ProjectConfig executable id")
            item = strict_object(value, name=f"ProjectConfig.executables.{safe_id}", required=("candidates",))
            candidates = strings(item["candidates"], f"ProjectConfig.executables.{safe_id}.candidates", minimum=1, maximum=16)
            for candidate in candidates:
                path = PurePath(candidate)
                if path.is_absolute() or len(path.parts) != 1 or "/" in candidate or "\\" in candidate:
                    raise ContractError(ErrorCode.FORBIDDEN, "Tracked executable candidates must be portable command names.")
            definitions.append(ExecutableDefinition(safe_id, candidates))
        plan = VerificationPlan.from_dict(data["verification_plan"])
        executable_ids = {item.executable_id for item in definitions}
        command_ids = {item.command_id for item in plan.commands}
        for command in plan.commands:
            if command.argv[0] not in executable_ids:
                raise ContractError(ErrorCode.INVALID_VALUE, "Verification command names an undefined executable id.")
            if command.command_id in command.dependencies:
                raise ContractError(ErrorCode.INVALID_VALUE, "Verification command cannot depend on itself.")
            missing = sorted(set(command.dependencies) - command_ids)
            if missing:
                raise ContractError(ErrorCode.INVALID_VALUE, "Verification dependencies are missing.", {"missing": missing})
            expected = command_definition_digest(command)
            if command.definition_digest != expected:
                raise ContractError(
                    ErrorCode.CONFLICT,
                    "Verification command definition digest is stale.",
                    {"command_id": command.command_id, "expected": expected},
                )
        _assert_acyclic(plan)
        return cls(SCHEMA_VERSION, tuple(definitions), plan)

    def candidates_for(self, executable_id: str) -> tuple[str, ...]:
        for item in self.executables:
            if item.executable_id == executable_id:
                return item.candidates
        raise ContractError(ErrorCode.NOT_FOUND, "Executable definition was not found.")


def command_definition_payload(command: VerificationCommand) -> dict[str, Any]:
    return {
        "command_id": command.command_id,
        "argv": list(command.argv),
        "cwd": command.cwd,
        "affected_paths": list(command.affected_paths),
        "writes": command.writes,
        "outputs": list(command.outputs),
        "dependencies": list(command.dependencies),
        "timeout_seconds": command.timeout_seconds,
        "risk_profiles": [item.value for item in command.risk_profiles],
        "expected_exit_codes": list(command.expected_exit_codes),
        "release_only": command.release_only,
    }


def command_definition_digest(command: VerificationCommand) -> str:
    return sha256(command_definition_payload(command))


def command_payload_with_digest(raw: dict[str, Any]) -> dict[str, Any]:
    candidate = dict(raw)
    candidate["definition_digest"] = "0" * 64
    parsed = VerificationCommand.from_dict(candidate)
    candidate["definition_digest"] = command_definition_digest(parsed)
    return candidate


def _assert_acyclic(plan: VerificationPlan) -> None:
    graph = {item.command_id: item.dependencies for item in plan.commands}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(command_id: str) -> None:
        if command_id in visiting:
            raise ContractError(ErrorCode.INVALID_VALUE, "Verification dependency graph contains a cycle.")
        if command_id in visited:
            return
        visiting.add(command_id)
        for dependency in graph[command_id]:
            visit(dependency)
        visiting.remove(command_id)
        visited.add(command_id)

    for command_id in sorted(graph):
        visit(command_id)

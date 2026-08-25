"""RunSnapshot public contract and compact projection types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .contract_utils import enum_value, identifier, integer, sequence, strict_object, strings, text
from .verification_contracts import RiskLevel
from .version import SCHEMA_VERSION


class RunStatus(StrEnum):
    PREFLIGHT = "preflight"
    DRAFT = "draft"
    AWAITING_GATE = "awaiting_gate"
    IMPLEMENTING = "implementing"
    VERIFYING = "verifying"
    REVIEWING = "reviewing"
    AWAITING_ACCEPTANCE = "awaiting_acceptance"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class GateSnapshot:
    gate_id: str
    status: str
    fingerprint: str
    approved_revision: int

    @classmethod
    def from_dict(cls, raw: Any) -> "GateSnapshot":
        data = strict_object(raw, name="GateSnapshot", required=("gate_id", "status", "fingerprint", "approved_revision"))
        return cls(
            identifier(data["gate_id"], "GateSnapshot.gate_id"),
            text(data["status"], "GateSnapshot.status", maximum=32),
            text(data["fingerprint"], "GateSnapshot.fingerprint", minimum=0, maximum=64),
            integer(data["approved_revision"], "GateSnapshot.approved_revision"),
        )


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    task_id: str
    status: TaskStatus

    @classmethod
    def from_dict(cls, raw: Any) -> "TaskSnapshot":
        data = strict_object(raw, name="TaskSnapshot", required=("task_id", "status"))
        return cls(
            identifier(data["task_id"], "TaskSnapshot.task_id"),
            enum_value(data["status"], "TaskSnapshot.status", TaskStatus),
        )


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    schema_version: int
    run_id: str
    revision: int
    status: RunStatus
    phase: str
    risk: RiskLevel
    base_branch: str
    base_ref: str
    run_branch: str
    required_gates: tuple[str, ...]
    gates: tuple[GateSnapshot, ...]
    tasks: tuple[TaskSnapshot, ...]
    pending_decision_id: str
    verification_status: str
    review_status: str
    thread_status: str
    turn_status: str
    blockers: tuple[str, ...]
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, raw: Any) -> "RunSnapshot":
        data = strict_object(
            raw,
            name="RunSnapshot",
            required=(
                "run_id", "revision", "status", "phase", "risk", "base_branch", "base_ref",
                "run_branch", "required_gates", "gates", "tasks", "pending_decision_id",
                "verification_status", "review_status", "thread_status", "turn_status", "blockers",
                "created_at", "updated_at",
            ),
            versioned=True,
        )
        return cls(
            SCHEMA_VERSION,
            identifier(data["run_id"], "RunSnapshot.run_id"),
            integer(data["revision"], "RunSnapshot.revision", minimum=1),
            enum_value(data["status"], "RunSnapshot.status", RunStatus),
            text(data["phase"], "RunSnapshot.phase", maximum=64),
            enum_value(data["risk"], "RunSnapshot.risk", RiskLevel),
            text(data["base_branch"], "RunSnapshot.base_branch", maximum=256),
            text(data["base_ref"], "RunSnapshot.base_ref", minimum=40, maximum=64),
            text(data["run_branch"], "RunSnapshot.run_branch", maximum=256),
            strings(data["required_gates"], "RunSnapshot.required_gates", maximum=8),
            tuple(GateSnapshot.from_dict(item) for item in sequence(data["gates"], "RunSnapshot.gates", maximum=8)),
            tuple(TaskSnapshot.from_dict(item) for item in sequence(data["tasks"], "RunSnapshot.tasks")),
            text(data["pending_decision_id"], "RunSnapshot.pending_decision_id", minimum=0, maximum=128),
            text(data["verification_status"], "RunSnapshot.verification_status", maximum=64),
            text(data["review_status"], "RunSnapshot.review_status", maximum=64),
            text(data["thread_status"], "RunSnapshot.thread_status", maximum=64),
            text(data["turn_status"], "RunSnapshot.turn_status", maximum=64),
            strings(data["blockers"], "RunSnapshot.blockers"),
            text(data["created_at"], "RunSnapshot.created_at", maximum=64),
            text(data["updated_at"], "RunSnapshot.updated_at", maximum=64),
        )

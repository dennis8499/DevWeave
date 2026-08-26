"""ExecPlan draft and pending-decision contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .contract_utils import (
    boolean,
    enum_value,
    identifier,
    integer,
    relative_paths,
    sequence,
    strict_object,
    strings,
    task_declared_paths,
    text,
    validate_task_declared_paths_for_repository,
)
from .verification_contracts import RiskLevel, VerificationPlan
from .version import SCHEMA_VERSION


class DecisionStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class TaskDefinition:
    task_id: str
    title: str
    requirement_ids: tuple[str, ...]
    acceptance_ids: tuple[str, ...]
    declared_paths: tuple[str, ...]
    dependencies: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: Any) -> "TaskDefinition":
        data = strict_object(
            raw,
            name="TaskDefinition",
            required=("task_id", "title", "requirement_ids", "acceptance_ids", "declared_paths", "dependencies"),
        )
        return cls(
            identifier(data["task_id"], "TaskDefinition.task_id"),
            text(data["title"], "TaskDefinition.title", maximum=512),
            strings(data["requirement_ids"], "TaskDefinition.requirement_ids", minimum=1),
            strings(data["acceptance_ids"], "TaskDefinition.acceptance_ids", minimum=1),
            task_declared_paths(data["declared_paths"], "TaskDefinition.declared_paths", minimum=1),
            strings(data["dependencies"], "TaskDefinition.dependencies"),
        )


@dataclass(frozen=True, slots=True)
class PlanDecision:
    decision_id: str
    summary: str

    @classmethod
    def from_dict(cls, raw: Any) -> "PlanDecision":
        data = strict_object(raw, name="PlanDecision", required=("decision_id", "summary"))
        return cls(identifier(data["decision_id"], "PlanDecision.decision_id"), text(data["summary"], "PlanDecision.summary"))


@dataclass(frozen=True, slots=True)
class RunPlanDraft:
    schema_version: int
    run_id: str
    revision: int
    goal: str
    scope: tuple[str, ...]
    non_goals: tuple[str, ...]
    requirements: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    decisions: tuple[PlanDecision, ...]
    tasks: tuple[TaskDefinition, ...]
    verification_plan: VerificationPlan
    risk: RiskLevel
    risk_rationale: str

    @classmethod
    def from_dict(cls, raw: Any) -> "RunPlanDraft":
        data = strict_object(
            raw,
            name="RunPlanDraft",
            required=("run_id", "revision", "goal", "scope", "non_goals", "requirements", "acceptance_criteria", "decisions", "tasks", "verification_plan", "risk", "risk_rationale"),
            versioned=True,
        )
        decisions = tuple(PlanDecision.from_dict(item) for item in sequence(data["decisions"], "RunPlanDraft.decisions"))
        tasks = tuple(TaskDefinition.from_dict(item) for item in sequence(data["tasks"], "RunPlanDraft.tasks", minimum=1))
        task_ids = [item.task_id for item in tasks]
        if len(task_ids) != len(set(task_ids)):
            from .errors import ContractError, ErrorCode
            raise ContractError(ErrorCode.INVALID_VALUE, "RunPlanDraft task ids must be unique.")
        return cls(
            SCHEMA_VERSION,
            identifier(data["run_id"], "RunPlanDraft.run_id"),
            integer(data["revision"], "RunPlanDraft.revision", minimum=1),
            text(data["goal"], "RunPlanDraft.goal"),
            relative_paths(data["scope"], "RunPlanDraft.scope", minimum=1),
            strings(data["non_goals"], "RunPlanDraft.non_goals"),
            strings(data["requirements"], "RunPlanDraft.requirements", minimum=1),
            strings(data["acceptance_criteria"], "RunPlanDraft.acceptance_criteria", minimum=1),
            decisions,
            tasks,
            VerificationPlan.from_dict(data["verification_plan"]),
            enum_value(data["risk"], "RunPlanDraft.risk", RiskLevel),
            text(data["risk_rationale"], "RunPlanDraft.risk_rationale"),
        )


def validate_run_plan_repository_paths(draft: RunPlanDraft, repository: Path) -> None:
    for index, task in enumerate(draft.tasks):
        validate_task_declared_paths_for_repository(
            task.declared_paths,
            repository,
            field=f"RunPlanDraft.tasks[{index}].declared_paths",
        )


@dataclass(frozen=True, slots=True)
class DecisionOption:
    option_id: str
    label: str
    description: str

    @classmethod
    def from_dict(cls, raw: Any) -> "DecisionOption":
        data = strict_object(raw, name="DecisionOption", required=("option_id", "label", "description"))
        return cls(
            identifier(data["option_id"], "DecisionOption.option_id"),
            text(data["label"], "DecisionOption.label", maximum=128),
            text(data["description"], "DecisionOption.description", maximum=1024),
        )


@dataclass(frozen=True, slots=True)
class PendingDecision:
    schema_version: int
    decision_id: str
    run_id: str
    question: str
    options: tuple[DecisionOption, ...]
    recommended_option_id: str
    allow_other: bool
    blocking_task_id: str
    created_revision: int
    status: DecisionStatus
    answer: str

    @classmethod
    def from_dict(cls, raw: Any) -> "PendingDecision":
        data = strict_object(
            raw,
            name="PendingDecision",
            required=("decision_id", "run_id", "question", "options", "recommended_option_id", "allow_other", "blocking_task_id", "created_revision", "status", "answer"),
            versioned=True,
        )
        options = tuple(DecisionOption.from_dict(item) for item in sequence(data["options"], "PendingDecision.options", minimum=2, maximum=3))
        option_ids = {item.option_id for item in options}
        recommended = identifier(data["recommended_option_id"], "PendingDecision.recommended_option_id")
        if recommended not in option_ids:
            from .errors import ContractError, ErrorCode
            raise ContractError(ErrorCode.INVALID_VALUE, "Recommended option must identify one supplied option.")
        status = enum_value(data["status"], "PendingDecision.status", DecisionStatus)
        answer = text(data["answer"], "PendingDecision.answer", minimum=0)
        if status is DecisionStatus.PENDING and answer:
            from .errors import ContractError, ErrorCode
            raise ContractError(ErrorCode.INVALID_VALUE, "A pending decision cannot have an answer.")
        return cls(
            SCHEMA_VERSION,
            identifier(data["decision_id"], "PendingDecision.decision_id"),
            identifier(data["run_id"], "PendingDecision.run_id"),
            text(data["question"], "PendingDecision.question", maximum=2048),
            options,
            recommended,
            boolean(data["allow_other"], "PendingDecision.allow_other"),
            identifier(data["blocking_task_id"], "PendingDecision.blocking_task_id"),
            integer(data["created_revision"], "PendingDecision.created_revision", minimum=1),
            status,
            answer,
        )

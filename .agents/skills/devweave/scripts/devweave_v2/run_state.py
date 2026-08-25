"""Canonical ExecPlan shape, fingerprints, and lifecycle invariants."""

from __future__ import annotations

from typing import Any

from .canonical import primitive, sha256
from .contract_utils import identifier, integer, strict_object, text
from .errors import ContractError, ErrorCode
from .plan_contracts import RunPlanDraft
from .risk import policy_for
from .verification_contracts import RiskLevel
from .version import SCHEMA_VERSION

EXEC_PLAN_FIELDS = {
    "schema_version", "run_id", "revision", "status", "phase", "risk", "risk_rationale",
    "base_branch", "base_ref", "run_branch", "plan", "definition_fingerprint", "required_gates",
    "gates", "tasks", "pending_decision", "decision_history", "verification", "review",
    "completion_requested", "blockers", "applied_mutations", "created_at", "updated_at",
}


def plan_definition_payload(plan: dict[str, Any]) -> dict[str, Any]:
    draft = dict(plan["plan"])
    draft.pop("revision", None)
    return {
        "risk": plan["risk"],
        "risk_rationale": plan["risk_rationale"],
        "plan": draft,
    }


def definition_fingerprint(plan: dict[str, Any]) -> str:
    return sha256(plan_definition_payload(plan))


def new_exec_plan(
    draft: RunPlanDraft,
    *,
    base_branch: str,
    base_ref: str,
    run_branch: str,
    now: str,
) -> dict[str, Any]:
    policy = policy_for(draft.risk)
    draft_value = primitive(draft)
    tasks = {
        task.task_id: {
            "definition": primitive(task),
            "status": "pending",
            "progress": "",
        }
        for task in draft.tasks
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": draft.run_id,
        "revision": 1,
        "status": "awaiting_gate",
        "phase": "planning",
        "risk": draft.risk.value,
        "risk_rationale": draft.risk_rationale,
        "base_branch": base_branch,
        "base_ref": base_ref,
        "run_branch": run_branch,
        "plan": draft_value,
        "definition_fingerprint": "",
        "required_gates": list(policy.required_gates),
        "gates": {
            gate: {"status": "pending", "fingerprint": "", "approved_revision": 0, "decided_at": ""}
            for gate in policy.required_gates
        },
        "tasks": tasks,
        "pending_decision": None,
        "decision_history": [],
        "verification": {"status": "pending", "evidence_ids": []},
        "review": {"mode": policy.review_mode, "max_rounds": policy.max_review_rounds, "round": 0, "status": "pending", "finding_ids": []},
        "completion_requested": False,
        "blockers": [],
        "applied_mutations": ["run-start"],
        "created_at": now,
        "updated_at": now,
    }
    result["definition_fingerprint"] = definition_fingerprint(result)
    return validate_exec_plan(result)


def validate_exec_plan(raw: Any) -> dict[str, Any]:
    data = strict_object(raw, name="ExecPlan", required=EXEC_PLAN_FIELDS - {"schema_version"}, versioned=True)
    run_id = identifier(data["run_id"], "ExecPlan.run_id")
    integer(data["revision"], "ExecPlan.revision", minimum=1)
    if data["status"] not in {
        "awaiting_gate", "implementing", "verifying", "reviewing", "awaiting_acceptance",
        "blocked", "cancelled", "completed",
    }:
        raise ContractError(ErrorCode.INVALID_VALUE, "ExecPlan.status is invalid.")
    if data["phase"] not in {"planning", "implementation", "verification", "review", "acceptance", "closed"}:
        raise ContractError(ErrorCode.INVALID_VALUE, "ExecPlan.phase is invalid.")
    try:
        risk = RiskLevel(data["risk"])
    except ValueError as exc:
        raise ContractError(ErrorCode.INVALID_VALUE, "ExecPlan.risk is invalid.") from exc
    text(data["base_branch"], "ExecPlan.base_branch", maximum=256)
    text(data["base_ref"], "ExecPlan.base_ref", minimum=40, maximum=64)
    text(data["run_branch"], "ExecPlan.run_branch", maximum=256)
    draft = RunPlanDraft.from_dict(data["plan"])
    if draft.run_id != run_id:
        raise ContractError(ErrorCode.INVALID_VALUE, "ExecPlan and plan draft run ids differ.")
    required = list(policy_for(risk).required_gates)
    if data["required_gates"] != required or set(data["gates"]) != set(required):
        raise ContractError(ErrorCode.INVALID_VALUE, "ExecPlan gate set does not match risk policy.")
    if set(data["tasks"]) != {task.task_id for task in draft.tasks}:
        raise ContractError(ErrorCode.INVALID_VALUE, "ExecPlan task state differs from immutable definitions.")
    for task_id, task in data["tasks"].items():
        identifier(task_id, "ExecPlan.tasks key")
        strict_object(task, name=f"ExecPlan.tasks.{task_id}", required=("definition", "status", "progress"))
        if task["status"] not in {"pending", "in_progress", "blocked", "completed"}:
            raise ContractError(ErrorCode.INVALID_VALUE, "ExecPlan task status is invalid.")
    if not isinstance(data["applied_mutations"], list) or len(data["applied_mutations"]) > 512:
        raise ContractError(ErrorCode.BOUND_EXCEEDED, "ExecPlan applied mutation ledger is invalid.")
    if not isinstance(data["blockers"], list) or len(data["blockers"]) > 256:
        raise ContractError(ErrorCode.BOUND_EXCEEDED, "ExecPlan blockers are invalid.")
    expected = definition_fingerprint(data)
    if data["definition_fingerprint"] != expected:
        raise ContractError(ErrorCode.CONFLICT, "ExecPlan definition fingerprint is stale.")
    return dict(data)


def planning_gates_current(plan: dict[str, Any]) -> bool:
    policy = policy_for(RiskLevel(plan["risk"]))
    fingerprint = plan["definition_fingerprint"]
    return all(
        plan["gates"][gate]["status"] == "approved"
        and plan["gates"][gate]["fingerprint"] == fingerprint
        for gate in policy.planning_gates
    )


def invalidate_gates(plan: dict[str, Any]) -> None:
    plan["definition_fingerprint"] = definition_fingerprint(plan)
    for gate in plan["gates"].values():
        gate.update({"status": "pending", "fingerprint": "", "approved_revision": 0, "decided_at": ""})
    plan["status"] = "awaiting_gate"
    plan["phase"] = "planning"
    plan["completion_requested"] = False
    plan["verification"] = {"status": "pending", "evidence_ids": []}
    plan["review"]["round"] = 0
    plan["review"]["status"] = "pending"
    plan["review"]["finding_ids"] = []

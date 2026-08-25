"""Deterministic, idempotent projection of ephemeral run events."""

from __future__ import annotations

from typing import Any, Iterable

from .contract_utils import identifier, strict_object, text
from .errors import DevWeaveError, ErrorCode
from .snapshot_contracts import RunSnapshot


def reduce_snapshot(plan: dict[str, Any], events: Iterable[dict[str, Any]]) -> RunSnapshot:
    projection = {
        "thread_status": "disconnected",
        "turn_status": "idle",
        "verification_status": plan["verification"]["status"],
        "review_status": plan["review"]["status"],
        "blockers": list(plan["blockers"]),
    }
    seen: set[str] = set()
    for raw in events:
        event = strict_object(raw, name="RunEvent", required=("event_id", "type", "value"))
        event_id = identifier(event["event_id"], "RunEvent.event_id")
        if event_id in seen:
            continue
        seen.add(event_id)
        kind = text(event["type"], "RunEvent.type", maximum=64)
        value = text(event["value"], "RunEvent.value", minimum=0, maximum=2048)
        if kind in {"thread_status", "turn_status", "verification_status", "review_status"}:
            projection[kind] = value
        elif kind == "blocker" and value not in projection["blockers"]:
            projection["blockers"].append(value)
        else:
            # Unknown events are diagnostic-only and never mutate authority.
            continue
    gates = [
        {
            "gate_id": gate_id,
            "status": value["status"],
            "fingerprint": value["fingerprint"],
            "approved_revision": value["approved_revision"],
        }
        for gate_id, value in sorted(plan["gates"].items())
    ]
    tasks = [
        {"task_id": task_id, "status": value["status"]}
        for task_id, value in sorted(plan["tasks"].items())
    ]
    pending = plan["pending_decision"]
    raw_snapshot = {
        "schema_version": 2,
        "run_id": plan["run_id"],
        "revision": plan["revision"],
        "status": plan["status"],
        "phase": plan["phase"],
        "risk": plan["risk"],
        "base_branch": plan["base_branch"],
        "base_ref": plan["base_ref"],
        "run_branch": plan["run_branch"],
        "required_gates": plan["required_gates"],
        "gates": gates,
        "tasks": tasks,
        "pending_decision_id": pending["decision_id"] if pending else "",
        "verification_status": projection["verification_status"],
        "review_status": projection["review_status"],
        "thread_status": projection["thread_status"],
        "turn_status": projection["turn_status"],
        "blockers": sorted(projection["blockers"]),
        "created_at": plan["created_at"],
        "updated_at": plan["updated_at"],
    }
    try:
        return RunSnapshot.from_dict(raw_snapshot)
    except Exception as exc:
        if isinstance(exc, DevWeaveError):
            raise
        raise DevWeaveError(ErrorCode.INTERNAL, "Run snapshot projection failed.") from exc

"""Single workflow authority with capability-separated facades."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .canonical import primitive
from .contract_utils import identifier, integer, text
from .errors import DevWeaveError, ErrorCode
from .plan_contracts import DecisionStatus, PendingDecision, RunPlanDraft
from .plan_store import PlanStore
from .risk import RISK_ORDER, escalate_risk, policy_for
from .run_state import definition_fingerprint, invalidate_gates, new_exec_plan, planning_gates_current
from .verification_contracts import RiskLevel

Clock = Callable[[], str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RunService:
    """Coordinates domain mutations; adapters only receive a narrow facade."""

    def __init__(self, repository: Path, *, store: PlanStore | None = None, clock: Clock = utc_now) -> None:
        self.repository = repository.resolve()
        self.store = store or PlanStore(self.repository)
        self.clock = clock

    def agent(self) -> "AgentFacade":
        return AgentFacade(self)

    def host(self) -> "HostFacade":
        return HostFacade(self)

    def inspect(self, run_id: str) -> dict[str, Any]:
        return self.store.load(run_id)

    def mutate(
        self,
        run_id: str,
        expected_revision: int,
        mutation_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        return self.store.mutate(
            run_id,
            expected_revision=integer(expected_revision, "expected_revision", minimum=1),
            mutation_id=mutation_id,
            now=self.clock(),
            mutation=callback,
        )


class AgentFacade:
    """The complete agent capability surface; it intentionally has no host verbs."""

    def __init__(self, service: RunService) -> None:
        self._service = service

    def run_inspect(self, run_id: str) -> dict[str, Any]:
        return self._service.inspect(run_id)

    def context_read(self, run_id: str, relative_path: str) -> dict[str, Any]:
        from .contract_utils import relative_path as validate_path
        plan = self._service.inspect(run_id)
        normalized = validate_path(relative_path, "relative_path")
        allowed = normalized == "AGENTS.md" or normalized == "ARCHITECTURE.md" or normalized.startswith("docs/")
        if not allowed or normalized.startswith("docs/exec-plans/"):
            raise DevWeaveError(ErrorCode.FORBIDDEN, "Context path is not agent-readable.", {"path": normalized})
        candidate = (self._service.repository / normalized).resolve()
        try:
            candidate.relative_to(self._service.repository)
        except ValueError as exc:
            raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "Context path escapes the repository.") from exc
        if not candidate.is_file():
            raise DevWeaveError(ErrorCode.NOT_FOUND, "Context file was not found.", {"path": normalized})
        content = candidate.read_text(encoding="utf-8")
        if len(content.encode("utf-8")) > 256_000:
            raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Context file exceeds the read limit.")
        return {"run_id": plan["run_id"], "revision": plan["revision"], "path": normalized, "content": content}

    def plan_save(
        self,
        run_id: str,
        *,
        expected_revision: int,
        mutation_id: str,
        draft: dict[str, Any],
        risk_signals: list[str] | None = None,
    ) -> dict[str, Any]:
        parsed = RunPlanDraft.from_dict(draft)
        if parsed.run_id != run_id or parsed.revision != expected_revision:
            raise DevWeaveError(ErrorCode.STALE_REVISION, "Plan draft identity or revision is stale.")

        def mutation(plan: dict[str, Any]) -> None:
            if plan["phase"] != "planning":
                raise DevWeaveError(ErrorCode.GATE_REQUIRED, "Plan definitions are immutable after planning gates.")
            requested = parsed.risk
            escalated = escalate_risk(requested, set(risk_signals or []))
            current = RiskLevel(plan["risk"])
            if RISK_ORDER[escalated] < RISK_ORDER[current]:
                raise DevWeaveError(ErrorCode.FORBIDDEN, "Agents cannot downgrade risk.")
            effective = current if RISK_ORDER[current] > RISK_ORDER[escalated] else escalated
            updated = replace(parsed, revision=expected_revision + 1, risk=effective)
            plan["plan"] = primitive(updated)
            plan["risk"] = effective.value
            plan["risk_rationale"] = updated.risk_rationale
            policy = policy_for(effective)
            plan["required_gates"] = list(policy.required_gates)
            old_gates = plan["gates"]
            plan["gates"] = {
                gate: old_gates.get(gate, {"status": "pending", "fingerprint": "", "approved_revision": 0, "decided_at": ""})
                for gate in policy.required_gates
            }
            plan["tasks"] = {
                task.task_id: {
                    "definition": primitive(task),
                    "status": plan["tasks"].get(task.task_id, {}).get("status", "pending"),
                    "progress": plan["tasks"].get(task.task_id, {}).get("progress", ""),
                }
                for task in updated.tasks
            }
            plan["review"] = {
                "mode": policy.review_mode,
                "max_rounds": policy.max_review_rounds,
                "round": 0,
                "status": "pending",
                "finding_ids": [],
            }
            plan["definition_fingerprint"] = definition_fingerprint(plan)
            invalidate_gates(plan)

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)

    def decision_request(
        self,
        run_id: str,
        *,
        expected_revision: int,
        mutation_id: str,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        parsed = PendingDecision.from_dict(decision)
        if parsed.run_id != run_id or parsed.created_revision != expected_revision or parsed.status is not DecisionStatus.PENDING:
            raise DevWeaveError(ErrorCode.STALE_REVISION, "Pending decision identity or revision is stale.")

        def mutation(plan: dict[str, Any]) -> None:
            if plan["pending_decision"] is not None:
                raise DevWeaveError(ErrorCode.CONFLICT, "A run may have only one pending decision.")
            task = plan["tasks"].get(parsed.blocking_task_id)
            if task is None:
                raise DevWeaveError(ErrorCode.NOT_FOUND, "Blocking task was not found.")
            value = primitive(parsed)
            value["previous_task_status"] = task["status"]
            value["previous_run_status"] = plan["status"]
            plan["pending_decision"] = value
            task["status"] = "blocked"
            plan["status"] = "blocked"

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)

    def task_update(
        self,
        run_id: str,
        *,
        expected_revision: int,
        mutation_id: str,
        task_id: str,
        status: str,
        progress: str = "",
    ) -> dict[str, Any]:
        safe_task = identifier(task_id, "task_id")
        if status not in {"in_progress", "completed"}:
            raise DevWeaveError(ErrorCode.INVALID_VALUE, "Agent task status is not allowed.")
        bounded_progress = text(progress, "progress", minimum=0, maximum=2048)

        def mutation(plan: dict[str, Any]) -> None:
            if not planning_gates_current(plan) or plan["phase"] != "implementation":
                raise DevWeaveError(ErrorCode.GATE_REQUIRED, "Planning gates are not current.")
            task = plan["tasks"].get(safe_task)
            if task is None:
                raise DevWeaveError(ErrorCode.NOT_FOUND, "Task was not found.")
            definitions = {item["task_id"]: item for item in (value["definition"] for value in plan["tasks"].values())}
            for dependency in definitions[safe_task]["dependencies"]:
                if plan["tasks"][dependency]["status"] != "completed":
                    raise DevWeaveError(ErrorCode.GATE_REQUIRED, "Task dependency is incomplete.", {"dependency": dependency})
            current = task["status"]
            if current == "completed" and status != "completed":
                raise DevWeaveError(ErrorCode.CONFLICT, "Completed task state is immutable.")
            task["status"] = status
            task["progress"] = bounded_progress

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)

    def verification_run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        raise DevWeaveError(ErrorCode.NOT_IMPLEMENTED, "Verification engine is installed by TASK-004.")

    def verification_read(self, run_id: str) -> dict[str, Any]:
        plan = self._service.inspect(run_id)
        return {"run_id": run_id, "revision": plan["revision"], "verification": plan["verification"], "review": plan["review"]}

    def completion_request(self, run_id: str, *, expected_revision: int, mutation_id: str) -> dict[str, Any]:
        def mutation(plan: dict[str, Any]) -> None:
            if plan["pending_decision"] is not None:
                raise DevWeaveError(ErrorCode.BLOCKED, "A pending decision blocks completion.")
            incomplete = sorted(task_id for task_id, value in plan["tasks"].items() if value["status"] != "completed")
            if incomplete:
                raise DevWeaveError(ErrorCode.BLOCKED, "Tasks remain incomplete.", {"tasks": incomplete})
            plan["completion_requested"] = True
            plan["phase"] = "verification"
            plan["status"] = "verifying"

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)


class HostFacade:
    """Host-only lifecycle surface.  No generic method dispatcher is provided."""

    def __init__(self, service: RunService) -> None:
        self._service = service

    def run_start(
        self,
        draft: dict[str, Any],
        *,
        base_branch: str,
        base_ref: str,
        run_branch: str,
    ) -> dict[str, Any]:
        parsed = RunPlanDraft.from_dict(draft)
        plan = new_exec_plan(parsed, base_branch=base_branch, base_ref=base_ref, run_branch=run_branch, now=self._service.clock())
        return self._service.store.create(plan)

    def run_resume(self, run_id: str) -> dict[str, Any]:
        return self._service.inspect(run_id)

    def decision_resolve(
        self,
        run_id: str,
        *,
        expected_revision: int,
        mutation_id: str,
        decision_id: str,
        option_id: str = "",
        other: str = "",
    ) -> dict[str, Any]:
        safe_decision = identifier(decision_id, "decision_id")
        if bool(option_id) == bool(other):
            raise DevWeaveError(ErrorCode.INVALID_ARGUMENT, "Resolve with exactly one option or custom answer.")

        def mutation(plan: dict[str, Any]) -> None:
            pending = plan["pending_decision"]
            if pending is None or pending["decision_id"] != safe_decision:
                raise DevWeaveError(ErrorCode.NOT_FOUND, "Pending decision was not found.")
            option_ids = {item["option_id"] for item in pending["options"]}
            if option_id:
                selected = identifier(option_id, "option_id")
                if selected not in option_ids:
                    raise DevWeaveError(ErrorCode.INVALID_VALUE, "Decision option is not valid.")
                answer = selected
            else:
                if not pending["allow_other"]:
                    raise DevWeaveError(ErrorCode.FORBIDDEN, "Custom answers are not allowed for this decision.")
                answer = text(other, "other", maximum=2048)
            record = {key: value for key, value in pending.items() if key not in {"previous_task_status", "previous_run_status"}}
            record["status"] = "resolved"
            record["answer"] = answer
            plan["decision_history"].append(record)
            task = plan["tasks"][pending["blocking_task_id"]]
            task["status"] = pending["previous_task_status"]
            plan["status"] = pending["previous_run_status"]
            plan["pending_decision"] = None

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)

    def gate_decide(
        self,
        run_id: str,
        *,
        expected_revision: int,
        mutation_id: str,
        gate_id: str,
        approve: bool,
    ) -> dict[str, Any]:
        safe_gate = identifier(gate_id, "gate_id")

        def mutation(plan: dict[str, Any]) -> None:
            gate = plan["gates"].get(safe_gate)
            if gate is None:
                raise DevWeaveError(ErrorCode.INVALID_VALUE, "Gate is not required by current risk policy.")
            gate["status"] = "approved" if approve else "rejected"
            gate["fingerprint"] = plan["definition_fingerprint"]
            gate["approved_revision"] = expected_revision + 1 if approve else 0
            gate["decided_at"] = self._service.clock()
            if not approve:
                plan["status"] = "blocked"
                plan["blockers"].append(f"gate_rejected:{safe_gate}")
            elif safe_gate == "acceptance":
                if not plan["completion_requested"]:
                    raise DevWeaveError(ErrorCode.GATE_REQUIRED, "Acceptance cannot precede completion request.")
                plan["status"] = "completed"
                plan["phase"] = "closed"
            elif planning_gates_current(plan):
                plan["status"] = "implementing"
                plan["phase"] = "implementation"

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)

    def run_cancel(self, run_id: str, *, expected_revision: int, mutation_id: str) -> dict[str, Any]:
        def mutation(plan: dict[str, Any]) -> None:
            if plan["status"] == "completed":
                raise DevWeaveError(ErrorCode.CONFLICT, "Completed runs cannot be cancelled.")
            plan["status"] = "cancelled"
            plan["phase"] = "closed"

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)

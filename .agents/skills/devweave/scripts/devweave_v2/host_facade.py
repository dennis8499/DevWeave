"""Host-only workflow lifecycle facade and strict review admission."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .contract_utils import integer, sequence, strict_object, text
from .errors import DevWeaveError, ErrorCode
from .plan_contracts import RunPlanDraft, validate_run_plan_repository_paths
from .run_state import new_exec_plan, planning_gates_current
from .verification_contracts import FindingSeverity, FindingStatus, ReviewFinding, RiskLevel

if TYPE_CHECKING:
    from .run_service import RunService


class HostFacade:
    """Host-only lifecycle surface. No generic method dispatcher is provided."""

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
        validate_run_plan_repository_paths(parsed, self._service.repository)
        plan = new_exec_plan(
            parsed,
            base_branch=base_branch,
            base_ref=base_ref,
            run_branch=run_branch,
            now=self._service.clock(),
        )
        return self._service.store.create(plan)

    def run_resume(self, run_id: str) -> dict[str, Any]:
        plan = self._service.recover(run_id)
        self._service.assert_run_context(plan)
        return plan

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
        from .contract_utils import identifier

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
            record = {
                key: value
                for key, value in pending.items()
                if key not in {"previous_task_status", "previous_run_status"}
            }
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
        review_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from .contract_utils import identifier

        safe_gate = identifier(gate_id, "gate_id")
        checkpoint_ref = ""

        def mutation(plan: dict[str, Any]) -> None:
            if safe_gate == "acceptance":
                self._decide_acceptance(plan, expected_revision, approve, review_result)
                gate = plan["gates"].get("acceptance")
                if gate is not None and checkpoint_ref:
                    gate["commit_ref"] = checkpoint_ref
                if plan["status"] == "completed" and checkpoint_ref:
                    plan["archive_ref"] = checkpoint_ref
                return
            gate = plan["gates"].get(safe_gate)
            if gate is None:
                raise DevWeaveError(ErrorCode.INVALID_VALUE, "Gate is not required by current risk policy.")
            gate["status"] = "approved" if approve else "rejected"
            gate["fingerprint"] = plan["definition_fingerprint"]
            gate["approved_revision"] = expected_revision + 1 if approve else 0
            gate["decided_at"] = self._service.clock()
            if checkpoint_ref:
                gate["commit_ref"] = checkpoint_ref
            if not approve:
                plan["status"] = "blocked"
                plan["blockers"].append(f"gate_rejected:{safe_gate}")
            elif planning_gates_current(plan):
                plan["status"] = "implementing"
                plan["phase"] = "implementation"

        coordinator = self._service.git_coordinator
        with self._service.authority_transaction():
            current = self._service._recover_locked(run_id)
            if mutation_id in current["applied_mutations"]:
                updated = current
            else:
                if current["revision"] != expected_revision:
                    raise DevWeaveError(ErrorCode.STALE_REVISION, "Gate decision expected a stale run revision.")
                if coordinator is not None:
                    checkpoint_ref = coordinator.prepare_gate(
                        current,
                        gate_id=safe_gate,
                        mutation_id=mutation_id,
                        expected_revision=expected_revision,
                    )
                updated = self._service._mutate_locked(run_id, expected_revision, mutation_id, mutation)
            if safe_gate == "acceptance" and updated["status"] == "completed":
                self._service.store.complete(run_id)
            if coordinator is not None:
                committed_ref = coordinator.checkpoint_gate(
                    updated,
                    gate_id=safe_gate,
                    mutation_id=mutation_id,
                    expected_revision=expected_revision,
                )
                coordinator.finalize_gate(run_id, mutation_id, committed_ref)
            return updated

    def _decide_acceptance(
        self,
        plan: dict[str, Any],
        expected_revision: int,
        approve: bool,
        review_result: dict[str, Any] | None,
    ) -> None:
        if not approve:
            gate = plan["gates"].get("acceptance")
            if gate is not None:
                gate.update({
                    "status": "rejected",
                    "fingerprint": plan["definition_fingerprint"],
                    "approved_revision": 0,
                    "decided_at": self._service.clock(),
                })
            plan["status"] = "blocked"
            plan["blockers"].append("gate_rejected:acceptance")
            return
        if not plan["completion_requested"]:
            raise DevWeaveError(ErrorCode.GATE_REQUIRED, "Acceptance requires completion request and current verification.")
        self._service.require_current_verification(plan)
        current_id = plan["verification"]["current_report_id"]
        source_fingerprint = plan["verification"]["reports"][current_id]["source_digest"]
        if RiskLevel(plan["risk"]) is RiskLevel.LOW:
            plan["review"].update({
                "round": 1,
                "status": "passed",
                "finding_ids": [],
                "source_fingerprint": source_fingerprint,
                "reviewer_thread_id": "self-review",
                "review_turn_id": "self-review",
            })
        else:
            plan["review"].update(
                validate_review_result(review_result, plan["review"]["max_rounds"], source_fingerprint)
            )
        gate = plan["gates"].get("acceptance")
        if gate is not None:
            gate.update({
                "status": "approved",
                "fingerprint": plan["definition_fingerprint"],
                "approved_revision": expected_revision + 1,
                "decided_at": self._service.clock(),
            })
        plan["status"] = "completed"
        plan["phase"] = "closed"

    def run_cancel(self, run_id: str, *, expected_revision: int, mutation_id: str) -> dict[str, Any]:
        def mutation(plan: dict[str, Any]) -> None:
            if plan["status"] == "completed":
                raise DevWeaveError(ErrorCode.CONFLICT, "Completed runs cannot be cancelled.")
            plan["status"] = "cancelled"
            plan["phase"] = "closed"

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)


def validate_review_result(
    raw: dict[str, Any] | None,
    max_rounds: int,
    expected_source_fingerprint: str,
) -> dict[str, Any]:
    if raw is None:
        raise DevWeaveError(ErrorCode.GATE_REQUIRED, "Detached review evidence is required for acceptance.")
    data = strict_object(
        raw,
        name="review_result",
        required=(
            "result", "severity", "source_fingerprint", "implementation_thread_id",
            "reviewer_thread_id", "review_turn_id", "round", "findings",
        ),
        versioned=True,
    )
    implementation_thread = text(data["implementation_thread_id"], "review_result.implementation_thread_id", maximum=256)
    reviewer_thread = text(data["reviewer_thread_id"], "review_result.reviewer_thread_id", maximum=256)
    review_turn = text(data["review_turn_id"], "review_result.review_turn_id", maximum=256)
    round_number = integer(data["round"], "review_result.round", minimum=1, maximum=max_rounds)
    source_fingerprint = text(data["source_fingerprint"], "review_result.source_fingerprint", minimum=64, maximum=64)
    if any(character not in "0123456789abcdef" for character in source_fingerprint):
        raise DevWeaveError(ErrorCode.INVALID_VALUE, "Review source fingerprint must be lowercase SHA-256.")
    findings = [ReviewFinding.from_dict(item) for item in sequence(data["findings"], "review_result.findings", maximum=128)]
    finding_ids = [item.finding_id for item in findings]
    if any(item.round != round_number for item in findings) or len(finding_ids) != len(set(finding_ids)):
        raise DevWeaveError(ErrorCode.CONFLICT, "Review findings contradict the envelope.")
    severity_order = {FindingSeverity.ADVISORY: 0, FindingSeverity.WARNING: 1, FindingSeverity.CRITICAL: 2}
    calculated = max((item.severity for item in findings), key=lambda item: severity_order[item], default=FindingSeverity.ADVISORY)
    unresolved = any(item.severity is FindingSeverity.CRITICAL and item.status is FindingStatus.OPEN for item in findings)
    if data["severity"] != calculated.value:
        raise DevWeaveError(ErrorCode.CONFLICT, "Review severity contradicts its findings.")
    if data["result"] != "passed" or implementation_thread == reviewer_thread or source_fingerprint != expected_source_fingerprint or unresolved:
        raise DevWeaveError(ErrorCode.BLOCKED, "Acceptance review bindings do not establish a detached, current, critical-clear result.")
    return {
        "round": round_number,
        "status": "passed",
        "finding_ids": finding_ids,
        "source_fingerprint": source_fingerprint,
        "reviewer_thread_id": reviewer_thread,
        "review_turn_id": review_turn,
    }

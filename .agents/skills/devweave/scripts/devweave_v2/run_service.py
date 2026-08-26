"""Single workflow authority with capability-separated facades."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
import threading
from typing import Any, Callable

from .canonical import primitive
from .contract_utils import identifier, integer, text
from .errors import DevWeaveError, ErrorCode
from .interprocess_lock import InterProcessLock
from .plan_contracts import DecisionStatus, PendingDecision, RunPlanDraft
from .plan_store import PlanStore
from .risk import RISK_ORDER, escalate_risk, policy_for
from .run_state import definition_fingerprint, invalidate_gates, planning_gates_current
from .verification_contracts import RiskLevel
from .verification_engine import VerificationEngine
from .verification_store import VerificationReportStore

try:
    from .run_git_coordinator import RunGitCoordinator
except ImportError:  # pragma: no cover - only protects partial embedded installations
    RunGitCoordinator = Any  # type: ignore[misc,assignment]

Clock = Callable[[], str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RunService:
    """Coordinates domain mutations; adapters only receive a narrow facade."""

    def __init__(
        self,
        repository: Path,
        *,
        store: PlanStore | None = None,
        clock: Clock = utc_now,
        verification_engine: VerificationEngine | None = None,
        verification_store: VerificationReportStore | None = None,
        git_coordinator: RunGitCoordinator | None = None,
    ) -> None:
        self.repository = repository.resolve()
        self.store = store or PlanStore(self.repository)
        self.clock = clock
        self.verification_engine = verification_engine
        self.verification_store = verification_store or VerificationReportStore(self.repository)
        self.git_coordinator = git_coordinator
        self._lock = threading.RLock()
        self._authority_lock_path = self.repository / ".devweave" / "runtime" / "locks" / "authority.lock"

    def agent(self) -> "AgentFacade":
        return AgentFacade(self)

    def host(self) -> "HostFacade":
        from .host_facade import HostFacade

        return HostFacade(self)

    def inspect(self, run_id: str) -> dict[str, Any]:
        return self.store.load(run_id)

    def mutate(
        self,
        run_id: str,
        expected_revision: int,
        mutation_id: str,
        callback: Callable[[dict[str, Any]], None],
        allowed_dirty_paths: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        with self.authority_transaction():
            return self._mutate_locked(
                run_id,
                expected_revision,
                mutation_id,
                callback,
                allowed_dirty_paths=allowed_dirty_paths,
            )

    def _mutate_locked(
        self,
        run_id: str,
        expected_revision: int,
        mutation_id: str,
        callback: Callable[[dict[str, Any]], None],
        *,
        allowed_dirty_paths: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        current = self.store.load(run_id)
        if self.git_coordinator is not None:
            self.git_coordinator.assert_run(current, extra_paths=allowed_dirty_paths)
        return self.store.mutate(
            run_id,
            expected_revision=integer(expected_revision, "expected_revision", minimum=1),
            mutation_id=mutation_id,
            now=self.clock(),
            mutation=callback,
        )

    @contextmanager
    def authority_transaction(self):
        with self._lock, InterProcessLock(self._authority_lock_path):
            yield

    def assert_run_context(self, plan: dict[str, Any], *, require_clean: bool = False) -> None:
        if self.git_coordinator is not None:
            self.git_coordinator.assert_run(plan, require_clean=require_clean)

    def verification_is_current(self, plan: dict[str, Any]) -> bool:
        engine = self.verification_engine
        current_id = plan["verification"].get("current_report_id", "")
        report = plan["verification"].get("reports", {}).get(current_id)
        if engine is None or not current_id or plan["verification"].get("status") != "passed" or not isinstance(report, dict):
            return False
        try:
            return engine.report_is_current(
                report,
                profile=RiskLevel(plan["risk"]),
                plan_digest=plan["definition_fingerprint"],
            )
        except (DevWeaveError, AttributeError, KeyError, TypeError, ValueError):
            return False

    def require_current_verification(self, plan: dict[str, Any]) -> None:
        if not self.verification_is_current(plan):
            raise DevWeaveError(
                ErrorCode.BLOCKED,
                "Verification evidence is stale or its source, plan, command, or executable binding changed.",
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
                    "commit_ref": plan["tasks"].get(task.task_id, {}).get("commit_ref", ""),
                }
                for task in updated.tasks
            }
            plan["review"] = {
                "mode": policy.review_mode,
                "max_rounds": policy.max_review_rounds,
                "round": 0,
                "status": "pending",
                "finding_ids": [],
                "source_fingerprint": "",
                "reviewer_thread_id": "",
                "review_turn_id": "",
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
        commit_ref = ""

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
            if status == "completed" and commit_ref:
                task["commit_ref"] = commit_ref
            plan["verification"].update({"status": "pending", "evidence_ids": [], "current_report_id": ""})
            plan["completion_requested"] = False

        coordinator = self._service.git_coordinator
        if status != "completed" or coordinator is None:
            return self._service.mutate(run_id, expected_revision, mutation_id, mutation)
        with self._service.authority_transaction():
            current = self._service.store.load(run_id)
            if mutation_id in current["applied_mutations"]:
                return current
            if current["revision"] != expected_revision:
                raise DevWeaveError(ErrorCode.STALE_REVISION, "Task completion expected a stale run revision.")
            coordinator.assert_run(current)
            commit_ref = coordinator.complete_task(current, task_id=safe_task, mutation_id=mutation_id)
            updated = self._service._mutate_locked(run_id, expected_revision, mutation_id, mutation)
            coordinator.finalize_task(run_id, mutation_id, commit_ref)
            return updated

    def verification_run(
        self,
        run_id: str,
        *,
        expected_revision: int,
        mutation_id: str,
        paths: list[str] | None = None,
        release: bool = False,
    ) -> dict[str, Any]:
        engine = self._service.verification_engine
        if engine is None:
            raise DevWeaveError(ErrorCode.BLOCKED, "Verification engine is not configured.")
        plan = self._service.inspect(run_id)
        if mutation_id in plan["applied_mutations"]:
            existing = self._service.verification_store.load(run_id, mutation_id)
            if existing is None:
                raise DevWeaveError(ErrorCode.CONFLICT, "Verification mutation is recorded but its runtime report is unavailable.")
            return {"run": plan, "report": existing}
        if plan["revision"] != expected_revision:
            raise DevWeaveError(ErrorCode.STALE_REVISION, "Verification expected a stale run revision.")
        if plan["phase"] not in {"implementation", "verification", "review"} or not planning_gates_current(plan):
            raise DevWeaveError(ErrorCode.GATE_REQUIRED, "Current planning gates do not allow verification.")
        effective_paths = tuple(paths or ())
        coordinator = self._service.git_coordinator
        if coordinator is not None:
            discovered = coordinator.changed_paths(plan)
            if effective_paths and tuple(sorted(set(effective_paths))) != discovered:
                raise DevWeaveError(
                    ErrorCode.FORBIDDEN,
                    "Verification paths must equal the Git-derived run change set.",
                    {"expected": list(discovered)},
                )
            effective_paths = discovered
        report = self._service.verification_store.load(run_id, mutation_id)
        if report is None:
            report = engine.run(
                profile=RiskLevel(plan["risk"]),
                plan_digest=plan["definition_fingerprint"],
                changed_paths=effective_paths,
                release=release,
            )
            report = self._service.verification_store.save_once(run_id, mutation_id, report)

        def mutation(candidate: dict[str, Any]) -> None:
            evidence_ids = [item["evidence_id"] for item in report["evidence"]]
            summary = {
                "schema_version": report["schema_version"],
                "gate_eligible": bool(report["gate_eligible"]),
                "evidence_ids": evidence_ids,
                "plan_id": report["plan_id"],
                "plan_digest": report["plan_digest"],
                "profile": report["profile"],
                "release": report["release"],
                "changed_paths": report["changed_paths"],
                "source_digest": report["source_digest"],
                "selection": report["selection"],
                "bindings": report["bindings"],
            }
            current = engine.report_is_current(
                summary,
                profile=RiskLevel(candidate["risk"]),
                plan_digest=candidate["definition_fingerprint"],
            )
            candidate["verification"]["status"] = "passed" if current else "failed"
            candidate["verification"]["evidence_ids"] = evidence_ids
            candidate["verification"]["reports"][mutation_id] = summary
            candidate["verification"]["current_report_id"] = mutation_id if current else ""

        effects = tuple(
            path
            for evidence in report["evidence"]
            for path in evidence.get("changed_paths", [])
        )
        updated = self._service.mutate(
            run_id,
            expected_revision,
            mutation_id,
            mutation,
            allowed_dirty_paths=effects,
        )
        return {"run": updated, "report": report}

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
            self._service.require_current_verification(plan)
            plan["completion_requested"] = True
            if RiskLevel(plan["risk"]) is RiskLevel.LOW:
                plan["phase"] = "acceptance"
                plan["status"] = "awaiting_acceptance"
            else:
                plan["phase"] = "review"
                plan["status"] = "reviewing"

        return self._service.mutate(run_id, expected_revision, mutation_id, mutation)

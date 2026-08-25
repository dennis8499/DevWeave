from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.canonical import dumps
from devweave_v2.errors import DevWeaveError, ErrorCode
from devweave_v2.plan_store import PlanStore
from devweave_v2.reducer import reduce_snapshot
from devweave_v2.run_service import RunService


BASE_REF = "a" * 40


class RunServiceHarness:
    def __init__(self, *, fault_hook=None) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="devweave-v2-run-")
        self.repo = Path(self.temp.name)
        self.clock_tick = 0
        self.store = PlanStore(self.repo, fault_hook=fault_hook)
        self.service = RunService(self.repo, store=self.store, clock=self.clock)

    def clock(self) -> str:
        self.clock_tick += 1
        return f"2026-08-25T00:00:{self.clock_tick:02d}Z"

    def close(self) -> None:
        self.temp.cleanup()

    def draft(self, risk: str = "high", *, run_id: str = "run-fixture", revision: int = 1) -> dict:
        raw = json.loads((ROOT / "fixtures" / "devweave_v2" / "run-plan-draft.json").read_text(encoding="utf-8"))
        raw["risk"] = risk
        raw["run_id"] = run_id
        raw["revision"] = revision
        return raw

    def start(self, risk: str = "high") -> dict:
        return self.service.host().run_start(
            self.draft(risk),
            base_branch="main",
            base_ref=BASE_REF,
            run_branch="devweave/run-fixture-slice",
        )


class RunServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = RunServiceHarness()

    def tearDown(self) -> None:
        self.h.close()

    def test_risk_matrix_selects_required_gates_and_review(self) -> None:
        expected = {
            "low": (["plan"], "self", 1),
            "standard": (["plan", "acceptance"], "detached", 1),
            "high": (["scope", "design", "acceptance"], "detached_fix_reverify", 3),
        }
        for index, (risk, contract) in enumerate(expected.items()):
            draft = self.h.draft(risk, run_id=f"run-{risk}")
            plan = self.h.service.host().run_start(
                draft,
                base_branch="main",
                base_ref=BASE_REF,
                run_branch=f"devweave/run-{risk}",
            )
            self.assertEqual(plan["required_gates"], contract[0])
            self.assertEqual((plan["review"]["mode"], plan["review"]["max_rounds"]), contract[1:])

    def test_gate_fingerprint_and_plan_change_invalidate_approval(self) -> None:
        plan = self.h.start("standard")
        approved = self.h.service.host().gate_decide(
            plan["run_id"], expected_revision=1, mutation_id="approve-plan", gate_id="plan", approve=True
        )
        self.assertEqual(approved["status"], "implementing")
        draft = self.h.draft("standard", revision=approved["revision"])
        draft["goal"] = "A changed governed goal."
        with self.assertRaises(DevWeaveError) as late:
            self.h.service.agent().plan_save(
                plan["run_id"], expected_revision=approved["revision"], mutation_id="late-plan", draft=draft
            )
        self.assertEqual(late.exception.code, ErrorCode.GATE_REQUIRED)

    def test_risk_signal_escalates_before_gate_and_invalidates_old_gate(self) -> None:
        plan = self.h.start("low")
        draft = self.h.draft("low", revision=1)
        updated = self.h.service.agent().plan_save(
            plan["run_id"], expected_revision=1, mutation_id="risk-escalate", draft=draft, risk_signals=["public_schema"]
        )
        self.assertEqual(updated["risk"], "high")
        self.assertEqual(updated["required_gates"], ["scope", "design", "acceptance"])
        self.assertTrue(all(item["status"] == "pending" for item in updated["gates"].values()))

    def test_stale_revision_rejected_before_mutation_and_duplicate_is_idempotent(self) -> None:
        plan = self.h.start("low")
        first = self.h.service.host().gate_decide(
            plan["run_id"], expected_revision=1, mutation_id="approve-once", gate_id="plan", approve=True
        )
        duplicate = self.h.service.host().gate_decide(
            plan["run_id"], expected_revision=1, mutation_id="approve-once", gate_id="plan", approve=True
        )
        self.assertEqual(dumps(first), dumps(duplicate))
        with self.assertRaises(DevWeaveError) as stale:
            self.h.service.host().run_cancel(plan["run_id"], expected_revision=1, mutation_id="stale-cancel")
        self.assertEqual(stale.exception.code, ErrorCode.STALE_REVISION)

    def test_pending_decision_only_host_can_resolve_and_malformed_keeps_pending(self) -> None:
        plan = self.h.start("low")
        plan = self.h.service.host().gate_decide(
            plan["run_id"], expected_revision=1, mutation_id="approve-plan", gate_id="plan", approve=True
        )
        plan = self.h.service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="start-task", task_id="TASK-001", status="in_progress"
        )
        decision = json.loads((ROOT / "fixtures" / "devweave_v2" / "pending-decision.json").read_text(encoding="utf-8"))
        decision["created_revision"] = plan["revision"]
        plan = self.h.service.agent().decision_request(
            plan["run_id"], expected_revision=plan["revision"], mutation_id="ask-question", decision=decision
        )
        self.assertFalse(hasattr(self.h.service.agent(), "decision_resolve"))
        with self.assertRaises(DevWeaveError) as cancelled:
            self.h.service.host().decision_resolve(
                plan["run_id"], expected_revision=plan["revision"], mutation_id="cancel-answer",
                decision_id="question-1"
            )
        self.assertEqual(cancelled.exception.code, ErrorCode.INVALID_ARGUMENT)
        with self.assertRaises(DevWeaveError):
            self.h.service.host().decision_resolve(
                plan["run_id"], expected_revision=plan["revision"], mutation_id="bad-answer",
                decision_id="question-1", option_id="missing"
            )
        still_pending = self.h.service.agent().run_inspect(plan["run_id"])
        self.assertEqual(still_pending["pending_decision"]["decision_id"], "question-1")
        resolved = self.h.service.host().decision_resolve(
            plan["run_id"], expected_revision=plan["revision"], mutation_id="good-answer",
            decision_id="question-1", option_id="small"
        )
        self.assertIsNone(resolved["pending_decision"])
        self.assertEqual(resolved["tasks"]["TASK-001"]["status"], "in_progress")

    def test_task_definition_is_immutable_and_dependency_order_is_enforced(self) -> None:
        draft = self.h.draft("low")
        second = dict(draft["tasks"][0])
        second["task_id"] = "TASK-002"
        second["dependencies"] = ["TASK-001"]
        draft["tasks"].append(second)
        plan = self.h.service.host().run_start(draft, base_branch="main", base_ref=BASE_REF, run_branch="devweave/tasks")
        plan = self.h.service.host().gate_decide(plan["run_id"], expected_revision=1, mutation_id="approve", gate_id="plan", approve=True)
        with self.assertRaises(DevWeaveError) as dependency:
            self.h.service.agent().task_update(
                plan["run_id"], expected_revision=2, mutation_id="start-second", task_id="TASK-002", status="in_progress"
            )
        self.assertEqual(dependency.exception.code, ErrorCode.GATE_REQUIRED)
        before_definition = plan["tasks"]["TASK-001"]["definition"]
        plan = self.h.service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="complete-first", task_id="TASK-001", status="completed", progress="done"
        )
        self.assertEqual(plan["tasks"]["TASK-001"]["definition"], before_definition)

    def test_acceptance_requires_current_verification_and_detached_review(self) -> None:
        plan = self.h.start("standard")
        plan = self.h.service.host().gate_decide(
            plan["run_id"], expected_revision=1, mutation_id="approve-plan", gate_id="plan", approve=True
        )
        plan = self.h.service.agent().task_update(
            plan["run_id"], expected_revision=2, mutation_id="complete-task", task_id="TASK-001", status="completed"
        )
        with self.assertRaises(DevWeaveError) as unverified:
            self.h.service.agent().completion_request(
                plan["run_id"], expected_revision=3, mutation_id="premature-completion"
            )
        self.assertEqual(unverified.exception.code, ErrorCode.BLOCKED)
        plan = self.h.service.mutate(
            plan["run_id"], 3, "record-verification",
            lambda candidate: candidate["verification"].update({"status": "passed", "evidence_ids": ["VER-1"]}),
        )
        plan = self.h.service.agent().completion_request(
            plan["run_id"], expected_revision=4, mutation_id="completion-request"
        )
        self.assertEqual(plan["status"], "reviewing")
        with self.assertRaises(DevWeaveError) as missing:
            self.h.service.host().gate_decide(
                plan["run_id"], expected_revision=5, mutation_id="accept-no-review",
                gate_id="acceptance", approve=True,
            )
        self.assertEqual(missing.exception.code, ErrorCode.GATE_REQUIRED)
        with self.assertRaises(DevWeaveError) as reused:
            self.h.service.host().gate_decide(
                plan["run_id"], expected_revision=5, mutation_id="accept-reused-review",
                gate_id="acceptance", approve=True,
                review_result={
                    "detached": True, "implementation_thread_id": "thread-1", "reviewer_thread_id": "thread-1",
                    "round": 1, "unresolved_critical": False, "finding_ids": [],
                },
            )
        self.assertEqual(reused.exception.code, ErrorCode.BLOCKED)
        completed = self.h.service.host().gate_decide(
            plan["run_id"], expected_revision=5, mutation_id="accept-detached-review",
            gate_id="acceptance", approve=True,
            review_result={
                "detached": True, "implementation_thread_id": "thread-1", "reviewer_thread_id": "review-1",
                "round": 1, "unresolved_critical": False, "finding_ids": ["FIND-1"],
            },
        )
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["review"]["finding_ids"], ["FIND-1"])

    def test_reducer_is_deterministic_and_duplicate_events_do_not_duplicate_effects(self) -> None:
        plan = self.h.start("low")
        events = [
            {"event_id": "evt-1", "type": "thread_status", "value": "connected"},
            {"event_id": "evt-2", "type": "blocker", "value": "network-disabled"},
            {"event_id": "evt-2", "type": "blocker", "value": "different-duplicate"},
            {"event_id": "evt-3", "type": "unknown", "value": "ignored"},
        ]
        first = reduce_snapshot(plan, events)
        second = reduce_snapshot(plan, list(events))
        self.assertEqual(dumps(first), dumps(second))
        self.assertEqual(first.blockers, ("network-disabled",))


class AtomicStoreTests(unittest.TestCase):
    def test_crash_before_replace_preserves_old_revision(self) -> None:
        armed = False

        def fault(stage: str, path: Path) -> None:
            if armed and stage == "before_replace":
                raise RuntimeError("injected-before")

        h = RunServiceHarness(fault_hook=fault)
        try:
            plan = h.start("low")
            armed = True
            with self.assertRaises(RuntimeError):
                h.service.host().gate_decide(plan["run_id"], expected_revision=1, mutation_id="approve", gate_id="plan", approve=True)
            armed = False
            self.assertEqual(h.store.load(plan["run_id"])["revision"], 1)
        finally:
            h.close()

    def test_crash_after_replace_is_recoverable_by_idempotency_key(self) -> None:
        armed = False

        def fault(stage: str, path: Path) -> None:
            if armed and stage == "after_replace":
                raise RuntimeError("injected-after")

        h = RunServiceHarness(fault_hook=fault)
        try:
            plan = h.start("low")
            armed = True
            with self.assertRaises(RuntimeError):
                h.service.host().gate_decide(plan["run_id"], expected_revision=1, mutation_id="approve", gate_id="plan", approve=True)
            armed = False
            recovered = h.service.host().gate_decide(
                plan["run_id"], expected_revision=1, mutation_id="approve", gate_id="plan", approve=True
            )
            self.assertEqual(recovered["revision"], 2)
            self.assertEqual(recovered["status"], "implementing")
        finally:
            h.close()


if __name__ == "__main__":
    unittest.main()

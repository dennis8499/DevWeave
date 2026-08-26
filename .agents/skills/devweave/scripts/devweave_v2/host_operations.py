"""Strict host-only operation adapter used exclusively by the private bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .canonical import primitive, sha256
from .codex_doctor import CodexDoctor
from .contract_utils import boolean, integer, strict_object, text
from .errors import DevWeaveError, ErrorCode
from .git_port import GitAdapter
from .git_transaction import GitTransaction
from .plan_contracts import RunPlanDraft
from .run_service import RunService
from .run_start_journal import RunStartJournal
from .service_factory import build_run_service

HOST_METHODS = ("run_start", "run_resume", "decision_resolve", "gate_decide", "run_cancel")


class DoctorPort(Protocol):
    def probe(self, *, repository: Path, configured_path: str | None = None) -> dict: ...


class HostOperationAdapter:
    def __init__(
        self,
        repository: Path,
        *,
        service: RunService | None = None,
        doctor: DoctorPort | None = None,
        git: GitTransaction | None = None,
    ) -> None:
        self.repository = repository.resolve()
        self.service = service or build_run_service(self.repository)
        self.doctor = doctor or CodexDoctor()
        self.git = git or GitTransaction(self.repository, GitAdapter(self.repository))
        self.start_journal = RunStartJournal(self.repository)

    def call(self, method: str, params: Any) -> Any:
        if method not in HOST_METHODS:
            raise DevWeaveError(ErrorCode.FORBIDDEN, "Private bridge method is not host-allowlisted.")
        if not isinstance(params, dict):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "Host operation parameters must be an object.")
        return getattr(self, f"_{method}")(params)

    def _run_start(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = strict_object(raw, name="run_start", required=("draft", "slug"), optional=("codex_path",))
        parsed = RunPlanDraft.from_dict(data["draft"])
        slug = text(data["slug"], "slug", maximum=128)
        codex_path = data.get("codex_path")
        if codex_path is not None:
            codex_path = text(codex_path, "codex_path", maximum=1024)
        preflight = self.doctor.probe(repository=self.repository, configured_path=codex_path)
        journal = self.start_journal.load(parsed.run_id)
        journal_created = journal is None
        draft_digest = sha256(primitive(parsed))
        if journal is None:
            branch = self.git.preflight(run_id=parsed.run_id, slug=slug)
            journal = self.start_journal.begin({
                "schema_version": 2,
                "run_id": parsed.run_id,
                "slug": slug,
                "draft_digest": draft_digest,
                **branch,
                "status": "intent",
            })
        else:
            required = {
                "schema_version", "run_id", "slug", "draft_digest", "base_branch", "base_ref", "run_branch", "status",
            }
            if set(journal) != required or journal["draft_digest"] != draft_digest or journal["slug"] != slug:
                raise DevWeaveError(ErrorCode.CONFLICT, "Run-start retry does not match its recovery journal.")
            branch = {key: journal[key] for key in ("base_branch", "base_ref", "run_branch")}
        if journal["status"] == "intent":
            current_branch = self.git.git.branch()
            if current_branch == branch["base_branch"]:
                if not journal_created:
                    current = self.git.preflight(run_id=parsed.run_id, slug=slug)
                    if current != branch:
                        raise DevWeaveError(ErrorCode.CONFLICT, "Run-start Git preflight drifted during recovery.")
                self.git.start_preflighted(branch)
            elif current_branch != branch["run_branch"] or self.git.git.head() != branch["base_ref"]:
                raise DevWeaveError(ErrorCode.BLOCKED, "Run-start recovery requires the recorded base or run branch checkout.")
            journal = self.start_journal.mark(journal, "branch_started")
        self.git.assert_run(**branch)
        try:
            plan = self.service.host().run_start(primitive(parsed), **branch)
        except DevWeaveError as exc:
            if exc.code is not ErrorCode.CONFLICT or not self.service.store.exists(parsed.run_id):
                raise
            plan = self.service.inspect(parsed.run_id)
            if plan["plan"] != primitive(parsed) or any(plan[key] != branch[key] for key in branch):
                raise DevWeaveError(ErrorCode.CONFLICT, "Existing run does not match the run-start recovery journal.") from exc
        self.start_journal.mark(journal, "finalized")
        return {"preflight": preflight, "run": plan}

    def _run_resume(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = strict_object(raw, name="run_resume", required=("run_id",), optional=("codex_path",))
        codex_path = data.get("codex_path")
        if codex_path is not None:
            codex_path = text(codex_path, "codex_path", maximum=1024)
        preflight = self.doctor.probe(repository=self.repository, configured_path=codex_path)
        plan = self.service.host().run_resume(text(data["run_id"], "run_id", maximum=128))
        self.git.assert_run(
            run_branch=plan["run_branch"], base_branch=plan["base_branch"], base_ref=plan["base_ref"]
        )
        return {"preflight": preflight, "run": plan}

    def _decision_resolve(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = strict_object(
            raw, name="decision_resolve",
            required=("run_id", "expected_revision", "mutation_id", "decision_id"),
            optional=("option_id", "other"),
        )
        return self.service.host().decision_resolve(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128),
            decision_id=text(data["decision_id"], "decision_id", maximum=128),
            option_id=text(data.get("option_id", ""), "option_id", minimum=0, maximum=128),
            other=text(data.get("other", ""), "other", minimum=0, maximum=2048),
        )

    def _gate_decide(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = strict_object(
            raw, name="gate_decide",
            required=("run_id", "expected_revision", "mutation_id", "gate_id", "approve"),
            optional=("review_result",),
        )
        return self.service.host().gate_decide(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128),
            gate_id=text(data["gate_id"], "gate_id", maximum=128),
            approve=boolean(data["approve"], "approve"),
            review_result=data.get("review_result"),
        )

    def _run_cancel(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = strict_object(raw, name="run_cancel", required=("run_id", "expected_revision", "mutation_id"))
        return self.service.host().run_cancel(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128),
        )

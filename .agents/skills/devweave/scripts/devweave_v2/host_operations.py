"""Strict host-only operation adapter used exclusively by the private bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .codex_doctor import CodexDoctor
from .contract_utils import boolean, integer, strict_object, text
from .errors import DevWeaveError, ErrorCode
from .git_port import GitAdapter
from .git_transaction import GitTransaction
from .run_service import RunService
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

    def call(self, method: str, params: Any) -> Any:
        if method not in HOST_METHODS:
            raise DevWeaveError(ErrorCode.FORBIDDEN, "Private bridge method is not host-allowlisted.")
        if not isinstance(params, dict):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "Host operation parameters must be an object.")
        return getattr(self, f"_{method}")(params)

    def _run_start(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = strict_object(raw, name="run_start", required=("draft", "slug"), optional=("codex_path",))
        codex_path = data.get("codex_path")
        if codex_path is not None:
            codex_path = text(codex_path, "codex_path", maximum=1024)
        preflight = self.doctor.probe(repository=self.repository, configured_path=codex_path)
        if not isinstance(data["draft"], dict) or not isinstance(data["draft"].get("run_id"), str):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "run_start draft must contain a run_id.")
        branch = self.git.start_branch(run_id=data["draft"]["run_id"], slug=text(data["slug"], "slug", maximum=128))
        plan = self.service.host().run_start(data["draft"], **branch)
        return {"preflight": preflight, "run": plan}

    def _run_resume(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = strict_object(raw, name="run_resume", required=("run_id",), optional=("codex_path",))
        codex_path = data.get("codex_path")
        if codex_path is not None:
            codex_path = text(codex_path, "codex_path", maximum=1024)
        preflight = self.doctor.probe(repository=self.repository, configured_path=codex_path)
        return {"preflight": preflight, "run": self.service.host().run_resume(text(data["run_id"], "run_id", maximum=128))}

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

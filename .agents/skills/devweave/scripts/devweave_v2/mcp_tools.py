"""Exact agent-facing MCP tool catalog and strict dispatch adapter."""

from __future__ import annotations

from typing import Any, Callable

from .contract_utils import boolean, integer, relative_path, sequence, strict_object, strings, text
from .errors import DevWeaveError, ErrorCode
from .run_service import AgentFacade

AGENT_TOOLS = (
    "run_inspect",
    "context_read",
    "plan_save",
    "decision_request",
    "task_update",
    "verification_run",
    "verification_read",
    "completion_request",
)

HOST_ONLY_OPERATIONS = ("run_start", "run_resume", "decision_resolve", "gate_decide", "run_cancel")


def object_schema(properties: dict[str, Any], required: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


COMMON = {
    "run_id": {"type": "string", "minLength": 1, "maxLength": 128},
    "expected_revision": {"type": "integer", "minimum": 1},
    "mutation_id": {"type": "string", "minLength": 1, "maxLength": 128},
}

TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "run_inspect", "description": "Read the bounded authoritative state for one DevWeave run.",
        "inputSchema": object_schema({"run_id": COMMON["run_id"]}, ("run_id",)),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "context_read", "description": "Read one allowlisted documentation context file for the current run.",
        "inputSchema": object_schema({"run_id": COMMON["run_id"], "path": {"type": "string", "minLength": 1, "maxLength": 512}}, ("run_id", "path")),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "plan_save", "description": "Replace the typed plan draft before its planning gates are approved.",
        "inputSchema": object_schema({**COMMON, "draft": {"type": "object"}, "risk_signals": {"type": "array", "items": {"type": "string"}, "maxItems": 32}}, ("run_id", "expected_revision", "mutation_id", "draft")),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "decision_request", "description": "Create one typed pending decision that only the host can resolve.",
        "inputSchema": object_schema({**COMMON, "decision": {"type": "object"}}, ("run_id", "expected_revision", "mutation_id", "decision")),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "task_update", "description": "Advance lifecycle state for an immutable task definition.",
        "inputSchema": object_schema({**COMMON, "task_id": {"type": "string"}, "status": {"enum": ["in_progress", "completed"]}, "progress": {"type": "string", "maxLength": 2048}}, ("run_id", "expected_revision", "mutation_id", "task_id", "status")),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "verification_run", "description": "Run the frozen verification policy for the run's current risk level.",
        "inputSchema": object_schema({**COMMON, "paths": {"type": "array", "items": {"type": "string"}, "maxItems": 256}, "release": {"type": "boolean", "default": False}}, ("run_id", "expected_revision", "mutation_id")),
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "verification_read", "description": "Read bounded verification and review summaries for one run.",
        "inputSchema": object_schema({"run_id": COMMON["run_id"]}, ("run_id",)),
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "completion_request", "description": "Request host review after all immutable tasks are complete.",
        "inputSchema": object_schema(COMMON, ("run_id", "expected_revision", "mutation_id")),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
)


class McpToolAdapter:
    def __init__(self, facade: AgentFacade) -> None:
        self.facade = facade
        self._dispatch: dict[str, Callable[[dict[str, Any]], Any]] = {
            "run_inspect": self._run_inspect,
            "context_read": self._context_read,
            "plan_save": self._plan_save,
            "decision_request": self._decision_request,
            "task_update": self._task_update,
            "verification_run": self._verification_run,
            "verification_read": self._verification_read,
            "completion_request": self._completion_request,
        }

    def call(self, name: str, arguments: Any) -> Any:
        handler = self._dispatch.get(name)
        if handler is None:
            raise DevWeaveError(ErrorCode.FORBIDDEN, "MCP tool is not agent-allowlisted.", {"tool": name})
        if not isinstance(arguments, dict):
            raise DevWeaveError(ErrorCode.INVALID_TYPE, "MCP tool arguments must be an object.")
        return handler(arguments)

    def _run_inspect(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="run_inspect", required=("run_id",))
        return self.facade.run_inspect(text(data["run_id"], "run_id", maximum=128))

    def _context_read(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="context_read", required=("run_id", "path"))
        return self.facade.context_read(text(data["run_id"], "run_id", maximum=128), relative_path(data["path"], "path"))

    def _plan_save(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="plan_save", required=("run_id", "expected_revision", "mutation_id", "draft"), optional=("risk_signals",))
        signals = strings(data.get("risk_signals", []), "risk_signals", maximum=32)
        return self.facade.plan_save(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128),
            draft=data["draft"], risk_signals=list(signals),
        )

    def _decision_request(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="decision_request", required=("run_id", "expected_revision", "mutation_id", "decision"))
        return self.facade.decision_request(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128), decision=data["decision"],
        )

    def _task_update(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="task_update", required=("run_id", "expected_revision", "mutation_id", "task_id", "status"), optional=("progress",))
        return self.facade.task_update(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128),
            task_id=text(data["task_id"], "task_id", maximum=128), status=text(data["status"], "status", maximum=32),
            progress=text(data.get("progress", ""), "progress", minimum=0, maximum=2048),
        )

    def _verification_run(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="verification_run", required=("run_id", "expected_revision", "mutation_id"), optional=("paths", "release"))
        paths = [relative_path(item, f"paths[{index}]") for index, item in enumerate(sequence(data.get("paths", []), "paths"))]
        return self.facade.verification_run(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128), paths=paths,
            release=boolean(data.get("release", False), "release"),
        )

    def _verification_read(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="verification_read", required=("run_id",))
        return self.facade.verification_read(text(data["run_id"], "run_id", maximum=128))

    def _completion_request(self, raw: dict[str, Any]) -> Any:
        data = strict_object(raw, name="completion_request", required=("run_id", "expected_revision", "mutation_id"))
        return self.facade.completion_request(
            text(data["run_id"], "run_id", maximum=128),
            expected_revision=integer(data["expected_revision"], "expected_revision", minimum=1),
            mutation_id=text(data["mutation_id"], "mutation_id", maximum=128),
        )

"""Bounded stdio JSON-RPC server for the project-scoped DevWeave MCP."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any, BinaryIO

from .errors import DevWeaveError, ErrorCode
from .mcp_tools import McpToolAdapter, TOOL_DEFINITIONS
from .service_factory import build_run_service
from .version import VERSION

SUPPORTED_PROTOCOLS = ("2025-06-18", "2024-11-05")
MAX_MESSAGE_BYTES = 1_000_000


class McpSession:
    def __init__(self, tools: McpToolAdapter) -> None:
        self.tools = tools
        self.initialized = False

    def handle(self, raw: Any) -> dict[str, Any] | None:
        request_id: Any = raw.get("id") if isinstance(raw, dict) else None
        try:
            if not isinstance(raw, dict) or raw.get("jsonrpc") != "2.0" or not isinstance(raw.get("method"), str):
                return rpc_error(request_id, -32600, "Invalid JSON-RPC request")
            allowed = {"jsonrpc", "id", "method", "params"}
            if set(raw) - allowed:
                return rpc_error(request_id, -32600, "Unknown JSON-RPC envelope fields")
            method = raw["method"]
            params = raw.get("params", {})
            if method == "initialize":
                return self._initialize(request_id, params)
            if method == "notifications/initialized":
                if request_id is not None:
                    return rpc_error(request_id, -32600, "initialized must be a notification")
                if not self.initialized:
                    return None
                return None
            if not self.initialized:
                return rpc_error(request_id, -32002, "MCP session is not initialized")
            if method == "ping":
                return rpc_result(request_id, {})
            if method == "tools/list":
                if params is None:
                    params = {}
                if not isinstance(params, dict) or set(params) - {"cursor", "_meta"}:
                    return rpc_error(request_id, -32602, "tools/list parameters are invalid")
                if params.get("cursor") is not None:
                    return rpc_error(request_id, -32602, "tools/list cursor is invalid")
                if "_meta" in params and params["_meta"] is not None and not isinstance(params["_meta"], dict):
                    return rpc_error(request_id, -32602, "tools/list metadata is invalid")
                return rpc_result(request_id, {"tools": list(TOOL_DEFINITIONS)})
            if method == "tools/call":
                if not isinstance(params, dict) or set(params) != {"name", "arguments"} or not isinstance(params.get("name"), str):
                    return rpc_error(request_id, -32602, "tools/call parameters are invalid")
                try:
                    result = self.tools.call(params["name"], params["arguments"])
                    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    return rpc_result(request_id, {
                        "content": [{"type": "text", "text": serialized}],
                        "structuredContent": result,
                        "isError": False,
                    })
                except DevWeaveError as exc:
                    payload = {"ok": False, "error": exc.as_dict()}
                    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    return rpc_result(request_id, {
                        "content": [{"type": "text", "text": serialized}],
                        "structuredContent": payload,
                        "isError": True,
                    })
            if method.startswith("notifications/") and request_id is None:
                return None
            return rpc_error(request_id, -32601, "Method not found")
        except DevWeaveError as exc:
            return rpc_error(request_id, -32602, exc.message, exc.as_dict())
        except Exception:
            return rpc_error(request_id, -32603, "Internal MCP server error")

    def _initialize(self, request_id: Any, params: Any) -> dict[str, Any]:
        if self.initialized:
            return rpc_error(request_id, -32600, "MCP session is already initialized")
        if not isinstance(params, dict):
            return rpc_error(request_id, -32602, "initialize parameters must be an object")
        protocol = params.get("protocolVersion")
        if protocol not in SUPPORTED_PROTOCOLS:
            return rpc_error(request_id, -32602, "Unsupported MCP protocol version", {"supported": list(SUPPORTED_PROTOCOLS)})
        if not isinstance(params.get("clientInfo"), dict) or not isinstance(params.get("capabilities"), dict):
            return rpc_error(request_id, -32602, "initialize requires clientInfo and capabilities")
        self.initialized = True
        return rpc_result(request_id, {
            "protocolVersion": protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "devweave", "version": VERSION},
            "instructions": "Use only the eight governed tools exposed by this project server.",
        })


def rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def run_stdio(repository: Path, stdin: BinaryIO | None = None, stdout: BinaryIO | None = None) -> int:
    input_stream = stdin or sys.stdin.buffer
    output_stream = stdout or sys.stdout.buffer
    session = McpSession(McpToolAdapter(build_run_service(repository).agent()))
    while True:
        line = input_stream.readline(MAX_MESSAGE_BYTES + 1)
        if not line:
            return 0
        if len(line) > MAX_MESSAGE_BYTES or not line.endswith(b"\n"):
            while line and not line.endswith(b"\n"):
                line = input_stream.readline(MAX_MESSAGE_BYTES + 1)
            response = rpc_error(None, -32700, "MCP message exceeds framing limit")
        else:
            try:
                request = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                response = rpc_error(None, -32700, "Parse error")
            else:
                response = session.handle(request)
        if response is not None:
            encoded = (json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            if len(encoded) > MAX_MESSAGE_BYTES:
                encoded = (json.dumps(rpc_error(response.get("id"), -32603, "MCP response exceeds framing limit"), separators=(",", ":")) + "\n").encode("utf-8")
            output_stream.write(encoded)
            output_stream.flush()

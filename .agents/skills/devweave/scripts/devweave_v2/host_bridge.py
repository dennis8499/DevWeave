"""Authenticated private child-stdio bridge for host-only capabilities."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sys
from pathlib import Path
from typing import Any, BinaryIO, Callable, Protocol

from .errors import DevWeaveError
from .host_operations import HostOperationAdapter

MAX_BRIDGE_MESSAGE_BYTES = 1_000_000


class HostCalls(Protocol):
    def call(self, method: str, params: Any) -> Any: ...


class HostBridgeSession:
    def __init__(self, operations: HostCalls, *, nonce_factory: Callable[[int], str] = secrets.token_hex) -> None:
        self.operations = operations
        self.nonce_factory = nonce_factory
        self.state = "awaiting_hello"
        self._token: bytearray | None = None
        self._client_nonce = ""
        self._challenge = ""
        self.session_id = ""

    def handle(self, raw: Any) -> dict[str, Any]:
        if self.state == "closed":
            return bridge_error(None, "BRIDGE_CLOSED", "Bridge session is closed.")
        if not isinstance(raw, dict):
            return self._close_error(None, "BRIDGE_PROTOCOL", "Bridge message must be an object.")
        if self.state == "awaiting_hello":
            return self._hello(raw)
        if self.state == "awaiting_proof":
            return self._proof(raw)
        return self._request(raw)

    def close(self) -> None:
        if self._token is not None:
            for index in range(len(self._token)):
                self._token[index] = 0
        self._token = None
        self.state = "closed"

    def _hello(self, raw: dict[str, Any]) -> dict[str, Any]:
        if set(raw) != {"type", "token", "client_nonce"} or raw.get("type") != "hello":
            return self._close_error(None, "BRIDGE_HANDSHAKE", "Expected bridge hello.")
        token = raw.get("token")
        client_nonce = raw.get("client_nonce")
        if not isinstance(token, str) or not 32 <= len(token) <= 256 or not isinstance(client_nonce, str) or not 16 <= len(client_nonce) <= 128:
            return self._close_error(None, "BRIDGE_HANDSHAKE", "Bridge hello is malformed.")
        self._token = bytearray(token.encode("utf-8"))
        self._client_nonce = client_nonce
        self._challenge = self.nonce_factory(32)
        self.session_id = self.nonce_factory(16)
        self.state = "awaiting_proof"
        return {
            "type": "challenge",
            "challenge": self._challenge,
            "session_id": self.session_id,
            "server_proof": self._digest("server"),
        }

    def _proof(self, raw: dict[str, Any]) -> dict[str, Any]:
        if set(raw) != {"type", "client_proof"} or raw.get("type") != "proof" or not isinstance(raw.get("client_proof"), str):
            return self._close_error(None, "BRIDGE_HANDSHAKE", "Expected bridge proof.")
        if not hmac.compare_digest(raw["client_proof"], self._digest("client")):
            return self._close_error(None, "BRIDGE_AUTH", "Bridge proof was rejected.")
        self.state = "ready"
        return {"type": "ready", "session_id": self.session_id}

    def _request(self, raw: dict[str, Any]) -> dict[str, Any]:
        request_id = raw.get("id")
        if set(raw) != {"id", "method", "params", "session_id"}:
            return bridge_error(request_id, "BRIDGE_PROTOCOL", "Host request envelope is invalid.")
        if raw.get("session_id") != self.session_id:
            return bridge_error(request_id, "BRIDGE_AUTH", "Host session id is invalid.")
        if not isinstance(raw.get("method"), str):
            return bridge_error(request_id, "BRIDGE_PROTOCOL", "Host method must be a string.")
        try:
            result = self.operations.call(raw["method"], raw["params"])
            return {"id": request_id, "ok": True, "result": result}
        except DevWeaveError as exc:
            return {"id": request_id, "ok": False, "error": exc.as_dict()}
        except Exception:
            return bridge_error(request_id, "BRIDGE_INTERNAL", "Internal host bridge error.")

    def _digest(self, role: str) -> str:
        if self._token is None:
            return ""
        message = f"{role}:{self._client_nonce}:{self._challenge}:{self.session_id}".encode("utf-8")
        return hmac.new(bytes(self._token), message, hashlib.sha256).hexdigest()

    def _close_error(self, request_id: Any, code: str, message: str) -> dict[str, Any]:
        self.close()
        return bridge_error(request_id, code, message)


def bridge_error(request_id: Any, code: str, message: str) -> dict[str, Any]:
    return {"id": request_id, "ok": False, "error": {"code": code, "message": message, "details": {}}}


def run_host_stdio(repository: Path, stdin: BinaryIO | None = None, stdout: BinaryIO | None = None) -> int:
    input_stream = stdin or sys.stdin.buffer
    output_stream = stdout or sys.stdout.buffer
    session = HostBridgeSession(HostOperationAdapter(repository))
    try:
        while True:
            line = input_stream.readline(MAX_BRIDGE_MESSAGE_BYTES + 1)
            if not line:
                return 0
            if len(line) > MAX_BRIDGE_MESSAGE_BYTES or not line.endswith(b"\n"):
                while line and not line.endswith(b"\n"):
                    line = input_stream.readline(MAX_BRIDGE_MESSAGE_BYTES + 1)
                response = bridge_error(None, "BRIDGE_FRAME", "Bridge message exceeds framing limit.")
                session.close()
            else:
                try:
                    raw = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    response = bridge_error(None, "BRIDGE_PARSE", "Bridge message is not valid JSON.")
                    session.close()
                else:
                    response = session.handle(raw)
            encoded = (json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            if len(encoded) > MAX_BRIDGE_MESSAGE_BYTES:
                encoded = (json.dumps(bridge_error(response.get("id"), "BRIDGE_FRAME", "Bridge response exceeds framing limit."), separators=(",", ":")) + "\n").encode("utf-8")
            output_stream.write(encoded)
            output_stream.flush()
            if session.state == "closed":
                return 3
    finally:
        session.close()

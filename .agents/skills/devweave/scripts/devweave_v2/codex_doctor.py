"""Fail-closed Codex CLI resolution, version probe, and app-server schema probe."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Protocol, Sequence

from .errors import DevWeaveError, ErrorCode
from .redaction import bounded_text
from .verification_engine import ProcessPort, ProcessResult, SubprocessRunner
from .version import SCHEMA_VERSION, VERSION

REQUIRED_APP_SERVER_DESCRIPTORS = (
    "initialize", "thread/start", "thread/resume", "thread/read", "turn/start",
    "turn/steer", "turn/interrupt", "review/start", "mcpServerStatus/list",
    "config/mcpServer/reload", "item/completed",
)
MAX_SCHEMA_FILES = 512
MAX_SCHEMA_BYTES = 10_000_000


class CodexDoctor:
    def __init__(self, *, runner: ProcessPort | None = None, which=shutil.which) -> None:
        self.runner = runner or SubprocessRunner()
        self.which = which

    def probe(self, *, repository: Path, configured_path: str | None = None) -> dict:
        executable, source = self.resolve(configured_path)
        version_result = self.runner.run((str(executable), "--version"), cwd=repository.resolve(), timeout_seconds=10)
        if version_result.timed_out or version_result.exit_code != 0:
            raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Codex version probe failed.")
        version, truncated = bounded_text(version_result.stdout, max_bytes=16_384)
        if truncated or not version.strip():
            raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Codex version probe returned invalid output.")
        with tempfile.TemporaryDirectory(prefix="devweave-codex-schema-") as temporary:
            output = Path(temporary)
            schema_result = self.runner.run(
                (str(executable), "app-server", "generate-json-schema", "--out", str(output)),
                cwd=repository.resolve(), timeout_seconds=30,
            )
            if schema_result.timed_out or schema_result.exit_code != 0:
                raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Codex app-server schema generation failed.")
            schema_hash, files = validate_schema_bundle(output)
        return {
            "schema_version": SCHEMA_VERSION,
            "devweave_version": VERSION,
            "status": "ready",
            "codex": {
                "path": str(executable),
                "source": source,
                "sha256": hash_file(executable),
                "version": version.strip()[:512],
            },
            "app_server": {
                "transport": "stdio-jsonl",
                "experimental_api": False,
                "schema_sha256": schema_hash,
                "schema_files": files,
                "required_descriptors": list(REQUIRED_APP_SERVER_DESCRIPTORS),
            },
            "certification": {"platform": "windows-x64-vscode", "status": "probe-only"},
        }

    def resolve(self, configured_path: str | None) -> tuple[Path, str]:
        if configured_path is not None:
            candidate = Path(configured_path)
            if not candidate.is_absolute():
                raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Configured Codex path must be absolute.")
            path = candidate.resolve()
            source = "configured"
        else:
            discovered = self.which("codex")
            if not discovered:
                raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Codex CLI was not found on PATH.")
            path = Path(discovered).resolve()
            source = "path"
        if not path.is_file():
            raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Resolved Codex path is not a file.")
        if os.name != "nt" and not os.access(path, os.X_OK):
            raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Resolved Codex file is not executable.")
        return path, source


def validate_schema_bundle(root: Path) -> tuple[str, int]:
    files = sorted(path for path in root.rglob("*.json") if path.is_file())
    if not files or len(files) > MAX_SCHEMA_FILES:
        raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Codex schema bundle has an invalid file count.")
    combined = hashlib.sha256()
    searchable: list[str] = []
    total = 0
    for path in files:
        raw = path.read_bytes()
        total += len(raw)
        if total > MAX_SCHEMA_BYTES:
            raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Codex schema bundle exceeds its byte limit.")
        try:
            json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Codex schema bundle contains invalid JSON.") from exc
        relative = path.relative_to(root).as_posix()
        combined.update(relative.encode("utf-8"))
        combined.update(b"\0")
        combined.update(hashlib.sha256(raw).digest())
        searchable.append(raw.decode("utf-8"))
    corpus = "\n".join(searchable)
    missing = [item for item in REQUIRED_APP_SERVER_DESCRIPTORS if item not in corpus]
    if missing:
        raise DevWeaveError(
            ErrorCode.CODEX_UNAVAILABLE,
            "Codex app-server schema lacks required stable descriptors.",
            {"missing": missing},
        )
    return combined.hexdigest(), len(files)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

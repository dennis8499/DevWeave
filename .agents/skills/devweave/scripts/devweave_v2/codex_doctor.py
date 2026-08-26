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
CODE_MODE_HOST_NAME = "codex-code-mode-host.exe" if os.name == "nt" else "codex-code-mode-host"
CODEX_BINARY_NAME = "codex.exe" if os.name == "nt" else "codex"
NPM_WRAPPER_NAMES = frozenset({"codex", "codex.cmd", "codex.ps1"})
MAX_NPM_NATIVE_CANDIDATES = 8


class CodexDoctor:
    def __init__(self, *, runner: ProcessPort | None = None, which=shutil.which) -> None:
        self.runner = runner or SubprocessRunner()
        self.which = which

    def probe(self, *, repository: Path, configured_path: str | None = None) -> dict:
        executable, source = self.resolve(configured_path)
        code_mode_host = self.resolve_code_mode_host(executable)
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
                "code_mode_host": {
                    "path": str(code_mode_host),
                    "sha256": hash_file(code_mode_host),
                },
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
        path = self.resolve_npm_native(path)
        if os.name != "nt" and not os.access(path, os.X_OK):
            raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Resolved Codex file is not executable.")
        return path, source

    def resolve_npm_native(self, executable: Path) -> Path:
        if executable.name.casefold() not in NPM_WRAPPER_NAMES:
            return executable
        package_root = executable.parent / "node_modules" / "@openai" / "codex"
        if not package_root.is_dir():
            return executable
        matches = list(
            package_root.glob(
                f"node_modules/@openai/codex-*/vendor/*/bin/{CODEX_BINARY_NAME}"
            )
        )
        if len(matches) > MAX_NPM_NATIVE_CANDIDATES:
            raise DevWeaveError(
                ErrorCode.CODEX_UNAVAILABLE,
                "Codex npm installation contains too many native candidates.",
            )
        candidates: set[Path] = set()
        for match in matches:
            native = match.resolve()
            companion = (native.parent / CODE_MODE_HOST_NAME).resolve()
            if native.is_file() and companion.is_file():
                candidates.add(native)
        if len(candidates) > 1:
            raise DevWeaveError(
                ErrorCode.CODEX_UNAVAILABLE,
                "Codex npm wrapper resolves to multiple native bundles.",
                {"candidate_count": len(candidates)},
            )
        return next(iter(candidates), executable)

    def resolve_code_mode_host(self, executable: Path) -> Path:
        companion = (executable.parent / CODE_MODE_HOST_NAME).resolve()
        if not companion.is_file():
            raise DevWeaveError(
                ErrorCode.CODEX_UNAVAILABLE,
                "Codex code-mode host companion is unavailable.",
                {"required_companion": CODE_MODE_HOST_NAME},
            )
        if os.name != "nt" and not os.access(companion, os.X_OK):
            raise DevWeaveError(ErrorCode.CODEX_UNAVAILABLE, "Codex code-mode host is not executable.")
        return companion


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

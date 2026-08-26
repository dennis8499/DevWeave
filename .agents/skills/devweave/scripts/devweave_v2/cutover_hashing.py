from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .errors import DevWeaveError, ErrorCode


MAX_FILE_BYTES = 50_000_000
PRE_FINALIZER_MANAGED_DELETIONS = frozenset(
    {
        "wiki/architecture/devweave-knowledge-workflow.md",
        "wiki/modules/command-policy-engine.md",
        "wiki/modules/knowledge-engine.md",
        "wiki/modules/vscode-extension.md",
        "wiki/overview.md",
    }
)


def canonical_file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise DevWeaveError(
            ErrorCode.FORBIDDEN,
            "Cutover hashes only regular files.",
            {"path": str(path)},
        )
    return _canonical_bytes_sha256(path.read_bytes(), label=str(path))


def git_file_sha256(repository: Path, revision: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=repository,
        check=False,
        capture_output=True,
        shell=False,
    )
    if result.returncode != 0:
        raise DevWeaveError(
            ErrorCode.NOT_FOUND,
            "A managed pre-finalizer deletion has no immutable Git source.",
            {"path": relative, "revision": revision},
        )
    return _canonical_bytes_sha256(result.stdout, label=f"{revision}:{relative}")


def _canonical_bytes_sha256(data: bytes, *, label: str) -> str:
    if len(data) > MAX_FILE_BYTES:
        raise DevWeaveError(
            ErrorCode.BOUND_EXCEEDED,
            "Cutover file exceeds the hash bound.",
            {"path": label},
        )
    if b"\x00" not in data:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()

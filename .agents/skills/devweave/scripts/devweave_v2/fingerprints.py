"""Portable repository snapshots for verification effect reconciliation."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .canonical import sha256


@dataclass(frozen=True, slots=True)
class FileObservation:
    kind: str
    size: int
    digest: str


IGNORED_PREFIXES = (".git/", ".devweave/runtime/")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(repository: Path) -> dict[str, FileObservation]:
    root = repository.resolve()
    result: dict[str, FileObservation] = {}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root).as_posix()
        directories[:] = sorted(
            name for name in directories
            if not _ignored(f"{relative_dir}/{name}/")
        )
        for name in sorted(files):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if _ignored(relative):
                continue
            if path.is_symlink():
                target = os.readlink(path)
                result[relative] = FileObservation("symlink", len(target.encode("utf-8")), hashlib.sha256(target.encode("utf-8")).hexdigest())
            elif path.is_file():
                stat = path.stat()
                result[relative] = FileObservation("file", stat.st_size, file_digest(path))
    return result


def snapshot_digest(snapshot: dict[str, FileObservation]) -> str:
    return sha256(
        [
            {"path": path, "kind": item.kind, "size": item.size, "digest": item.digest}
            for path, item in sorted(snapshot.items())
        ]
    )


def changed_paths(before: dict[str, FileObservation], after: dict[str, FileObservation]) -> tuple[str, ...]:
    return tuple(sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path)))


def _ignored(path: str) -> bool:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in IGNORED_PREFIXES)

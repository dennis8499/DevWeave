"""Bounded Git observations used by the destructive cutover preflight."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .errors import DevWeaveError, ErrorCode


def git(repository: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=repository, check=True, capture_output=True,
            text=True, encoding="utf-8", errors="strict", shell=False,
        )
    except (subprocess.CalledProcessError, UnicodeError) as exc:
        raise DevWeaveError(
            ErrorCode.COMMAND_FAILED,
            "Git cutover preflight failed.",
            {"args": list(arguments)},
        ) from exc
    return result.stdout


def git_files(repository: Path) -> tuple[str, ...]:
    raw = _git_bytes(repository, "ls-files", "-z")
    try:
        return tuple(item.decode("utf-8") for item in raw.split(b"\0") if item)
    except UnicodeDecodeError as exc:
        raise DevWeaveError(ErrorCode.INVALID_VALUE, "Git contains a non-UTF-8 tracked path.") from exc


def git_status_paths(repository: Path) -> tuple[str, ...]:
    raw = _git_bytes(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = raw.split(b"\0")
    paths: set[str] = set()
    index = 0
    try:
        while index < len(entries) and entries[index]:
            entry = entries[index]
            if len(entry) < 4 or entry[2:3] != b" ":
                raise DevWeaveError(ErrorCode.INVALID_VALUE, "Git returned malformed porcelain status.")
            status = entry[:2].decode("ascii")
            paths.add(entry[3:].decode("utf-8").replace("\\", "/"))
            index += 1
            if "R" in status or "C" in status:
                if index >= len(entries) or not entries[index]:
                    raise DevWeaveError(ErrorCode.INVALID_VALUE, "Git rename status is incomplete.")
                paths.add(entries[index].decode("utf-8").replace("\\", "/"))
                index += 1
    except UnicodeDecodeError as exc:
        raise DevWeaveError(ErrorCode.INVALID_VALUE, "Git status contains a non-UTF-8 path.") from exc
    return tuple(sorted(paths))


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=repository, check=True, capture_output=True, shell=False,
        )
    except subprocess.CalledProcessError as exc:
        raise DevWeaveError(
            ErrorCode.COMMAND_FAILED,
            "Git cutover preflight failed.",
            {"args": list(arguments)},
        ) from exc
    return result.stdout

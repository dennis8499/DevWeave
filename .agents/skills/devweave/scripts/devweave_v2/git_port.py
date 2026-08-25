"""Shell-free Git adapter and run-owned transaction coordinator."""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, Sequence

from .contract_utils import relative_path
from .errors import DevWeaveError, ErrorCode

SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")


@dataclass(frozen=True, slots=True)
class GitStatusEntry:
    code: str
    path: str
    original_path: str = ""


class GitPort(Protocol):
    def root(self) -> Path: ...
    def head(self) -> str: ...
    def branch(self) -> str: ...
    def resolve_ref(self, ref: str) -> str: ...
    def status(self) -> tuple[GitStatusEntry, ...]: ...
    def branch_exists(self, branch: str) -> bool: ...
    def switch_new_branch(self, branch: str) -> None: ...
    def stage(self, paths: Sequence[str]) -> None: ...
    def staged_paths(self) -> tuple[str, ...]: ...
    def commit(self, message: str) -> str: ...
    def list_tree(self, ref: str, prefix: str) -> tuple[str, ...]: ...
    def read_tree_file(self, ref: str, path: str) -> bytes: ...


class GitAdapter:
    """Production Git port. Every invocation is argv-based with shell disabled."""

    def __init__(self, repository: Path) -> None:
        self.repository = repository.resolve()
        self.invocations: list[tuple[str, ...]] = []

    def _run(self, args: Sequence[str], *, check: bool = True, text: bool = True) -> subprocess.CompletedProcess:
        argv = ("git", "-C", str(self.repository), *args)
        self.invocations.append(tuple(args))
        try:
            return subprocess.run(
                argv,
                check=check,
                capture_output=True,
                text=text,
                encoding="utf-8" if text else None,
                shell=False,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            stderr = ""
            if isinstance(exc, subprocess.CalledProcessError):
                stderr = (exc.stderr or "")[:2_048]
            raise DevWeaveError(
                ErrorCode.COMMAND_FAILED,
                "Git operation failed.",
                {"operation": args[0] if args else "unknown", "diagnostic": stderr},
            ) from exc

    def root(self) -> Path:
        return Path(self._run(("rev-parse", "--show-toplevel")).stdout.strip()).resolve()

    def head(self) -> str:
        return self._run(("rev-parse", "HEAD")).stdout.strip()

    def branch(self) -> str:
        result = self._run(("symbolic-ref", "--quiet", "--short", "HEAD"), check=False)
        if result.returncode != 0 or not result.stdout.strip():
            raise DevWeaveError(ErrorCode.BLOCKED, "Detached HEAD is not a valid run base.")
        return result.stdout.strip()

    def resolve_ref(self, ref: str) -> str:
        safe = validate_git_ref(ref)
        result = self._run(("rev-parse", "--verify", f"{safe}^{{commit}}"))
        resolved = result.stdout.strip()
        if not re.fullmatch(r"[0-9a-fA-F]{40,64}", resolved):
            raise DevWeaveError(ErrorCode.COMMAND_FAILED, "Git returned an invalid object id.")
        return resolved.lower()

    def status(self) -> tuple[GitStatusEntry, ...]:
        output = self._run(("status", "--porcelain=v1", "-z", "--untracked-files=all")).stdout
        records = output.split("\0")
        entries: list[GitStatusEntry] = []
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < 4:
                raise DevWeaveError(ErrorCode.PROTOCOL_ERROR, "Git status record is malformed.")
            code = record[:2]
            path = record[3:].replace("\\", "/")
            original = ""
            if "R" in code or "C" in code:
                if index >= len(records) or not records[index]:
                    raise DevWeaveError(ErrorCode.PROTOCOL_ERROR, "Git rename status is malformed.")
                original = records[index].replace("\\", "/")
                index += 1
            entries.append(GitStatusEntry(code, path, original))
        return tuple(entries)

    def branch_exists(self, branch: str) -> bool:
        safe = validate_git_ref(branch)
        result = self._run(("show-ref", "--verify", "--quiet", f"refs/heads/{safe}"), check=False)
        return result.returncode == 0

    def switch_new_branch(self, branch: str) -> None:
        self._run(("switch", "-c", validate_git_ref(branch)))

    def stage(self, paths: Sequence[str]) -> None:
        if not paths:
            raise DevWeaveError(ErrorCode.INVALID_ARGUMENT, "No declared paths were supplied for staging.")
        self._run(("add", "--", *paths))

    def staged_paths(self) -> tuple[str, ...]:
        output = self._run(("diff", "--cached", "--name-only", "-z")).stdout
        return tuple(sorted(item.replace("\\", "/") for item in output.split("\0") if item))

    def commit(self, message: str) -> str:
        self._run(("commit", "-m", message))
        return self.head()

    def list_tree(self, ref: str, prefix: str) -> tuple[str, ...]:
        resolved = self.resolve_ref(ref)
        safe_prefix = relative_path(prefix, "prefix")
        output = self._run(("ls-tree", "-r", "--name-only", "-z", resolved, "--", safe_prefix)).stdout
        return tuple(sorted(item.replace("\\", "/") for item in output.split("\0") if item))

    def read_tree_file(self, ref: str, path: str) -> bytes:
        resolved = self.resolve_ref(ref)
        safe_path = relative_path(path, "path")
        result = self._run(("show", f"{resolved}:{safe_path}"), text=False)
        return bytes(result.stdout)


def validate_git_ref(ref: str) -> str:
    if not isinstance(ref, str) or not SAFE_REF.fullmatch(ref) or ".." in ref or ref.endswith("/"):
        raise DevWeaveError(ErrorCode.INVALID_VALUE, "Git ref is not allowed.", {"ref": str(ref)[:128]})
    return ref


def branch_name(run_id: str, slug: str) -> str:
    safe_run = re.sub(r"[^a-z0-9-]+", "-", run_id.lower()).strip("-")[:80]
    safe_slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")[:48]
    if not safe_run or not safe_slug:
        raise DevWeaveError(ErrorCode.INVALID_VALUE, "Run id and slug must produce a non-empty branch name.")
    return f"devweave/{safe_run}-{safe_slug}"


def path_matches(path: str, declarations: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    for declaration in declarations:
        pattern = declaration.replace("\\", "/")
        if pattern.endswith("/**") and (normalized == pattern[:-3] or normalized.startswith(pattern[:-2])):
            return True
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False

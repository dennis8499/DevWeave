"""Controlled verification planner, executor, and evidence derivation."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .canonical import sha256
from .errors import DevWeaveError, ErrorCode
from .fingerprints import changed_paths as compare_paths
from .fingerprints import file_digest, snapshot_digest, snapshot_tree
from .git_port import path_matches
from .project_config import ProjectConfig
from .redaction import bounded_text
from .verification_contracts import RiskLevel, VerificationCommand
from .version import SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class ResolvedExecutable:
    executable_id: str
    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class ProcessResult:
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    duration_ms: int
    timed_out: bool


class ProcessPort(Protocol):
    def run(self, argv: Sequence[str], *, cwd: Path, timeout_seconds: int) -> ProcessResult: ...


class SubprocessRunner:
    """Executes an argument vector directly; no shell command string exists."""

    def run(self, argv: Sequence[str], *, cwd: Path, timeout_seconds: int) -> ProcessResult:
        started = time.monotonic()
        environment = {
            key: value for key, value in os.environ.items()
            if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC"}
        }
        try:
            result = subprocess.run(
                list(argv), cwd=cwd, timeout=timeout_seconds, capture_output=True,
                shell=False, env=environment, check=False,
            )
            return ProcessResult(result.returncode, result.stdout, result.stderr, int((time.monotonic() - started) * 1000), False)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, bytes) else (exc.stdout or "").encode("utf-8")
            stderr = exc.stderr if isinstance(exc.stderr, bytes) else (exc.stderr or "").encode("utf-8")
            return ProcessResult(None, stdout, stderr, int((time.monotonic() - started) * 1000), True)
        except OSError as exc:
            return ProcessResult(None, b"", str(exc).encode("utf-8", errors="replace"), int((time.monotonic() - started) * 1000), False)


class ExecutableResolver:
    def __init__(self, overrides: Mapping[str, Path] | None = None) -> None:
        self.overrides = {key: value.resolve() for key, value in (overrides or {}).items()}

    def resolve(self, executable_id: str, candidates: Sequence[str]) -> ResolvedExecutable:
        path = self.overrides.get(executable_id)
        if path is None:
            discovered = next((shutil.which(candidate) for candidate in candidates if shutil.which(candidate)), None)
            path = Path(discovered).resolve() if discovered else None
        if path is None or not path.is_absolute() or not path.is_file():
            raise DevWeaveError(ErrorCode.COMMAND_FAILED, "Verification executable is unavailable.", {"executable_id": executable_id})
        return ResolvedExecutable(executable_id, path, file_digest(path))


@dataclass(frozen=True, slots=True)
class VerificationSelection:
    selected: tuple[str, ...]
    skipped: tuple[str, ...]
    closure_added: tuple[str, ...]
    stages: tuple[tuple[str, ...], ...]


class VerificationEngine:
    def __init__(
        self,
        repository: Path,
        config: ProjectConfig,
        *,
        resolver: ExecutableResolver | None = None,
        runner: ProcessPort | None = None,
        diagnostic_limit_bytes: int = 65_536,
    ) -> None:
        self.repository = repository.resolve()
        self.config = config
        self.resolver = resolver or ExecutableResolver()
        self.runner = runner or SubprocessRunner()
        self.diagnostic_limit_bytes = diagnostic_limit_bytes

    def plan(
        self,
        *,
        profile: RiskLevel,
        changed_paths: Sequence[str] = (),
        release: bool = False,
    ) -> VerificationSelection:
        commands = {item.command_id: item for item in self.config.verification_plan.commands}
        candidates = {
            item.command_id for item in commands.values()
            if profile in item.risk_profiles and (release or not item.release_only)
        }
        if changed_paths:
            direct = {
                command_id for command_id in candidates
                if not commands[command_id].affected_paths
                or any(path_matches(path, commands[command_id].affected_paths) for path in changed_paths)
            }
        else:
            direct = set(candidates)
        selected = set(direct)
        pending = list(sorted(direct))
        while pending:
            current = pending.pop()
            for dependency in commands[current].dependencies:
                if dependency not in selected:
                    selected.add(dependency)
                    pending.append(dependency)
        closure = selected - direct
        skipped = set(commands) - selected
        stages = _execution_stages(commands, selected)
        order = tuple(item for stage in stages for item in stage)
        return VerificationSelection(order, tuple(sorted(skipped)), tuple(sorted(closure)), stages)

    def run(
        self,
        *,
        profile: RiskLevel,
        plan_digest: str,
        changed_paths: Sequence[str] = (),
        release: bool = False,
    ) -> dict[str, Any]:
        selection = self.plan(profile=profile, changed_paths=changed_paths, release=release)
        commands = {item.command_id: item for item in self.config.verification_plan.commands}
        evidence: dict[str, dict[str, Any]] = {}
        for stage in selection.stages:
            runnable: list[VerificationCommand] = []
            for command_id in stage:
                command = commands[command_id]
                failed = [dependency for dependency in command.dependencies if not evidence.get(dependency, {}).get("gate_eligible", False)]
                if failed:
                    evidence[command_id] = self._skipped_evidence(command, plan_digest, failed)
                else:
                    runnable.append(command)
            readers = [item for item in runnable if item.writes == "none"]
            writers = [item for item in runnable if item.writes != "none"]
            if readers:
                with ThreadPoolExecutor(max_workers=min(4, len(readers)), thread_name_prefix="devweave-verify") as pool:
                    futures = {item.command_id: pool.submit(self._execute, item, plan_digest) for item in readers}
                    for command_id in sorted(futures):
                        evidence[command_id] = futures[command_id].result()
            for writer in writers:
                evidence[writer.command_id] = self._execute(writer, plan_digest)
        ordered = [evidence[command_id] for command_id in selection.selected]
        current = all(item["gate_eligible"] for item in ordered) and bool(ordered)
        return {
            "schema_version": SCHEMA_VERSION,
            "plan_id": self.config.verification_plan.plan_id,
            "plan_digest": plan_digest,
            "profile": profile.value,
            "selection": {
                "selected": list(selection.selected),
                "skipped": list(selection.skipped),
                "closure_added": list(selection.closure_added),
                "stages": [list(stage) for stage in selection.stages],
            },
            "evidence": ordered,
            "gate_eligible": current,
            "usage": {"available": False, "input_tokens": None, "output_tokens": None, "total_tokens": None},
        }

    def _execute(self, command: VerificationCommand, plan_digest: str) -> dict[str, Any]:
        executable = self.resolver.resolve(command.argv[0], self.config.candidates_for(command.argv[0]))
        cwd = (self.repository / command.cwd).resolve()
        try:
            cwd.relative_to(self.repository)
        except ValueError as exc:
            raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "Verification cwd escapes repository.") from exc
        if not cwd.is_dir():
            raise DevWeaveError(ErrorCode.NOT_FOUND, "Verification cwd is not a directory.")
        before = snapshot_tree(self.repository)
        input_digest = snapshot_digest(before)
        result = self.runner.run((str(executable.path), *command.argv[1:]), cwd=cwd, timeout_seconds=command.timeout_seconds)
        after = snapshot_tree(self.repository)
        output_digest = snapshot_digest(after)
        effects = compare_paths(before, after)
        undeclared = list(effects) if command.writes == "none" else [path for path in effects if not path_matches(path, command.outputs)]
        expected_exit = result.exit_code in command.expected_exit_codes if result.exit_code is not None else False
        status = "passed" if expected_exit and not result.timed_out and not undeclared else "failed"
        stdout, stdout_truncated = bounded_text(result.stdout, max_bytes=self.diagnostic_limit_bytes)
        stderr, stderr_truncated = bounded_text(result.stderr, max_bytes=self.diagnostic_limit_bytes)
        identity = sha256({
            "command_id": command.command_id,
            "definition_digest": command.definition_digest,
            "plan_digest": plan_digest,
            "input_digest": input_digest,
            "output_digest": output_digest,
        })[:20]
        return {
            "schema_version": SCHEMA_VERSION,
            "evidence_id": f"VER-{identity}",
            "command_id": command.command_id,
            "status": status,
            "definition_digest": command.definition_digest,
            "plan_digest": plan_digest,
            "input_digest": input_digest,
            "output_digest": output_digest,
            "executable": {"id": executable.executable_id, "path": str(executable.path), "sha256": executable.sha256},
            "exit_code": result.exit_code,
            "expected_exit_codes": list(command.expected_exit_codes),
            "timed_out": result.timed_out,
            "duration_ms": max(0, result.duration_ms),
            "changed_paths": list(effects),
            "undeclared_paths": undeclared,
            "stdout": stdout,
            "stderr": stderr,
            "diagnostic_truncated": stdout_truncated or stderr_truncated,
            "gate_eligible": status == "passed",
            "usage": {"available": False, "input_tokens": None, "output_tokens": None, "total_tokens": None},
        }

    def _skipped_evidence(self, command: VerificationCommand, plan_digest: str, failed: list[str]) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "evidence_id": f"VER-{sha256({'command': command.command_id, 'plan': plan_digest, 'failed': failed})[:20]}",
            "command_id": command.command_id,
            "status": "skipped_dependency",
            "definition_digest": command.definition_digest,
            "plan_digest": plan_digest,
            "failed_dependencies": failed,
            "gate_eligible": False,
            "usage": {"available": False, "input_tokens": None, "output_tokens": None, "total_tokens": None},
        }


def evidence_is_current(
    evidence: Mapping[str, Any], *, source_digest: str, plan_digest: str, definition_digest: str
) -> bool:
    bound_source = evidence.get("output_digest")
    return bool(
        evidence.get("gate_eligible")
        and bound_source == source_digest
        and evidence.get("plan_digest") == plan_digest
        and evidence.get("definition_digest") == definition_digest
    )


def _execution_stages(
    commands: Mapping[str, VerificationCommand], selected: set[str]
) -> tuple[tuple[str, ...], ...]:
    remaining = set(selected)
    completed: set[str] = set()
    stages: list[tuple[str, ...]] = []
    while remaining:
        ready = sorted(command_id for command_id in remaining if set(commands[command_id].dependencies) <= completed)
        if not ready:
            raise DevWeaveError(ErrorCode.INVALID_VALUE, "Verification graph cannot be scheduled.")
        readers = tuple(command_id for command_id in ready if commands[command_id].writes == "none")
        if readers:
            stages.append(readers)
            remaining.difference_update(readers)
            completed.update(readers)
        for writer in (command_id for command_id in ready if commands[command_id].writes != "none"):
            stages.append((writer,))
            remaining.remove(writer)
            completed.add(writer)
    return tuple(stages)

from __future__ import annotations

import fnmatch
import getpass
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

import knowledge_core as knowledge


SCHEMA_VERSION = 1
KINDS = ("new", "feature", "refactor", "bug")
RISK_LEVELS = ("low", "standard", "high")
COMMAND_WRITES = ("none", "generated", "tracked-artifact")
COMMAND_METADATA_FIELDS = ("affected_paths", "writes", "outputs", "release_only")
GATES = ("scope", "build", "acceptance")
PHASES = (
    "requirements",
    "scope_review",
    "design",
    "build_review",
    "implementation",
    "verification",
    "acceptance_review",
    "closed",
)
RISK_RANK = {"low": 0, "standard": 1, "high": 2}
WAIVER_GATES = {
    "unreproducible": "scope",
    "missing-command": "acceptance",
    "out-of-scope": "acceptance",
    "review-critical": "acceptance",
}
PHASE_REFERENCES = {
    "requirements": "references/requirements-phase.md",
    "scope_review": "references/requirements-phase.md",
    "design": "references/design-phase.md",
    "build_review": "references/design-phase.md",
    "implementation": "references/implementation-phase.md",
    "verification": "references/verification-phase.md",
    "acceptance_review": "references/verification-phase.md",
    "closed": "references/contracts.md",
}
ARTIFACT_NAMES = (
    "brief.md",
    "requirements.md",
    "design.md",
    "plan.md",
    "acceptance.md",
)
KNOWLEDGE_CONTENT_TYPES = tuple(sorted(knowledge.PAGE_TYPES - {"index", "log"}))
FRAMEWORK_PREFIXES = (
    ".devweave/",
    ".agents/skills/devweave/",
    ".codex/",
)
MAX_RAW_LOG_BYTES = 5_000_000
MAX_METRIC_COUNT = 10_000_000
MAX_METRIC_BYTES = 250_000
REVIEW_RESULTS = ("passed", "unavailable", "critical")
REVIEW_SEVERITIES = ("none", "advisory", "critical")
REVIEW_CONTEXT_MODE = "isolated_read_only"
REVIEW_MAX_TEXT_CHARS = 20_000
REVIEW_MAX_FINDINGS = 100
ID_PATTERN = re.compile(r"\b(REQ|NFR|AC|DEC|TASK|EVID)-\d{3}\b")
WORK_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
HEADING_PATTERN = re.compile(
    r"^##\s+((?:REQ|NFR|AC|DEC|TASK)-\d{3})\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)
TODO_PATTERN = re.compile(r"(?:<!--\s*TODO|\[TODO\]|TODO:)", re.IGNORECASE)
DEPENDENCIES_PATTERN = re.compile(r"^-\s*Dependencies:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)


class DevWeaveError(Exception):
    exit_code = 2
    error_code = "devweave_error"

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(DevWeaveError):
    exit_code = 2
    error_code = "validation_failed"


class SelectionError(DevWeaveError):
    exit_code = 3
    error_code = "selection_required"


class ExecutionError(DevWeaveError):
    exit_code = 4
    error_code = "execution_failed"


@dataclass
class ValidationReport:
    gate: str | None
    errors: list[str]
    warnings: list[str]
    trace: dict[str, list[str]]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "gate": self.gate,
            "errors": self.errors,
            "warnings": self.warnings,
            "trace": self.trace,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _bounded_nonnegative_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(
            "Evidence metric must be a non-negative integer.",
            {"metric": label, "value": value},
        )
    if value > MAX_METRIC_COUNT:
        raise ValidationError(
            "Evidence metric exceeds the bounded maximum.",
            {"metric": label, "maximum": MAX_METRIC_COUNT},
        )
    return value


def normalize_evidence_metrics(metrics: Any | None) -> dict[str, Any] | None:
    if metrics is None:
        return None
    if not isinstance(metrics, dict):
        raise ValidationError("Evidence metrics must be an object.")
    allowed = {"context", "tools", "verification", "usage", "duration_ms"}
    unknown = sorted(set(metrics) - allowed)
    if unknown:
        raise ValidationError(
            "Evidence metrics contain unsupported fields.",
            {"fields": unknown},
        )
    normalized: dict[str, Any] = {}
    if "duration_ms" in metrics:
        normalized["duration_ms"] = _bounded_nonnegative_int(
            metrics["duration_ms"], label="duration_ms"
        )
    context = metrics.get("context")
    if context is not None:
        if not isinstance(context, dict):
            raise ValidationError("Evidence metrics.context must be an object.")
        unknown = sorted(set(context) - {"pages", "bytes", "chars"})
        if unknown:
            raise ValidationError("Evidence metrics.context contains unsupported fields.", {"fields": unknown})
        normalized["context"] = {
            key: _bounded_nonnegative_int(context[key], label=f"context.{key}")
            for key in ("pages", "bytes", "chars")
            if key in context
        }
    tools = metrics.get("tools")
    if tools is not None:
        if not isinstance(tools, dict):
            raise ValidationError("Evidence metrics.tools must be an object.")
        unknown = sorted(set(tools) - {"read", "search", "write", "test"})
        if unknown:
            raise ValidationError("Evidence metrics.tools contains unsupported fields.", {"fields": unknown})
        normalized["tools"] = {
            key: _bounded_nonnegative_int(tools[key], label=f"tools.{key}")
            for key in ("read", "search", "write", "test")
            if key in tools
        }
    verification = metrics.get("verification")
    if verification is not None:
        if not isinstance(verification, dict):
            raise ValidationError("Evidence metrics.verification must be an object.")
        item: dict[str, Any] = {}
        for key in ("selected", "skipped", "dependency_closure_added"):
            if key in verification:
                item[key] = _bounded_nonnegative_int(
                    verification[key], label=f"verification.{key}"
                )
        if "cache_hit" in verification:
            if not isinstance(verification["cache_hit"], bool):
                raise ValidationError("Evidence metrics.verification.cache_hit must be boolean.")
            item["cache_hit"] = verification["cache_hit"]
        unknown = sorted(set(verification) - {"selected", "skipped", "dependency_closure_added", "cache_hit"})
        if unknown:
            raise ValidationError("Evidence metrics.verification contains unsupported fields.", {"fields": unknown})
        normalized["verification"] = item
    usage = metrics.get("usage")
    if usage is not None:
        if not isinstance(usage, dict):
            raise ValidationError("Evidence metrics.usage must be an object.")
        unknown = sorted(set(usage) - {"status", "input_tokens", "output_tokens", "cached_tokens", "cost"})
        if unknown:
            raise ValidationError("Evidence metrics.usage contains unsupported fields.", {"fields": unknown})
        status = usage.get("status", "unavailable")
        if status not in ("available", "unavailable"):
            raise ValidationError("Evidence metrics.usage.status is invalid.")
        item = {"status": status}
        if status == "available":
            for key in ("input_tokens", "output_tokens", "cached_tokens"):
                if key in usage:
                    item[key] = _bounded_nonnegative_int(usage[key], label=f"usage.{key}")
            if "cost" in usage:
                cost = usage["cost"]
                if (
                    isinstance(cost, bool)
                    or not isinstance(cost, (int, float))
                    or not math.isfinite(float(cost))
                    or cost < 0
                ):
                    raise ValidationError("Evidence metrics.usage.cost must be non-negative.")
                item["cost"] = float(cost)
        else:
            item.update({"input_tokens": None, "output_tokens": None, "cached_tokens": None, "cost": None})
        normalized["usage"] = item
    encoded = canonical_json(normalized)
    if len(encoded) > MAX_METRIC_BYTES:
        raise ValidationError(
            "Evidence metrics exceed the bounded payload size.",
            {"maximum_bytes": MAX_METRIC_BYTES},
        )
    return normalized


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_relpath(path: str | Path) -> str:
    normalized = Path(path).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def is_framework_path(path: str, knowledge_root: str = "wiki") -> bool:
    normalized = normalize_relpath(path)
    prefixes = (*FRAMEWORK_PREFIXES, knowledge.normalize_root(knowledge_root) + "/")
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in prefixes)


def path_matches_scope(path: str, patterns: Sequence[str]) -> bool:
    normalized = normalize_relpath(path)
    for raw_pattern in patterns:
        pattern = normalize_relpath(raw_pattern).rstrip("/")
        if pattern in ("", ".", "*", "**"):
            return True
        if (
            fnmatch.fnmatch(normalized, pattern)
            or normalized == pattern
            or normalized.startswith(pattern + "/")
        ):
            return True
    return False


def _normalize_command_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("path must not be empty")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:($|/)", normalized):
        raise ValueError("path must be repository-relative")
    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        raise ValueError("path must not contain '..'")
    return normalized


def _command_metadata_errors(
    command: dict[str, Any], *, label: str = "command"
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    normalized: dict[str, Any] = {}
    for field in ("affected_paths", "outputs"):
        if field not in command:
            continue
        values = command.get(field)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            errors.append(f"{label}.{field} must be a string array")
            continue
        converted: list[str] = []
        for item in values:
            try:
                converted.append(_normalize_command_path(item))
            except ValueError as exc:
                errors.append(f"{label}.{field} contains invalid path: {item!r} ({exc})")
        if len(converted) != len(set(converted)):
            errors.append(f"{label}.{field} must not contain duplicate paths")
        normalized[field] = converted
    if "writes" in command:
        writes = command.get("writes")
        if not isinstance(writes, str) or writes not in COMMAND_WRITES:
            errors.append(
                f"{label}.writes must be one of: {', '.join(COMMAND_WRITES)}"
            )
        else:
            normalized["writes"] = writes
    if "release_only" in command:
        release_only = command.get("release_only")
        if not isinstance(release_only, bool):
            errors.append(f"{label}.release_only must be a boolean")
        else:
            normalized["release_only"] = release_only
    return errors, normalized


def _command_metadata_present(command: dict[str, Any]) -> bool:
    return any(field in command for field in COMMAND_METADATA_FIELDS)


def normalize_command_metadata(
    command: dict[str, Any], *, label: str = "command"
) -> dict[str, Any]:
    errors, normalized = _command_metadata_errors(command, label=label)
    if errors:
        raise ValidationError("Invalid verification command metadata.", {"errors": errors})
    return normalized


def _command_path_patterns(command: dict[str, Any]) -> list[str]:
    return [
        *command.get("affected_paths", []),
        *command.get("outputs", []),
    ]


def _command_path_intersects(changed: str, pattern: str) -> bool:
    changed_normalized = normalize_relpath(changed).replace("\\", "/")
    pattern_normalized = pattern.replace("\\", "/")
    if path_matches_scope(changed_normalized, [pattern_normalized]):
        return True
    if pattern_normalized.endswith("/**") and path_matches_scope(
        changed_normalized, [pattern_normalized[:-3]]
    ):
        return True
    # A caller may provide a directory or glob while command metadata names a
    # concrete output. Checking both directions keeps directory-level impact
    # selection conservative without treating unrelated siblings as affected.
    return path_matches_scope(pattern_normalized, [changed_normalized])


def _command_matches_paths(command: dict[str, Any], paths: Sequence[str]) -> bool:
    patterns = _command_path_patterns(command)
    return bool(patterns) and any(
        _command_path_intersects(path, pattern)
        for path in paths
        for pattern in patterns
    )


def _normalize_verification_paths(paths: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for path in paths:
        try:
            normalized.append(_normalize_command_path(path))
        except ValueError as exc:
            raise ValidationError(
                "Verification --path values must be repository-relative paths or globs.",
                {"path": path, "reason": str(exc)},
            ) from exc
    if len(normalized) != len(set(normalized)):
        raise ValidationError(
            "Verification --path values must not contain duplicates.",
            {"paths": normalized},
        )
    return normalized


def ensure_within(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValidationError(
            f"Path escapes repository root: {candidate}",
            {"root": str(resolved_root), "path": str(resolved)},
        ) from exc
    return resolved


def find_repo_root(start: str | Path | None = None) -> Path:
    cwd = Path(start or os.getcwd()).resolve()
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    current = cwd
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise ValidationError("DevWeave requires a Git repository.", {"cwd": str(cwd)})


def devweave_root(repo: Path) -> Path:
    return repo / ".devweave"


def project_path(repo: Path) -> Path:
    return devweave_root(repo) / "project.json"


def work_items_root(repo: Path) -> Path:
    return devweave_root(repo) / "work-items"


def work_root(repo: Path, work_id: str) -> Path:
    if not WORK_ID_PATTERN.fullmatch(work_id) or work_id in (".", ".."):
        raise ValidationError("Invalid work-item ID.", {"work": work_id})
    return work_items_root(repo) / work_id


def state_path(repo: Path, work_id: str) -> Path:
    return work_root(repo, work_id) / "state.json"


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def assets_root() -> Path:
    return skill_root() / "assets"


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"Required JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"Invalid JSON: {path}",
            {"line": exc.lineno, "column": exc.colno, "message": exc.msg},
        ) from exc


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_write_text(path, payload)


class WorkLock:
    def __init__(self, repo: Path, name: str, timeout_seconds: float = 10.0):
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
        self.path = devweave_root(repo) / "cache" / "locks" / f"{safe_name}.lock"
        self.timeout_seconds = timeout_seconds

    def __enter__(self) -> "WorkLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self.path.mkdir()
                atomic_write_json(
                    self.path / "owner.json",
                    {"pid": os.getpid(), "created_at": utc_now()},
                )
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > 120:
                        owner = self.path / "owner.json"
                        if owner.exists():
                            owner.unlink()
                        self.path.rmdir()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise ExecutionError(
                        f"Timed out waiting for DevWeave lock: {self.path.name}"
                    )
                time.sleep(0.05)

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        owner = self.path / "owner.json"
        try:
            if owner.exists():
                owner.unlink()
            self.path.rmdir()
        except FileNotFoundError:
            return


def append_event_unlocked(repo: Path, work_id: str, event: str, data: dict[str, Any] | None = None) -> None:
    path = work_root(repo, work_id) / "events.jsonl"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "at": utc_now(),
        "event": event,
        "data": data or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def save_state_unlocked(repo: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    atomic_write_json(state_path(repo, state["id"]), state)


def load_project(repo: Path) -> dict[str, Any]:
    project = read_json(project_path(repo))
    if project.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(
            "Unsupported DevWeave project schema.",
            {"expected": SCHEMA_VERSION, "actual": project.get("schema_version")},
        )
    errors: list[str] = []
    if not isinstance(project.get("managed"), bool):
        errors.append("managed must be a boolean")
    if not isinstance(project.get("locale"), str) or not project.get("locale"):
        errors.append("locale must be a non-empty string")
    commands = project.get("commands")
    if not isinstance(commands, list):
        errors.append("commands must be an array")
        commands = []
    command_ids: list[str] = []
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            errors.append(f"commands[{index}] must be an object")
            continue
        command_id = command.get("id")
        if not isinstance(command_id, str) or not re.fullmatch(
            r"[A-Za-z0-9._-]+", command_id
        ):
            errors.append(f"commands[{index}].id is invalid")
        else:
            command_ids.append(command_id)
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(
            isinstance(item, str) and item for item in argv
        ):
            errors.append(f"commands[{index}].argv must be a non-empty string array")
        if not isinstance(command.get("cwd"), str) or not command.get("cwd"):
            errors.append(f"commands[{index}].cwd must be a non-empty string")
        timeout = command.get("timeout_seconds")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            errors.append(f"commands[{index}].timeout_seconds must be a positive integer")
        required_for = command.get("required_for")
        if (
            not isinstance(required_for, list)
            or not all(isinstance(item, str) for item in required_for)
            or not set(required_for).issubset(set(RISK_LEVELS))
        ):
            errors.append(f"commands[{index}].required_for contains invalid risk levels")
        depends_on = command.get("depends_on", [])
        if (
            not isinstance(depends_on, list)
            or not all(
                isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9._-]+", item)
                for item in depends_on
            )
        ):
            errors.append(f"commands[{index}].depends_on contains invalid command IDs")
        exclusive_group = command.get("exclusive_group", "")
        if not isinstance(exclusive_group, str):
            errors.append(f"commands[{index}].exclusive_group must be a string")
        metadata_errors, _ = _command_metadata_errors(
            command, label=f"commands[{index}]"
        )
        errors.extend(metadata_errors)
    if len(command_ids) != len(set(command_ids)):
        errors.append("command IDs must be unique")
    known_command_ids = set(command_ids)
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            continue
        command_id = command.get("id")
        for dependency in command.get("depends_on", []):
            if dependency not in known_command_ids:
                errors.append(
                    f"commands[{index}].depends_on references an undefined command: {dependency}"
                )
            if dependency == command_id:
                errors.append(f"commands[{index}].depends_on cannot reference itself")
    profiles = project.get("verification_profiles")
    if not isinstance(profiles, dict):
        errors.append("verification_profiles must be an object")
    else:
        for level in RISK_LEVELS:
            profile = profiles.get(level)
            if not isinstance(profile, list) or not all(
                isinstance(item, str) and item for item in profile
            ):
                errors.append(f"verification_profiles.{level} must be a string array")
    evidence_policy = project.get("evidence")
    raw_limit = (
        evidence_policy.get("raw_log_limit_bytes")
        if isinstance(evidence_policy, dict)
        else None
    )
    if (
        not isinstance(evidence_policy, dict)
        or isinstance(raw_limit, bool)
        or not isinstance(raw_limit, int)
        or raw_limit <= 0
    ):
        errors.append("evidence.raw_log_limit_bytes must be a positive integer")
    knowledge_policy = project.get("knowledge")
    if knowledge_policy is None:
        knowledge_policy = {"enabled": True, "root": "wiki"}
        project["knowledge"] = knowledge_policy
    if (
        not isinstance(knowledge_policy, dict)
        or knowledge_policy.get("enabled") is not True
        or not isinstance(knowledge_policy.get("root"), str)
    ):
        errors.append("knowledge must enable one repo-relative root")
    else:
        try:
            knowledge_policy["root"] = knowledge.normalize_root(knowledge_policy["root"])
            if knowledge_policy["root"] != "wiki":
                errors.append("knowledge.root must be wiki")
        except knowledge.KnowledgeError as exc:
            errors.append(exc.message)
    if errors:
        raise ValidationError(
            "Invalid DevWeave project model.",
            {"path": str(project_path(repo)), "errors": errors},
        )
    return project


def project_defaults() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "managed": True,
        "locale": "zh-TW",
        "commands": [],
        "verification_profiles": {
            "low": [],
            "standard": [],
            "high": [],
        },
        "protected_mutations": [
            "product-code",
            "tests",
            "schema",
            "dependencies",
            "build",
            "ci",
        ],
        "evidence": {
            "raw_log_limit_bytes": MAX_RAW_LOG_BYTES,
            "version_summaries": True,
        },
        "knowledge": {
            "enabled": True,
            "root": "wiki",
        },
    }


def knowledge_root(repo: Path) -> str:
    if not project_path(repo).exists():
        return "wiki"
    try:
        raw = read_json(project_path(repo)).get("knowledge", {})
        return knowledge.normalize_root(str(raw.get("root", "wiki")))
    except (DevWeaveError, knowledge.KnowledgeError):
        return "wiki"


def _ensure_gitignore(repo: Path) -> None:
    path = repo / ".gitignore"
    required = (".devweave/cache/",)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = {line.strip() for line in current.splitlines()}
    additions = [entry for entry in required if entry not in lines]
    if not additions:
        return
    prefix = "" if not current or current.endswith("\n") else "\n"
    atomic_write_text(path, current + prefix + "\n".join(additions) + "\n")


def _render_asset(name: str, values: dict[str, str]) -> str:
    path = assets_root() / name
    try:
        template = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ExecutionError(f"Bundled DevWeave asset is missing: {name}") from exc
    return template.format_map(values)


def baseline_snapshot(repo: Path) -> dict[str, Any]:
    root = devweave_root(repo) / "baseline"
    files: dict[str, str] = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            safe_path = ensure_within(root, path)
            relative = normalize_relpath(safe_path.relative_to(repo))
            files[relative] = sha256_bytes(safe_path.read_bytes())
    return {"files": files, "fingerprint": sha256_bytes(canonical_json(files))}


def init_project(repo: Path) -> dict[str, Any]:
    if sys.version_info < (3, 11):
        raise ValidationError(
            "DevWeave requires Python 3.11 or newer.",
            {"current": list(sys.version_info[:3])},
        )
    root = devweave_root(repo)
    root_existed = root.exists()
    cache_existed = (root / "cache").exists()
    locks_existed = (root / "cache" / "locks").exists()

    def validate_wiki_preflight() -> None:
        inspection = knowledge.inspect_wiki(repo, root=knowledge_root(repo))
        if not inspection["compatible"]:
            raise ValidationError(
                "Existing Wiki content is not compatible and was not modified.",
                {"code": "knowledge_conflict", "details": {"conflicts": inspection["conflicts"]}},
            )

    validate_wiki_preflight()
    try:
        with WorkLock(repo, "project"):
            validate_wiki_preflight()
            existing = read_json(project_path(repo)) if project_path(repo).exists() else None
            locale = (
                existing.get("locale", "zh-TW")
                if isinstance(existing, dict)
                else "zh-TW"
            )
            if not isinstance(locale, str) or not locale:
                locale = "zh-TW"
            try:
                knowledge.bootstrap_wiki(
                    repo,
                    assets_root(),
                    root=knowledge_root(repo),
                    locale=locale,
                )
            except knowledge.KnowledgeError as exc:
                raise ValidationError(exc.message, {"code": exc.code, "details": exc.details}) from exc

            root.mkdir(parents=True, exist_ok=True)
            (root / "cache" / "sessions").mkdir(parents=True, exist_ok=True)
            (root / "work-items").mkdir(parents=True, exist_ok=True)
            (root / "baseline" / "capabilities").mkdir(parents=True, exist_ok=True)
            if existing is None:
                atomic_write_json(project_path(repo), project_defaults())
            elif "knowledge" not in existing:
                existing["knowledge"] = {"enabled": True, "root": "wiki"}
                atomic_write_json(project_path(repo), existing)
            for target, asset in (
                ("product.md", "baseline-product.md.tmpl"),
                ("architecture.md", "baseline-architecture.md.tmpl"),
                ("quality.md", "baseline-quality.md.tmpl"),
            ):
                output = root / "baseline" / target
                if not output.exists():
                    atomic_write_text(output, _render_asset(asset, {}))
            load_project(repo)
            _ensure_gitignore(repo)
    except ValidationError:
        for candidate, existed in (
            (root / "cache" / "locks", locks_existed),
            (root / "cache", cache_existed),
            (root, root_existed),
        ):
            if not existed and candidate.is_dir():
                try:
                    candidate.rmdir()
                except OSError:
                    pass
        raise
    return load_project(repo)


def _project_requires_bootstrap(repo: Path) -> bool:
    if not project_path(repo).exists():
        return True
    raw = read_json(project_path(repo))
    if "knowledge" not in raw:
        return True
    project = load_project(repo)
    required = [
        devweave_root(repo) / "cache" / "sessions",
        devweave_root(repo) / "work-items",
        devweave_root(repo) / "baseline" / "capabilities",
        *(devweave_root(repo) / "baseline" / name for name in ("product.md", "architecture.md", "quality.md")),
    ]
    root = project["knowledge"]["root"]
    wiki = repo / root
    required.extend(wiki / name for name in knowledge.STARTER_FILES)
    required.extend(wiki / name for name in knowledge.TYPE_DIRECTORIES.values())
    if any(not path.exists() for path in required):
        return True
    try:
        return not knowledge.inspect_wiki(repo, root=root)["compatible"]
    except knowledge.KnowledgeError:
        return True


def _git(repo: Path, args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise ExecutionError(
            f"Git command failed: git {' '.join(args)}",
            {
                "returncode": result.returncode,
                "stderr": result.stderr.decode("utf-8", errors="replace"),
            },
        )
    return result


def _zpaths(raw: bytes) -> list[str]:
    return [
        normalize_relpath(item.decode("utf-8", errors="surrogateescape"))
        for item in raw.split(b"\0")
        if item
    ]


def git_snapshot(repo: Path) -> dict[str, Any]:
    head_result = _git(repo, ["rev-parse", "HEAD"], check=False)
    head = (
        head_result.stdout.decode("ascii", errors="replace").strip()
        if head_result.returncode == 0
        else "UNBORN"
    )
    branch_result = _git(repo, ["branch", "--show-current"], check=False)
    branch = branch_result.stdout.decode("utf-8", errors="replace").strip() or "DETACHED"
    paths: set[str] = set()
    for args in (
        ["diff", "--name-only", "-z"],
        ["diff", "--cached", "--name-only", "-z"],
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ):
        paths.update(_zpaths(_git(repo, args).stdout))
    wiki_root = knowledge_root(repo)
    filtered = sorted(path for path in paths if not is_framework_path(path, wiki_root))
    files: dict[str, str] = {}
    for relative in filtered:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ExecutionError(
                "Git reported a path outside the repository.", {"path": relative}
            )
        candidate = repo / relative_path
        combined_diff = _git(
            repo, ["diff", "HEAD", "--binary", "--", relative], check=False
        )
        if combined_diff.returncode == 0:
            diff_material = combined_diff.stdout
        else:
            unstaged = _git(
                repo, ["diff", "--binary", "--", relative], check=False
            ).stdout
            staged = _git(
                repo, ["diff", "--cached", "--binary", "--", relative], check=False
            ).stdout
            diff_material = staged + b"\0" + unstaged
        if candidate.is_symlink():
            content_hash = sha256_bytes(
                ("symlink:" + os.readlink(candidate)).encode("utf-8", errors="surrogateescape")
            )
        else:
            safe_candidate = ensure_within(repo, candidate)
            content_hash = (
                sha256_bytes(safe_candidate.read_bytes())
                if safe_candidate.is_file()
                else "<missing>"
            )
        path_material = canonical_json(
            {
                "content": content_hash,
                "diff": sha256_bytes(diff_material),
            }
        )
        files[relative] = sha256_bytes(path_material)
    fingerprint = sha256_bytes(
        canonical_json({"head": head, "branch": branch, "files": files})
    )
    return {
        "head": head,
        "branch": branch,
        "dirty_paths": filtered,
        "files": files,
        "fingerprint": fingerprint,
    }


def changed_paths_since(repo: Path, base_snapshot: dict[str, Any]) -> list[str]:
    current = git_snapshot(repo)
    paths = {
        path
        for path in set(current.get("files", {})) | set(base_snapshot.get("files", {}))
        if current.get("files", {}).get(path) != base_snapshot.get("files", {}).get(path)
    }
    base_head = base_snapshot.get("head", "UNBORN")
    current_head = current.get("head", "UNBORN")
    if base_head != current_head:
        if base_head != "UNBORN":
            result = _git(
                repo,
                ["diff", "--name-only", "-z", f"{base_head}..{current_head}"],
                check=False,
            )
            if result.returncode == 0:
                paths.update(_zpaths(result.stdout))
        else:
            paths.update(_zpaths(_git(repo, ["ls-files", "-z"]).stdout))
    wiki_root = knowledge_root(repo)
    return sorted(path for path in paths if not is_framework_path(path, wiki_root))


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:40] or "work"


def _new_work_id(repo: Path, kind: str, title: str) -> str:
    prefix = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{prefix}-{kind}-{_slugify(title)}"
    candidate = base
    suffix = 2
    while work_root(repo, candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _empty_knowledge_updates() -> dict[str, Any]:
    return {
        "upserts": [],
        "deletes": [],
        "coupled": [],
        "rationale": "",
        "sealed": [],
        "change_fingerprint": None,
        "recorded_at": None,
    }


def create_work(
    repo: Path,
    kind: str,
    title: str,
    risk: str = "standard",
    risk_rationale: str = "",
    knowledge_profile: str | None = None,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValidationError("Unknown work kind.", {"kind": kind, "allowed": list(KINDS)})
    if risk not in RISK_LEVELS:
        raise ValidationError(
            "Unknown risk level.", {"risk": risk, "allowed": list(RISK_LEVELS)}
        )
    if not title.strip():
        raise ValidationError("Work title must not be empty.")
    if knowledge_profile not in (None, "bootstrap"):
        raise ValidationError(
            "Unknown knowledge profile.",
            {"profile": knowledge_profile, "allowed": ["bootstrap"]},
        )
    if _project_requires_bootstrap(repo):
        init_project(repo)
    project = load_project(repo)
    with WorkLock(repo, "project"):
        work_id = _new_work_id(repo, kind, title)
        root = work_root(repo, work_id)
        root.mkdir(parents=True)
        (root / "evidence").mkdir()
        values = {
            "work_id": work_id,
            "title": title.strip(),
            "kind": kind,
            "risk": risk,
        }
        for name in ARTIFACT_NAMES:
            atomic_write_text(root / name, _render_asset(f"{name}.tmpl", values))
        base = git_snapshot(repo)
        base_baseline = baseline_snapshot(repo)
        base_knowledge = knowledge.knowledge_snapshot(
            repo, root=project["knowledge"]["root"]
        )
        state = {
            "schema_version": SCHEMA_VERSION,
            "id": work_id,
            "kind": kind,
            "title": title.strip(),
            "status": "active",
            "phase": "requirements",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "risk": {
                "level": risk,
                "rationale": risk_rationale.strip(),
                "downgrade_rationale": None,
            },
            "scope": {
                "paths": [],
                "rationale": "",
            },
            "base_source": base,
            "base_baseline": base_baseline,
            "base_knowledge": base_knowledge,
            "knowledge_review_required": True,
            "knowledge_context": {
                "pages": [],
                "records": [],
                "gaps": [],
                "recorded_at": None,
            },
            "knowledge_review": {
                "disposition": None,
                "rationale": "",
                "affected_pages": [],
                "covered_changed_paths": [],
                "uncovered_changed_paths": [],
                "change_fingerprint": None,
                "recorded_at": None,
                "invalidated_at": None,
            },
            "knowledge_updates": _empty_knowledge_updates(),
            "gates": {
                gate: {
                    "status": "pending",
                    "fingerprint": None,
                    "approved_by": None,
                    "approved_at": None,
                }
                for gate in GATES
            },
            "tasks": {},
            "evidence": {},
            "waivers": [],
            "baseline_updates": {
                "targets": [],
                "rationale": "",
                "recorded_at": None,
            },
            "last_verification": None,
            "blocker": None,
        }
        if knowledge_profile is not None:
            state["knowledge_profile"] = knowledge_profile
        atomic_write_json(root / "state.json", state)
        append_event_unlocked(repo, work_id, "work_started", {"kind": kind, "risk": risk})
    return state


def load_state(repo: Path, work_id: str) -> dict[str, Any]:
    state = read_json(state_path(repo, work_id))
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(
            "Unsupported work-item schema.",
            {
                "work": work_id,
                "expected": SCHEMA_VERSION,
                "actual": state.get("schema_version"),
            },
        )
    errors: list[str] = []
    if state.get("id") != work_id:
        errors.append("state id does not match its directory")
    if state.get("kind") not in KINDS:
        errors.append("kind is invalid")
    if state.get("status") not in ("active", "closed"):
        errors.append("status is invalid")
    if state.get("phase") not in PHASES:
        errors.append("phase is invalid")
    if "knowledge_profile" in state and state.get("knowledge_profile") != "bootstrap":
        errors.append("knowledge_profile is invalid")
    if "knowledge_review_required" in state and not isinstance(
        state.get("knowledge_review_required"), bool
    ):
        errors.append("knowledge_review_required must be a boolean")
    if state.get("knowledge_review_required") and "base_knowledge" not in state:
        errors.append("knowledge_review_required needs a base_knowledge snapshot")
    if state.get("knowledge_profile") == "bootstrap" and state.get(
        "knowledge_review_required"
    ) is not True:
        errors.append("bootstrap knowledge profile requires the new review contract")
    base_baseline = state.get("base_baseline")
    if (
        not isinstance(base_baseline, dict)
        or not isinstance(base_baseline.get("files"), dict)
        or not isinstance(base_baseline.get("fingerprint"), str)
    ):
        errors.append("base_baseline is invalid")
    if "base_knowledge" in state:
        base_knowledge = state.get("base_knowledge")
        if (
            not isinstance(base_knowledge, dict)
            or not isinstance(base_knowledge.get("files"), dict)
            or not isinstance(base_knowledge.get("pages"), dict)
            or not isinstance(base_knowledge.get("fingerprint"), str)
        ):
            errors.append("base_knowledge is invalid")
        context = state.get("knowledge_context")
        if (
            not isinstance(context, dict)
            or not isinstance(context.get("pages"), list)
            or not all(isinstance(item, str) for item in context.get("pages", []))
            or not isinstance(context.get("gaps"), list)
            or not all(isinstance(item, str) for item in context.get("gaps", []))
            or context.get("recorded_at") is not None
            and not isinstance(context.get("recorded_at"), str)
        ):
            errors.append("knowledge_context is invalid")
        elif state.get("knowledge_review_required"):
            records = context.get("records")
            if not isinstance(records, list) or not all(
                isinstance(item, dict)
                and all(
                    key in item
                    for key in (
                        "path",
                        "present",
                        "status",
                        "content_hash",
                        "source_fingerprint",
                        "computed_source_fingerprint",
                    )
                )
                and isinstance(item.get("path"), str)
                and isinstance(item.get("present"), bool)
                and (
                    item.get("status") is None
                    or isinstance(item.get("status"), str)
                )
                and all(
                    item.get(key) is None or isinstance(item.get(key), str)
                    for key in (
                        "content_hash",
                        "source_fingerprint",
                        "computed_source_fingerprint",
                    )
                )
                for item in records or []
            ):
                errors.append("knowledge_context.records is invalid")
            review = state.get("knowledge_review")
            if not isinstance(review, dict):
                errors.append("knowledge_review is invalid")
            else:
                if review.get("disposition") not in (None, "promote", "no-update"):
                    errors.append("knowledge_review.disposition is invalid")
                for key in (
                    "rationale",
                ):
                    if not isinstance(review.get(key), str):
                        errors.append(f"knowledge_review.{key} must be a string")
                for key in (
                    "affected_pages",
                    "covered_changed_paths",
                    "uncovered_changed_paths",
                ):
                    if not isinstance(review.get(key), list) or not all(
                        isinstance(item, str) for item in review.get(key, [])
                    ):
                        errors.append(f"knowledge_review.{key} must be a string array")
                for key in (
                    "change_fingerprint",
                    "recorded_at",
                    "invalidated_at",
                ):
                    if review.get(key) is not None and not isinstance(
                        review.get(key), str
                    ):
                        errors.append(f"knowledge_review.{key} must be a string or null")
                if review.get("disposition") is not None and (
                    not review.get("rationale", "").strip()
                    or not isinstance(review.get("change_fingerprint"), str)
                    or not review.get("change_fingerprint")
                    or not isinstance(review.get("recorded_at"), str)
                    or not review.get("recorded_at")
                ):
                    errors.append(
                        "knowledge_review disposition requires rationale, change_fingerprint, and recorded_at"
                    )
        updates = state.get("knowledge_updates")
        if not isinstance(updates, dict):
            errors.append("knowledge_updates is invalid")
        else:
            for key in ("upserts", "deletes", "coupled", "sealed"):
                if not isinstance(updates.get(key), list) or not all(
                    isinstance(item, str) for item in updates.get(key, [])
                ):
                    errors.append(f"knowledge_updates.{key} must be a string array")
            if not isinstance(updates.get("rationale"), str):
                errors.append("knowledge_updates.rationale must be a string")
            if updates.get("recorded_at") is not None and not isinstance(
                updates.get("recorded_at"), str
            ):
                errors.append("knowledge_updates.recorded_at must be a string or null")
            if updates.get("change_fingerprint") is not None and not isinstance(
                updates.get("change_fingerprint"), str
            ):
                errors.append("knowledge_updates.change_fingerprint must be a string or null")
    risk = state.get("risk")
    if (
        not isinstance(risk, dict)
        or risk.get("level") not in RISK_LEVELS
        or not isinstance(risk.get("rationale"), str)
        or risk.get("downgrade_rationale") is not None
        and not isinstance(risk.get("downgrade_rationale"), str)
    ):
        errors.append("risk model is invalid")
    scope = state.get("scope")
    if (
        not isinstance(scope, dict)
        or not isinstance(scope.get("paths"), list)
        or not all(isinstance(item, str) for item in scope.get("paths", []))
        or not isinstance(scope.get("rationale"), str)
    ):
        errors.append("scope model is invalid")
    gates = state.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates must be an object")
    else:
        for gate in GATES:
            record = gates.get(gate)
            if not isinstance(record, dict) or record.get("status") not in (
                "pending",
                "approved",
                "stale",
            ):
                errors.append(f"gate {gate} is invalid")
    for ledger in ("tasks", "evidence"):
        value = state.get(ledger)
        if not isinstance(value, dict) or not all(
            isinstance(item, dict) for item in value.values()
        ):
            errors.append(f"{ledger} must be an object")
    if not isinstance(state.get("waivers"), list) or not all(
        isinstance(item, dict) for item in state.get("waivers", [])
    ):
        errors.append("waivers must be an array")
    if errors:
        raise ValidationError(
            "Invalid DevWeave work-item model.",
            {"work": work_id, "errors": errors},
        )
    return state


def list_work(repo: Path, *, include_closed: bool = False) -> list[dict[str, Any]]:
    root = work_items_root(repo)
    if not root.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not (path / "state.json").exists():
            continue
        state = load_state(repo, path.name)
        if include_closed or state.get("status") != "closed":
            items.append(state)
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return items


def resolve_work(
    repo: Path,
    work_id: str | None,
    *,
    include_closed: bool = False,
) -> dict[str, Any]:
    if work_id:
        state = load_state(repo, work_id)
        if not include_closed and state.get("status") == "closed":
            raise SelectionError("The selected work item is closed.", {"work": work_id})
        return state
    candidates = list_work(repo, include_closed=include_closed)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SelectionError("No eligible DevWeave work item exists.", {"candidates": []})
    raise SelectionError(
        "Multiple DevWeave work items are eligible; choose one.",
        {
            "candidates": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "kind": item["kind"],
                    "phase": item["phase"],
                    "status": item["status"],
                }
                for item in candidates
            ]
        },
    )


def _artifact_bytes(repo: Path, work_id: str, names: Iterable[str]) -> bytes:
    pieces: list[bytes] = []
    root = work_root(repo, work_id)
    for name in names:
        path = root / name
        pieces.append(name.encode("utf-8") + b"\0")
        pieces.append(path.read_bytes() if path.exists() else b"<missing>")
        pieces.append(b"\0")
    return b"".join(pieces)


def scope_fingerprint(repo: Path, state: dict[str, Any]) -> str:
    material = _artifact_bytes(repo, state["id"], ("brief.md", "requirements.md"))
    scope_material = {
        "risk": state["risk"],
        "scope": state["scope"],
        "waivers": _waivers_for_gate(state, "scope"),
        "discovery_evidence": _discovery_evidence(state),
    }
    if "base_knowledge" in state:
        context = state.get("knowledge_context", {})
        scope_material["knowledge_context"] = context
        if state.get("knowledge_review_required"):
            captured = context.get("records", [])
            observed = captured
            if state.get("gates", {}).get("build", {}).get("status") != "approved":
                project = load_project(repo)
                current_knowledge = knowledge.knowledge_snapshot(
                    repo, root=project["knowledge"]["root"]
                )
                observed = knowledge.context_records(
                    current_knowledge, context.get("pages", [])
                )
            scope_material["knowledge_context_observed"] = observed
    material += canonical_json(scope_material)
    return sha256_bytes(material)


def _discovery_evidence(state: dict[str, Any]) -> list[dict[str, Any]]:
    required_kind = {"bug": "reproduction", "refactor": "baseline"}.get(
        state.get("kind")
    )
    if not required_kind:
        return []
    return [
        {
            "id": item.get("id"),
            "kind": item.get("kind"),
            "status": item.get("status"),
            "summary": item.get("summary"),
            "covers": item.get("covers", []),
            "observed_result": item.get("observed_result"),
            "source_fingerprint": item.get("source_fingerprint"),
            "git_head": item.get("git_head"),
        }
        for item in sorted(
            state.get("evidence", {}).values(), key=lambda value: value.get("id", "")
        )
        if item.get("kind") == required_kind
    ]


def build_fingerprint(repo: Path, state: dict[str, Any]) -> str:
    material = scope_fingerprint(repo, state).encode("ascii")
    material += _artifact_bytes(repo, state["id"], ("design.md", "plan.md"))
    material += canonical_json({"waivers": _waivers_for_gate(state, "build")})
    return sha256_bytes(material)


def _baseline_fingerprint(repo: Path, state: dict[str, Any]) -> str:
    update = state.get("baseline_updates", {})
    material: list[dict[str, Any]] = []
    for target in sorted(set(update.get("targets", []))):
        path = ensure_within(repo, repo / target)
        material.append(
            {
                "path": normalize_relpath(target),
                "hash": sha256_bytes(path.read_bytes()) if path.is_file() else "<missing>",
            }
        )
    return sha256_bytes(
        canonical_json(
            {
                "targets": material,
                "rationale": update.get("rationale", ""),
                "tree": baseline_snapshot(repo)["fingerprint"],
            }
        )
    )


def acceptance_fingerprint(
    repo: Path,
    state: dict[str, Any],
    source: dict[str, Any] | None = None,
) -> str:
    source = source or git_snapshot(repo)
    evidence = [
        {
            "id": item["id"],
            "kind": item["kind"],
            "status": item["status"],
            "covers": sorted(item.get("covers", [])),
            "source_fingerprint": item.get("source_fingerprint"),
            "stale": item.get("stale", False),
        }
        for item in sorted(state.get("evidence", {}).values(), key=lambda value: value["id"])
    ]
    material = build_fingerprint(repo, state).encode("ascii")
    material += _artifact_bytes(repo, state["id"], ("acceptance.md",))
    acceptance_material: dict[str, Any] = {
        "source": source["fingerprint"],
        "evidence": evidence,
        "baseline": _baseline_fingerprint(repo, state),
        "waivers": _waivers_for_gate(state, "acceptance"),
    }
    if "base_knowledge" in state:
        project = load_project(repo)
        current_knowledge = knowledge.knowledge_snapshot(
            repo, root=project["knowledge"]["root"]
        )
        acceptance_material["knowledge"] = {
            "fingerprint": current_knowledge["fingerprint"],
            "updates": state.get("knowledge_updates", {}),
        }
    material += canonical_json(acceptance_material)
    return sha256_bytes(material)


def _mark_gate_stale(gate: dict[str, Any]) -> None:
    if gate.get("status") == "approved":
        gate["status"] = "stale"
    gate["fingerprint"] = None
    gate["approved_by"] = None
    gate["approved_at"] = None


def sync_state_unlocked(repo: Path, state: dict[str, Any]) -> bool:
    if state.get("status") == "closed":
        return False
    changed = False
    invalidated_from: str | None = None
    scope_gate = state["gates"]["scope"]
    if scope_gate.get("status") == "approved":
        current = scope_fingerprint(repo, state)
        if current != scope_gate.get("fingerprint"):
            for gate in GATES:
                _mark_gate_stale(state["gates"][gate])
            state["phase"] = "requirements"
            invalidated_from = "scope"
            changed = True
    build_gate = state["gates"]["build"]
    if invalidated_from is None and build_gate.get("status") == "approved":
        current = build_fingerprint(repo, state)
        if current != build_gate.get("fingerprint"):
            _mark_gate_stale(state["gates"]["build"])
            _mark_gate_stale(state["gates"]["acceptance"])
            state["phase"] = "design"
            invalidated_from = "build"
            changed = True

    current_source = git_snapshot(repo)
    review = state.get("knowledge_review", {})
    if (
        state.get("knowledge_review_required")
        and isinstance(review, dict)
        and review.get("recorded_at")
        and review.get("change_fingerprint") != current_source["fingerprint"]
        and review.get("invalidated_at") is None
    ):
        review["invalidated_at"] = utc_now()
        state["knowledge_review"] = review
        state["knowledge_updates"] = _empty_knowledge_updates()
        append_event_unlocked(
            repo,
            state["id"],
            "knowledge_review_invalidated",
            {
                "review_fingerprint": review.get("change_fingerprint"),
                "current_fingerprint": current_source["fingerprint"],
            },
        )
        changed = True
    latest = state.get("last_verification")
    if latest and latest.get("source_fingerprint") != current_source["fingerprint"]:
        for item in state.get("evidence", {}).values():
            if item.get("binds_current_source") and not item.get("stale"):
                item["stale"] = True
                changed = True
        state["last_verification"] = None
        _mark_gate_stale(state["gates"]["acceptance"])
        if state["gates"]["build"].get("status") == "approved":
            state["phase"] = "verification"
        invalidated_from = invalidated_from or "source"

    acceptance_gate = state["gates"]["acceptance"]
    if invalidated_from is None and acceptance_gate.get("status") == "approved":
        current = acceptance_fingerprint(repo, state, current_source)
        if current != acceptance_gate.get("fingerprint"):
            _mark_gate_stale(acceptance_gate)
            state["phase"] = "verification"
            invalidated_from = "acceptance"
            changed = True

    if invalidated_from:
        append_event_unlocked(
            repo,
            state["id"],
            "downstream_invalidated",
            {"from": invalidated_from},
        )
    if changed:
        save_state_unlocked(repo, state)
    return changed


def sync_state(repo: Path, work_id: str) -> dict[str, Any]:
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        return state


def _read_artifact(repo: Path, state: dict[str, Any], name: str) -> str:
    path = work_root(repo, state["id"]) / name
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _heading_blocks(text: str) -> dict[str, str]:
    matches = list(HEADING_PATTERN.finditer(text))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.start() : end]
    return blocks


def _validate_id_sequence(
    text: str,
    prefixes: Iterable[str],
    artifact: str,
    errors: list[str],
) -> None:
    allowed = set(prefixes)
    prefix_expression = "|".join(sorted(allowed))
    candidate = re.compile(rf"^##\s+(?:{prefix_expression})-", re.IGNORECASE)
    valid = re.compile(
        rf"^##\s+(?:{prefix_expression})-\d{{3}}\s*:\s*\S", re.IGNORECASE
    )
    malformed = [
        line.strip()
        for line in text.splitlines()
        if candidate.match(line) and not valid.match(line)
    ]
    if malformed:
        errors.append(
            f"{artifact} contains malformed ID headings: {', '.join(malformed)}"
        )
    identifiers = [
        match.group(1)
        for match in HEADING_PATTERN.finditer(text)
        if match.group(1).split("-", 1)[0] in allowed
    ]
    duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicates:
        errors.append(f"{artifact} contains duplicate IDs: {', '.join(duplicates)}")
    for prefix in sorted(allowed):
        numbers = sorted(
            int(item.split("-", 1)[1])
            for item in identifiers
            if item.startswith(prefix + "-")
        )
        if numbers and numbers != list(range(1, max(numbers) + 1)):
            errors.append(f"{artifact} {prefix}-* IDs must be contiguous from 001.")


def _validate_evidence_id_syntax(
    covers: Sequence[str], tasks: Sequence[str]
) -> None:
    invalid_covers = sorted(
        {item for item in covers if not re.fullmatch(r"AC-\d{3}", item)}
    )
    invalid_tasks = sorted(
        {item for item in tasks if not re.fullmatch(r"TASK-\d{3}", item)}
    )
    if invalid_covers or invalid_tasks:
        raise ValidationError(
            "Evidence links must use AC-* and TASK-* IDs.",
            {"invalid_covers": invalid_covers, "invalid_tasks": invalid_tasks},
        )


def _task_dependency_graph(plan_blocks: dict[str, str]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for task_id, block in plan_blocks.items():
        if not task_id.startswith("TASK-"):
            continue
        match = DEPENDENCIES_PATTERN.search(block)
        if not match or match.group(1).strip().lower() in ("none", "無"):
            graph[task_id] = []
        else:
            graph[task_id] = _ids(match.group(1), ("TASK",))
    return graph


def _dependency_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(task_id: str) -> list[str] | None:
        if task_id in visiting:
            start = visiting.index(task_id)
            return visiting[start:] + [task_id]
        if task_id in visited:
            return None
        visiting.append(task_id)
        for dependency in graph.get(task_id, []):
            if dependency in graph:
                cycle = visit(dependency)
                if cycle:
                    return cycle
        visiting.pop()
        visited.add(task_id)
        return None

    for task_id in graph:
        cycle = visit(task_id)
        if cycle:
            return cycle
    return None


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    next_heading = text.find("\n## ", start + len(heading))
    return text[start : next_heading if next_heading >= 0 else len(text)]


def _ids(text: str, prefixes: Iterable[str]) -> list[str]:
    allowed = set(prefixes)
    return sorted(
        {
            match.group(0)
            for match in ID_PATTERN.finditer(text)
            if match.group(1) in allowed
        }
    )


def _validate_headings(
    text: str,
    headings: Iterable[str],
    artifact: str,
    errors: list[str],
) -> None:
    for heading in headings:
        if heading not in text:
            errors.append(f"{artifact} is missing required heading: {heading}")


def _waiver_exists(
    state: dict[str, Any],
    kind: str,
    target: str | None = None,
    gate: str | None = None,
) -> bool:
    return any(
        waiver.get("kind") == kind
        and (target is None or waiver.get("target") == target)
        and (gate is None or waiver.get("gate") == gate)
        and waiver.get("reason", "").strip()
        for waiver in state.get("waivers", [])
    )


def _waivers_for_gate(state: dict[str, Any], gate: str) -> list[dict[str, Any]]:
    return [
        {
            "id": waiver.get("id"),
            "kind": waiver.get("kind"),
            "target": waiver.get("target"),
            "reason": waiver.get("reason"),
            "approved_by": waiver.get("approved_by"),
            "approved_at": waiver.get("approved_at"),
        }
        for waiver in state.get("waivers", [])
        if waiver.get("gate") == gate
    ]


def _current_gate_for_phase(phase: str) -> str | None:
    return {
        "requirements": "scope",
        "scope_review": "scope",
        "design": "build",
        "build_review": "build",
        "implementation": None,
        "verification": "acceptance",
        "acceptance_review": "acceptance",
        "closed": None,
    }.get(phase)


def _validate_knowledge_context(
    repo: Path,
    state: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    if "base_knowledge" not in state:
        return
    project = load_project(repo)
    root = project["knowledge"]["root"]
    context = state.get("knowledge_context", {})
    pages = context.get("pages", [])
    index = f"{root}/index.md"
    if not context.get("recorded_at") or not pages:
        errors.append("G1 requires a recorded Wiki-first knowledge context.")
        return
    if pages[0] != index or pages.count(index) != 1:
        errors.append("Knowledge context must record wiki/index.md first and exactly once.")
    if len(pages) > 6 or len(pages) != len(set(pages)):
        errors.append("Knowledge context may include index plus at most five unique related pages.")
    try:
        current = knowledge.knowledge_snapshot(repo, root=root)
    except knowledge.KnowledgeError as exc:
        errors.append(f"Knowledge context cannot be checked: {exc.message}")
        return
    if state.get("knowledge_review_required"):
        captured_records = context.get("records", [])
        current_records = knowledge.context_records(current, pages)
        if captured_records != current_records:
            errors.append(
                "Knowledge context pages or source observations changed after they were recorded."
            )
    nonfresh: list[str] = []
    for page in pages:
        try:
            normalized = knowledge.normalize_page(page, root)
        except knowledge.KnowledgeError as exc:
            errors.append(f"Knowledge context page is invalid: {exc.message}")
            continue
        record = current.get("pages", {}).get(normalized)
        if (
            not record
            or record.get("status") != "active"
            or record.get("parse_errors")
            or record.get("source_error")
            or record.get("source_fingerprint")
            != record.get("computed_source_fingerprint")
        ):
            nonfresh.append(normalized)
    if nonfresh and not context.get("gaps"):
        errors.append(
            "Knowledge context has missing, placeholder, stale, or invalid pages without a gap: "
            + ", ".join(nonfresh)
        )
    if context.get("gaps"):
        warnings.append(
            f"Knowledge context records {len(context['gaps'])} gap(s) for raw-source follow-up."
        )


def _validate_knowledge_acceptance(
    repo: Path,
    state: dict[str, Any],
    changed_source_paths: Sequence[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    if "base_knowledge" not in state:
        return
    project = load_project(repo)
    root = project["knowledge"]["root"]
    base = state["base_knowledge"]
    try:
        current = knowledge.knowledge_snapshot(repo, root=root)
        lint = knowledge.lint_wiki(
            repo, root=root, base_snapshot=base, snapshot=current
        )
    except knowledge.KnowledgeError as exc:
        errors.append(f"Knowledge validation failed: {exc.message}")
        return
    for finding in lint.get("findings", []):
        page = f" [{finding['page']}]" if finding.get("page") else ""
        message = f"Wiki {finding['code']}{page}: {finding['message']}"
        if finding.get("severity") == "critical":
            errors.append(message)
        else:
            warnings.append(message)

    updates = state.get("knowledge_updates", {})
    upserts = set(updates.get("upserts", []))
    deletes = set(updates.get("deletes", []))
    coupled = set(updates.get("coupled", []))
    sealed = set(updates.get("sealed", []))
    declared = upserts | deletes | coupled
    actual = set(knowledge.changed_knowledge_paths(base, current))
    undeclared = sorted(actual - declared)
    unchanged = sorted(declared - actual)
    if undeclared:
        errors.append("Changed Wiki paths were not declared: " + ", ".join(undeclared))
    if unchanged:
        errors.append("Declared Wiki targets have no work-item change: " + ", ".join(unchanged))

    content_targets = upserts | deletes
    expected_coupled = {f"{root}/index.md", f"{root}/log.md"} if content_targets else set()
    if coupled != expected_coupled:
        errors.append("Wiki content updates must couple exactly wiki/index.md and wiki/log.md.")
    for page in sorted(deletes):
        if page not in base.get("pages", {}):
            errors.append(f"Deleted Wiki target was not present at work start: {page}")
        if page in current.get("pages", {}):
            errors.append(f"Declared Wiki delete target still exists: {page}")

    def active_current(page: str) -> bool:
        record = current.get("pages", {}).get(page)
        return bool(
            record
            and page in sealed
            and record.get("status") == "active"
            and not record.get("parse_errors")
            and not record.get("source_error")
            and record.get("verified_by") == state["id"]
            and record.get("source_fingerprint")
            == record.get("computed_source_fingerprint")
        )

    for page in sorted(upserts | coupled):
        if page not in current.get("pages", {}):
            errors.append(f"Declared Wiki upsert target does not exist: {page}")
        elif not active_current(page):
            errors.append(
                f"Wiki target is not active and sealed against current sources by this work item: {page}"
            )

    affected = knowledge.affected_pages(base, changed_source_paths)

    if state.get("knowledge_review_required"):
        review = state.get("knowledge_review", {})
        current_source = git_snapshot(repo)
        review_current = bool(
            isinstance(review, dict)
            and review.get("disposition") in ("promote", "no-update")
            and review.get("rationale")
            and review.get("recorded_at")
            and review.get("invalidated_at") is None
            and review.get("change_fingerprint")
            == current_source["fingerprint"]
        )
        if not review_current:
            errors.append(
                "A current knowledge review is required before G3 acceptance."
            )
        elif review["disposition"] == "no-update":
            if state.get("knowledge_profile") == "bootstrap":
                errors.append("Knowledge no-update is not allowed for Wiki bootstrap work.")
            if affected:
                errors.append(
                    "Knowledge no-update cannot leave affected Wiki pages unresolved: "
                    + ", ".join(affected)
                )
            if actual or content_targets or coupled or sealed:
                errors.append(
                    "Knowledge no-update requires no Wiki diff or knowledge plan."
                )
        else:
            if not 1 <= len(content_targets) <= 5:
                errors.append(
                    "A promote knowledge review requires a plan with one to five content targets."
                )
            if updates.get("change_fingerprint") != current_source["fingerprint"]:
                errors.append(
                    "The knowledge plan is stale relative to the promote knowledge review."
                )

    if state.get("knowledge_profile") == "bootstrap":
        if changed_source_paths:
            errors.append(
                "Wiki bootstrap work must not modify product source: "
                + ", ".join(sorted(changed_source_paths))
            )
        if deletes:
            errors.append("Wiki bootstrap may not delete content pages.")
        if not 3 <= len(upserts) <= 5:
            errors.append(
                "Wiki bootstrap must upsert three to five content pages."
            )
        overview = f"{root}/overview.md"
        if overview not in upserts:
            errors.append("Wiki bootstrap must upsert wiki/overview.md.")
        bootstrap_records = {
            page: current.get("pages", {}).get(page) for page in upserts
        }
        if not any(
            isinstance(record, dict) and record.get("type") == "architecture"
            for record in bootstrap_records.values()
        ):
            errors.append("Wiki bootstrap must upsert an architecture page.")
        if not any(
            isinstance(record, dict) and record.get("type") == "module"
            for record in bootstrap_records.values()
        ):
            errors.append("Wiki bootstrap must upsert a module page.")
        assessment = knowledge.bootstrap_assessment(
            repo, root=root, snapshot=current
        )
        if not assessment["complete"]:
            errors.append(
                "Wiki bootstrap core knowledge is not complete: "
                + ", ".join(assessment["reasons"])
            )

    for page in affected:
        if page in deletes and page not in current.get("pages", {}):
            continue
        if page not in upserts or not active_current(page):
            errors.append(
                f"Affected Wiki page must be refreshed and sealed or deleted: {page}"
            )

    if state.get("kind") == "new":
        overview = f"{root}/overview.md"
        record = current.get("pages", {}).get(overview)
        if (
            overview not in upserts
            or not active_current(overview)
            or not record
            or not record.get("sources")
            or record.get("source_fingerprint") == "none"
        ):
            errors.append(
                "New-project work must promote wiki/overview.md to an active, sourced, sealed page."
            )

    if content_targets:
        for message in knowledge.validate_promote_log(
            repo, state["id"], root=root, base=base
        ):
            errors.append(f"Wiki log: {message}")


def validate_work(
    repo: Path,
    state: dict[str, Any],
    gate: str | None = None,
) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    gate = gate or _current_gate_for_phase(state.get("phase", ""))
    if gate is not None and gate not in GATES:
        raise ValidationError("Unknown gate.", {"gate": gate, "allowed": list(GATES)})

    brief = _read_artifact(repo, state, "brief.md")
    requirements = _read_artifact(repo, state, "requirements.md")
    design = _read_artifact(repo, state, "design.md")
    plan = _read_artifact(repo, state, "plan.md")
    acceptance = _read_artifact(repo, state, "acceptance.md")
    texts = {
        "brief.md": brief,
        "requirements.md": requirements,
        "design.md": design,
        "plan.md": plan,
        "acceptance.md": acceptance,
    }
    for name, text in texts.items():
        if not text:
            errors.append(f"Missing artifact: {name}")

    _validate_headings(
        brief,
        ("## 問題與目標", "## 現況證據", "## 範圍", "## 非目標", "## 風險"),
        "brief.md",
        errors,
    )
    requirement_blocks = _heading_blocks(requirements)
    _validate_id_sequence(
        requirements, ("REQ", "NFR", "AC"), "requirements.md", errors
    )
    requirement_ids = sorted(
        key for key in requirement_blocks if key.startswith(("REQ-", "NFR-"))
    )
    acceptance_ids = sorted(key for key in requirement_blocks if key.startswith("AC-"))
    if not requirement_ids:
        errors.append("requirements.md must define at least one REQ-* or NFR-* heading.")
    if not acceptance_ids:
        errors.append("requirements.md must define at least one AC-* heading.")
    for requirement_id in requirement_ids:
        linked = _ids(requirement_blocks[requirement_id], ("AC",))
        if not linked:
            errors.append(f"{requirement_id} does not trace to an AC-*.")
        unknown = sorted(set(linked) - set(acceptance_ids))
        if unknown:
            errors.append(
                f"{requirement_id} traces to undefined acceptance criteria: {', '.join(unknown)}"
            )
    for acceptance_id in acceptance_ids:
        linked = _ids(requirement_blocks[acceptance_id], ("REQ", "NFR"))
        if not linked:
            errors.append(f"{acceptance_id} does not trace to a REQ-* or NFR-*.")
        unknown = sorted(set(linked) - set(requirement_ids))
        if unknown:
            errors.append(
                f"{acceptance_id} traces to undefined requirements: {', '.join(unknown)}"
            )

    trace = {
        "requirements": requirement_ids,
        "acceptance_criteria": acceptance_ids,
        "decisions": [],
        "tasks": [],
        "evidence": sorted(state.get("evidence", {})),
    }

    if gate in ("build", "acceptance"):
        if state["gates"]["scope"].get("status") != "approved":
            errors.append("G1 scope approval is not current.")
        design_blocks = _heading_blocks(design)
        _validate_id_sequence(design, ("DEC",), "design.md", errors)
        decision_ids = sorted(key for key in design_blocks if key.startswith("DEC-"))
        trace["decisions"] = decision_ids
        if not decision_ids:
            errors.append("design.md must define at least one DEC-* heading.")
        for decision_id in decision_ids:
            linked = _ids(design_blocks[decision_id], ("REQ", "NFR"))
            if not linked:
                errors.append(f"{decision_id} does not trace to a requirement.")
            unknown = sorted(set(linked) - set(requirement_ids))
            if unknown:
                errors.append(
                    f"{decision_id} traces to undefined requirements: {', '.join(unknown)}"
                )
        _validate_headings(
            design,
            ("## 選項比較", "## 介面與資料流", "## 失敗模式與回復"),
            "design.md",
            errors,
        )
        if state["risk"]["level"] == "high" and "## 高風險分析" not in design:
            errors.append("High-risk work requires the 高風險分析 section in design.md.")
        if state["risk"]["level"] == "high":
            analysis = _section(design, "## 高風險分析").lower()
            required_topics = {
                "migration": ("migration", "遷移"),
                "rollback": ("rollback", "回復", "回滾"),
                "security": ("security", "安全"),
                "compatibility": ("compatibility", "相容"),
                "performance": ("performance", "效能", "性能"),
            }
            missing_topics = [
                topic
                for topic, terms in required_topics.items()
                if not any(term in analysis for term in terms)
            ]
            if missing_topics:
                errors.append(
                    "High-risk analysis must address or mark not applicable: "
                    + ", ".join(missing_topics)
                )
        plan_blocks = _heading_blocks(plan)
        _validate_id_sequence(plan, ("TASK",), "plan.md", errors)
        task_ids = sorted(key for key in plan_blocks if key.startswith("TASK-"))
        trace["tasks"] = task_ids
        if not task_ids:
            errors.append("plan.md must define at least one TASK-* heading.")
        dependencies = _task_dependency_graph(plan_blocks)
        for task_id, linked_tasks in dependencies.items():
            unknown_dependencies = sorted(set(linked_tasks) - set(task_ids))
            if task_id in linked_tasks:
                errors.append(f"{task_id} cannot depend on itself.")
            if unknown_dependencies:
                errors.append(
                    f"{task_id} has undefined dependencies: {', '.join(unknown_dependencies)}"
                )
        cycle = _dependency_cycle(dependencies)
        if cycle:
            errors.append("Task dependency cycle: " + " -> ".join(cycle))
        for task_id in task_ids:
            block = plan_blocks[task_id]
            linked_requirements = _ids(block, ("REQ", "NFR"))
            linked_acceptance = _ids(block, ("AC",))
            linked_decisions = _ids(block, ("DEC",))
            if not linked_requirements:
                errors.append(f"{task_id} does not trace to a requirement.")
            if not linked_acceptance:
                errors.append(f"{task_id} does not trace to an acceptance criterion.")
            if not linked_decisions:
                errors.append(f"{task_id} does not trace to a decision.")
            unknown_requirements = sorted(
                set(linked_requirements) - set(requirement_ids)
            )
            unknown_acceptance = sorted(set(linked_acceptance) - set(acceptance_ids))
            unknown_decisions = sorted(set(linked_decisions) - set(decision_ids))
            if unknown_requirements or unknown_acceptance or unknown_decisions:
                errors.append(
                    f"{task_id} has undefined trace links: "
                    + ", ".join(
                        unknown_requirements + unknown_acceptance + unknown_decisions
                    )
                )

    if gate == "scope":
        for name in ("brief.md", "requirements.md"):
            if TODO_PATTERN.search(texts[name]):
                errors.append(f"{name} still contains TODO markers.")
        if not state["risk"].get("rationale", "").strip():
            errors.append("Risk rationale is required before G1.")
        if state["risk"]["level"] == "low" and not state["risk"].get(
            "downgrade_rationale"
        ):
            errors.append("Low-risk classification requires a downgrade rationale.")
        if not state["scope"].get("paths"):
            errors.append("At least one approved scope path is required before G1.")
        _validate_knowledge_context(repo, state, errors, warnings)
        if state["kind"] == "bug":
            reproduction = [
                item
                for item in state.get("evidence", {}).values()
                if item.get("kind") == "reproduction"
                and item.get("status") == "passed"
                and item.get("observed_result") == "failure"
            ]
            if not reproduction and not _waiver_exists(state, "unreproducible"):
                errors.append(
                    "Bug work requires failing reproduction evidence or an unreproducible waiver."
                )
        if state["kind"] == "refactor":
            baseline = [
                item
                for item in state.get("evidence", {}).values()
                if item.get("kind") == "baseline" and item.get("status") == "passed"
            ]
            if not baseline:
                errors.append("Refactor work requires passing baseline evidence before G1.")

    if gate == "build":
        for name in ("design.md", "plan.md"):
            if TODO_PATTERN.search(texts[name]):
                errors.append(f"{name} still contains TODO markers.")

    if gate == "acceptance":
        if state["gates"]["build"].get("status") != "approved":
            errors.append("G2 build approval is not current.")
        if TODO_PATTERN.search(acceptance):
            errors.append("acceptance.md still contains TODO markers.")
        _validate_headings(
            acceptance,
            ("## 驗證矩陣", "## 基線更新", "## 殘餘風險"),
            "acceptance.md",
            errors,
        )
        if state["risk"]["level"] == "high":
            _validate_headings(
                acceptance,
                ("## 獨立 Review",),
                "acceptance.md",
                errors,
            )
        for acceptance_id in acceptance_ids:
            if acceptance_id not in acceptance:
                errors.append(f"acceptance.md does not account for {acceptance_id}.")
        task_ids = trace["tasks"]
        task_state = state.get("tasks", {})
        if set(task_ids) != set(task_state):
            errors.append("Machine task ledger does not match the approved plan.")
        incomplete = [
            task_id
            for task_id in task_ids
            if task_state.get(task_id, {}).get("status") != "completed"
        ]
        if incomplete:
            errors.append(f"Incomplete tasks: {', '.join(incomplete)}")

        current_source = git_snapshot(repo)
        passing_evidence = [
            item
            for item in state.get("evidence", {}).values()
            if item.get("status") == "passed" and not item.get("stale")
        ]
        source_bound_evidence = [
            item
            for item in passing_evidence
            if item.get("binds_current_source")
            and item.get("source_fingerprint") == current_source["fingerprint"]
        ]
        coverage = {
            covered
            for item in source_bound_evidence
            for covered in item.get("covers", [])
            if covered.startswith("AC-")
        }
        missing_coverage = sorted(set(acceptance_ids) - coverage)
        if missing_coverage:
            errors.append(
                f"Acceptance criteria without current passing evidence: {', '.join(missing_coverage)}"
            )
        required_kinds = {
            "new": {"acceptance"},
            "feature": {"acceptance", "regression"},
            "refactor": {"equivalence", "regression"},
            "bug": {"regression"},
        }[state["kind"]]
        observed_kinds = {item.get("kind") for item in source_bound_evidence}
        missing_kinds = sorted(required_kinds - observed_kinds)
        if missing_kinds:
            errors.append(
                f"Missing required passing evidence kinds: {', '.join(missing_kinds)}"
            )
        if state["risk"]["level"] == "high":
            current_reviews = [
                item
                for item in state.get("evidence", {}).values()
                if item.get("kind") == "review"
                and item.get("binds_current_source")
                and not item.get("stale")
                and item.get("source_fingerprint") == current_source["fingerprint"]
            ]
            if not current_reviews:
                warnings.append(
                    "High-risk independent review is missing or unavailable; human G3 approval may continue with attention."
                )
            else:
                current_review = sorted(
                    current_reviews, key=lambda item: item.get("id", "")
                )[-1]
                review_metadata = current_review.get("review")
                review_id = current_review.get("id", "<unknown>")
                if not isinstance(review_metadata, dict):
                    errors.append(f"{review_id} has invalid independent review metadata.")
                else:
                    review_result = review_metadata.get("result")
                    review_severity = review_metadata.get("severity")
                    findings = review_metadata.get("findings", [])
                    if review_result not in REVIEW_RESULTS or review_severity not in REVIEW_SEVERITIES:
                        errors.append(f"{review_id} has invalid independent review result metadata.")
                    elif not isinstance(findings, list) or not all(
                        isinstance(item, dict) for item in findings
                    ):
                        errors.append(f"{review_id} has invalid independent review findings.")
                    else:
                        if review_id not in acceptance:
                            errors.append(f"acceptance.md does not account for {review_id}.")
                        for finding in findings:
                            finding_id = finding.get("id")
                            if not isinstance(finding_id, str):
                                errors.append(f"{review_id} contains a finding without a named ID.")
                            elif finding_id not in acceptance:
                                errors.append(
                                    f"acceptance.md does not account for review finding {finding_id}."
                                )
                        if review_result == "unavailable":
                            warnings.append(
                                f"Independent review {review_id} is unavailable; human G3 approval may continue."
                            )
                        elif review_result == "passed":
                            if review_severity == "advisory" or any(
                                item.get("severity") == "advisory" for item in findings
                            ):
                                warnings.append(
                                    f"Independent review {review_id} passed with advisory findings."
                                )
                        elif review_result == "critical":
                            critical_findings = [
                                item
                                for item in findings
                                if item.get("severity") == "critical"
                            ]
                            if not critical_findings:
                                errors.append(
                                    f"Independent review {review_id} is critical without a critical finding."
                                )
                            for finding in critical_findings:
                                finding_id = finding.get("id")
                                if not isinstance(finding_id, str) or not _waiver_exists(
                                    state,
                                    "review-critical",
                                    finding_id,
                                    gate="acceptance",
                                ):
                                    errors.append(
                                        f"Critical independent review finding requires a named review-critical waiver: {finding_id}"
                                    )
                                else:
                                    if finding_id not in acceptance:
                                        errors.append(
                                            f"acceptance.md must name the waiver target {finding_id}."
                                        )
                                    warnings.append(
                                        f"Critical independent review finding {finding_id} is covered by a narrow waiver."
                                    )
        known_tasks = set(task_ids)
        known_acceptance = set(acceptance_ids)
        for item in source_bound_evidence:
            evidence_id = item.get("id", "<unknown>")
            covers = set(item.get("covers", []))
            tasks = set(item.get("tasks", []))
            if not covers:
                errors.append(f"{evidence_id} does not trace to an AC-*.")
            if not tasks:
                errors.append(f"{evidence_id} does not trace to a TASK-*.")
            unknown_covers = sorted(covers - known_acceptance)
            unknown_tasks = sorted(tasks - known_tasks)
            if unknown_covers or unknown_tasks:
                errors.append(
                    f"{evidence_id} has undefined trace links: "
                    + ", ".join(unknown_covers + unknown_tasks)
                )
            if evidence_id not in acceptance:
                errors.append(f"acceptance.md does not account for {evidence_id}.")

        project = load_project(repo)
        commands = {item.get("id"): item for item in project.get("commands", [])}
        required_commands = project.get("verification_profiles", {}).get(
            state["risk"]["level"], []
        )
        for command_id in required_commands:
            if command_id not in commands:
                if not _waiver_exists(state, "missing-command", command_id):
                    errors.append(f"Required verification command is undefined: {command_id}")
                continue
            current_pass = any(
                item.get("command_id") == command_id
                and item.get("status") == "passed"
                and not item.get("stale")
                and item.get("source_fingerprint") == current_source["fingerprint"]
                for item in passing_evidence
            )
            if not current_pass and not _waiver_exists(
                state, "missing-command", command_id
            ):
                errors.append(
                    f"Required verification command has no current passing evidence: {command_id}"
                )

        update = state.get("baseline_updates", {})
        if not update.get("targets") and not update.get("rationale", "").strip():
            errors.append(
                "Record baseline update targets or a rationale that no baseline update is needed."
            )
        base_baseline_files = state.get("base_baseline", {}).get("files", {})
        current_baseline = baseline_snapshot(repo)
        current_baseline_files = current_baseline["files"]
        changed_baseline = sorted(
            path
            for path in set(base_baseline_files) | set(current_baseline_files)
            if base_baseline_files.get(path) != current_baseline_files.get(path)
        )
        declared_targets = set(update.get("targets", []))
        undeclared_baseline = sorted(set(changed_baseline) - declared_targets)
        unchanged_targets = sorted(declared_targets - set(changed_baseline))
        if undeclared_baseline:
            errors.append(
                "Changed baseline paths not declared by this work item: "
                + ", ".join(undeclared_baseline)
            )
        if unchanged_targets:
            errors.append(
                "Declared baseline targets have no work-item change: "
                + ", ".join(unchanged_targets)
            )
        for target in update.get("targets", []):
            path = ensure_within(repo, repo / target)
            if not path.is_file() and target not in base_baseline_files:
                errors.append(f"Baseline update target does not exist: {target}")
        if state["kind"] == "new" and ".devweave/baseline/architecture.md" not in update.get(
            "targets", []
        ):
            errors.append(
                "New-project work must update .devweave/baseline/architecture.md."
            )

        changed = changed_paths_since(repo, state.get("base_source", {}))
        _validate_knowledge_acceptance(repo, state, changed, errors, warnings)
        out_of_scope = [
            path
            for path in changed
            if not path_matches_scope(path, state["scope"].get("paths", []))
            and not _waiver_exists(state, "out-of-scope", path)
        ]
        if out_of_scope:
            errors.append(
                f"Changed paths outside approved scope: {', '.join(out_of_scope)}"
            )
        latest = state.get("last_verification")
        if not latest or latest.get("source_fingerprint") != current_source["fingerprint"]:
            errors.append("No current verification snapshot covers the present source state.")

    return ValidationReport(gate=gate, errors=errors, warnings=warnings, trace=trace)


def _actor(repo: Path, explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    name = _git(repo, ["config", "user.name"], check=False).stdout.decode(
        "utf-8", errors="replace"
    ).strip()
    email = _git(repo, ["config", "user.email"], check=False).stdout.decode(
        "utf-8", errors="replace"
    ).strip()
    if name and email:
        return f"{name} <{email}>"
    return name or email or getpass.getuser()


def _task_ids_from_plan(repo: Path, state: dict[str, Any]) -> list[str]:
    plan = _read_artifact(repo, state, "plan.md")
    blocks = _heading_blocks(plan)
    return sorted(key for key in blocks if key.startswith("TASK-"))


def approve_gate(
    repo: Path,
    work_id: str,
    gate: str | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if state.get("status") == "closed":
            raise ValidationError("Closed work cannot be approved.")
        expected_gate = _current_gate_for_phase(state["phase"])
        gate = gate or expected_gate
        if gate not in GATES:
            raise ValidationError(
                "The current phase is not awaiting a human approval.",
                {"phase": state["phase"]},
            )
        if gate != expected_gate:
            raise ValidationError(
                "The requested gate is not the current phase gate.",
                {
                    "phase": state["phase"],
                    "requested_gate": gate,
                    "expected_gate": expected_gate,
                },
            )
        report = validate_work(repo, state, gate)
        if not report.ok:
            raise ValidationError(f"{gate} gate is not ready.", report.as_dict())
        if gate == "scope":
            fingerprint = scope_fingerprint(repo, state)
            next_phase = "design"
        elif gate == "build":
            fingerprint = build_fingerprint(repo, state)
            next_phase = "implementation"
            state["tasks"] = {
                task_id: {
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "evidence": [],
                    "note": "",
                }
                for task_id in _task_ids_from_plan(repo, state)
            }
        else:
            source = git_snapshot(repo)
            fingerprint = acceptance_fingerprint(repo, state, source)
            next_phase = "acceptance_review"
        approval = state["gates"][gate]
        approval.update(
            {
                "status": "approved",
                "fingerprint": fingerprint,
                "approved_by": _actor(repo, actor),
                "approved_at": utc_now(),
            }
        )
        state["phase"] = next_phase
        state["blocker"] = None
        save_state_unlocked(repo, state)
        append_event_unlocked(
            repo,
            work_id,
            "gate_approved",
            {"gate": gate, "actor": approval["approved_by"], "fingerprint": fingerprint},
        )
        return state


def set_risk(
    repo: Path,
    work_id: str,
    level: str,
    rationale: str,
    downgrade_rationale: str | None = None,
) -> dict[str, Any]:
    if level not in RISK_LEVELS:
        raise ValidationError("Unknown risk level.", {"level": level})
    if not rationale.strip():
        raise ValidationError("Risk rationale must not be empty.")
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        previous = state.get("risk", {}).get("level", "standard")
        is_downgrade = RISK_RANK[level] < RISK_RANK.get(previous, 1)
        if (level == "low" or is_downgrade) and not (
            downgrade_rationale or ""
        ).strip():
            raise ValidationError("Risk downgrade requires a recorded rationale.")
        state["risk"] = {
            "level": level,
            "rationale": rationale.strip(),
            "downgrade_rationale": (downgrade_rationale or "").strip() or None,
        }
        sync_state_unlocked(repo, state)
        save_state_unlocked(repo, state)
        append_event_unlocked(repo, work_id, "risk_set", state["risk"])
        return state


def set_scope(
    repo: Path,
    work_id: str,
    paths: Sequence[str],
    rationale: str,
) -> dict[str, Any]:
    normalized = sorted({normalize_relpath(path) for path in paths if path.strip()})
    if not normalized:
        raise ValidationError("At least one scope path is required.")
    if not rationale.strip():
        raise ValidationError("Scope rationale must not be empty.")
    for pattern in normalized:
        if ".." in Path(pattern).parts or Path(pattern).is_absolute():
            raise ValidationError("Scope paths must stay relative to the repository.", {"path": pattern})
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        state["scope"] = {"paths": normalized, "rationale": rationale.strip()}
        sync_state_unlocked(repo, state)
        save_state_unlocked(repo, state)
        append_event_unlocked(repo, work_id, "scope_set", state["scope"])
        return state


def set_baseline_updates(
    repo: Path,
    work_id: str,
    targets: Sequence[str],
    rationale: str,
) -> dict[str, Any]:
    normalized = sorted({normalize_relpath(path) for path in targets if path.strip()})
    if not normalized and not rationale.strip():
        raise ValidationError("Baseline update rationale is required when no targets are listed.")
    for target in normalized:
        candidate = ensure_within(repo, repo / target)
        baseline_root = (repo / ".devweave" / "baseline").resolve()
        try:
            candidate.relative_to(baseline_root)
        except ValueError:
            raise ValidationError(
                "Baseline targets must be inside .devweave/baseline/.",
                {"target": target},
            )
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        state["baseline_updates"] = {
            "targets": normalized,
            "rationale": rationale.strip(),
            "recorded_at": utc_now(),
        }
        save_state_unlocked(repo, state)
        append_event_unlocked(
            repo, work_id, "baseline_updates_set", state["baseline_updates"]
        )
        return state


def _raise_knowledge(exc: knowledge.KnowledgeError) -> None:
    raise ValidationError(
        exc.message,
        {"knowledge_code": exc.code, "details": exc.details},
    ) from exc


def bootstrap_knowledge_work(repo: Path) -> dict[str, Any]:
    """Create or resolve the single repository-wide Wiki bootstrap work item."""

    if _project_requires_bootstrap(repo):
        init_project(repo)
    project = load_project(repo)
    with WorkLock(repo, "knowledge-bootstrap"):
        try:
            assessment = knowledge.bootstrap_assessment(
                repo, root=project["knowledge"]["root"]
            )
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        if assessment["complete"]:
            return {
                "action": "already_complete",
                "work": None,
                "bootstrap": assessment,
            }
        active = [
            state
            for state in list_work(repo)
            if state.get("knowledge_profile") == "bootstrap"
        ]
        if len(active) > 1:
            raise SelectionError(
                "Multiple active Wiki bootstrap work items exist; choose and reconcile one.",
                {"candidates": [state["id"] for state in active]},
            )
        if active:
            return {
                "action": "resume",
                "work": active[0],
                "bootstrap": assessment,
            }
        state = create_work(
            repo,
            kind="feature",
            title="建立初始 Codebase Wiki",
            risk="standard",
            risk_rationale=(
                "Bootstrap 只提升 source-bound Wiki knowledge，沿用 G1/G2/G3 與完整驗證。"
            ),
            knowledge_profile="bootstrap",
        )
        return {"action": "created", "work": state, "bootstrap": assessment}


def work_knowledge_status(repo: Path, state: dict[str, Any] | None = None) -> dict[str, Any]:
    project = load_project(repo)
    root = project["knowledge"]["root"]
    try:
        current = knowledge.knowledge_snapshot(repo, root=root)
        result = knowledge.knowledge_status(repo, root=root, snapshot=current)
        bootstrap = knowledge.bootstrap_assessment(repo, root=root, snapshot=current)
    except knowledge.KnowledgeError as exc:
        _raise_knowledge(exc)
    result["bootstrap"] = bootstrap
    result["legacy_work"] = state is not None and "knowledge_review_required" not in state
    if state is None or "base_knowledge" not in state:
        bootstrap_pending = any(
            item.get("code") == "missing_wiki" for item in result.get("critical", [])
        )
        if state is not None and bootstrap_pending:
            result["health"] = "bootstrap_pending"
            result["critical"] = []
        result.update(
            {
                "affected_pages": [],
                "pending_refresh": [],
                "changed_paths": [],
                "planned": None,
                "bootstrap_pending": bootstrap_pending,
                "covered_changed_paths": [],
                "uncovered_changed_paths": [],
                "review": {
                    "required": False,
                    "current": False,
                    "disposition": None,
                },
            }
        )
        return result
    changed_source = (
        changed_paths_since(repo, state.get("base_source", {}))
        if state.get("phase") in ("verification", "acceptance_review", "closed")
        else []
    )
    affected = knowledge.affected_pages(state["base_knowledge"], changed_source)
    coverage = knowledge.coverage_paths(current, changed_source)
    current_source = git_snapshot(repo)
    review_state = state.get("knowledge_review", {})
    review = dict(review_state) if isinstance(review_state, dict) else {}
    review.update(
        {
            "required": bool(state.get("knowledge_review_required")),
            "current": bool(
                review.get("disposition")
                and review.get("rationale", "").strip()
                and review.get("recorded_at")
                and review.get("invalidated_at") is None
                and review.get("change_fingerprint")
                == current_source["fingerprint"]
            ),
        }
    )
    updates = state.get("knowledge_updates", {})
    upserts = set(updates.get("upserts", []))
    deletes = set(updates.get("deletes", []))
    sealed = set(updates.get("sealed", []))
    pending: list[str] = []
    for page in affected:
        record = current.get("pages", {}).get(page)
        deleted = page in deletes and record is None
        refreshed = bool(
            page in upserts
            and page in sealed
            and record
            and record.get("status") == "active"
            and record.get("verified_by") == state["id"]
            and record.get("source_fingerprint") == record.get("computed_source_fingerprint")
        )
        if not deleted and not refreshed:
            pending.append(page)
    result.update(
        {
            "affected_pages": affected[:50],
            "pending_refresh": sorted(pending)[:50],
            "changed_paths": knowledge.changed_knowledge_paths(
                state["base_knowledge"], current
            )[:50],
            "planned": updates,
            "covered_changed_paths": coverage["covered"][:50],
            "uncovered_changed_paths": coverage["uncovered"][:50],
            "review": review,
        }
    )
    return result


def set_knowledge_review(
    repo: Path,
    work_id: str,
    disposition: str,
    rationale: str,
) -> dict[str, Any]:
    if disposition not in ("promote", "no-update"):
        raise ValidationError(
            "Knowledge review disposition must be promote or no-update.",
            {"disposition": disposition},
        )
    if not rationale.strip():
        raise ValidationError("Knowledge review rationale must not be empty.")
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if not state.get("knowledge_review_required"):
            raise ValidationError(
                "This legacy work item does not require a retrospective knowledge review."
            )
        if state["gates"]["build"].get("status") != "approved" or state[
            "phase"
        ] not in ("verification", "acceptance_review"):
            raise ValidationError(
                "Knowledge review may be recorded only during verification or acceptance.",
                {"phase": state["phase"]},
            )
        project = load_project(repo)
        root = project["knowledge"]["root"]
        try:
            current_knowledge = knowledge.knowledge_snapshot(repo, root=root)
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        current_source = git_snapshot(repo)
        changed_source = changed_paths_since(repo, state.get("base_source", {}))
        affected = knowledge.affected_pages(state["base_knowledge"], changed_source)
        coverage = knowledge.coverage_paths(current_knowledge, changed_source)
        wiki_changes = knowledge.changed_knowledge_paths(
            state["base_knowledge"], current_knowledge
        )
        if disposition == "no-update":
            reasons: list[str] = []
            if state.get("knowledge_profile") == "bootstrap":
                reasons.append("bootstrap work must promote knowledge")
            if affected:
                reasons.append("affected Wiki pages require refresh or delete")
            if wiki_changes:
                reasons.append("Wiki already has work-item changes")
            if reasons:
                raise ValidationError(
                    "Knowledge no-update review is not allowed.",
                    {
                        "reasons": reasons,
                        "affected_pages": affected,
                        "changed_pages": wiki_changes,
                    },
                )
        review = {
            "disposition": disposition,
            "rationale": rationale.strip(),
            "affected_pages": affected[:50],
            "covered_changed_paths": coverage["covered"][:50],
            "uncovered_changed_paths": coverage["uncovered"][:50],
            "change_fingerprint": current_source["fingerprint"],
            "recorded_at": utc_now(),
            "invalidated_at": None,
        }
        state["knowledge_review"] = review
        state["knowledge_updates"] = _empty_knowledge_updates()
        save_state_unlocked(repo, state)
        append_event_unlocked(repo, work_id, "knowledge_review_set", review)
        return review


def set_knowledge_context(
    repo: Path,
    work_id: str,
    pages: Sequence[str],
    gaps: Sequence[str] = (),
) -> dict[str, Any]:
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if "base_knowledge" not in state:
            raise ValidationError(
                "This legacy work item does not require a retrospective knowledge context."
            )
        if state["phase"] not in ("requirements", "scope_review"):
            raise ValidationError(
                "Knowledge context is read-only after G1.", {"phase": state["phase"]}
            )
        project = load_project(repo)
        root = project["knowledge"]["root"]
        normalized: list[str] = []
        try:
            for page in pages:
                value = knowledge.normalize_page(page, root)
                if value not in normalized:
                    normalized.append(value)
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        if not normalized or len(normalized) > 6:
            raise ValidationError(
                "Knowledge context must contain wiki/index.md and at most five related pages.",
                {"pages": normalized},
            )
        expected_index = f"{root}/index.md"
        if normalized[0] != expected_index:
            raise ValidationError(
                "Knowledge context must record wiki/index.md first.",
                {"expected": expected_index, "pages": normalized},
            )
        cleaned_gaps = [item.strip() for item in gaps if item.strip()]
        if len(cleaned_gaps) != len(gaps) or len(cleaned_gaps) > 20 or any(
            len(item) > 500 for item in cleaned_gaps
        ):
            raise ValidationError("Knowledge gaps must be non-empty and at most 500 characters each.")
        try:
            snapshot = knowledge.knowledge_snapshot(repo, root=root)
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        nonfresh = []
        for page in normalized:
            record = snapshot.get("pages", {}).get(page)
            if (
                not record
                or record.get("status") != "active"
                or record.get("parse_errors")
                or record.get("source_error")
                or record.get("source_fingerprint")
                != record.get("computed_source_fingerprint")
            ):
                nonfresh.append(page)
        if nonfresh and not cleaned_gaps:
            raise ValidationError(
                "Missing, placeholder, stale, or invalid Wiki pages require a recorded gap.",
                {"pages": nonfresh},
            )
        state["knowledge_context"] = {
            "pages": normalized,
            "records": knowledge.context_records(snapshot, normalized),
            "gaps": cleaned_gaps,
            "recorded_at": utc_now(),
        }
        save_state_unlocked(repo, state)
        append_event_unlocked(
            repo, work_id, "knowledge_context_set", state["knowledge_context"]
        )
        return state["knowledge_context"]


def set_knowledge_plan(
    repo: Path,
    work_id: str,
    upserts: Sequence[str],
    deletes: Sequence[str],
    rationale: str,
) -> dict[str, Any]:
    if not rationale.strip():
        raise ValidationError("Knowledge plan rationale must not be empty.")
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if "base_knowledge" not in state:
            raise ValidationError(
                "This legacy work item does not require a retrospective knowledge plan."
            )
        if state["gates"]["build"].get("status") != "approved" or state["phase"] not in (
            "verification",
            "acceptance_review",
        ):
            raise ValidationError(
                "Knowledge promotion may be planned only during verification or acceptance.",
                {"phase": state["phase"]},
            )
        current_source = git_snapshot(repo)
        if state.get("knowledge_review_required"):
            review = state.get("knowledge_review", {})
            if not (
                isinstance(review, dict)
                and review.get("disposition") == "promote"
                and review.get("recorded_at")
                and review.get("invalidated_at") is None
                and review.get("change_fingerprint")
                == current_source["fingerprint"]
            ):
                raise ValidationError(
                    "A current promote knowledge review is required before planning Wiki updates."
                )
        project = load_project(repo)
        root = project["knowledge"]["root"]
        try:
            normalized_upserts = sorted(
                {knowledge.normalize_page(page, root) for page in upserts}
            )
            normalized_deletes = sorted(
                {knowledge.normalize_page(page, root) for page in deletes}
            )
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        special = {f"{root}/index.md", f"{root}/log.md"}
        if special.intersection(normalized_upserts) or special.intersection(
            normalized_deletes
        ):
            raise ValidationError(
                "wiki/index.md and wiki/log.md are coupled automatically; do not list them as content targets."
            )
        overlap = sorted(set(normalized_upserts) & set(normalized_deletes))
        if overlap:
            raise ValidationError(
                "A Wiki page cannot be both upserted and deleted.", {"pages": overlap}
            )
        content_count = len(normalized_upserts) + len(normalized_deletes)
        if state.get("knowledge_review_required") and not 1 <= content_count <= 5:
            raise ValidationError(
                "A promote knowledge plan must declare between one and five content targets.",
                {"count": content_count},
            )
        if content_count > 5:
            raise ValidationError(
                "A knowledge plan may declare at most five content targets.",
                {"count": content_count},
            )
        unknown_deletes = sorted(
            set(normalized_deletes) - set(state["base_knowledge"].get("pages", {}))
        )
        if unknown_deletes:
            raise ValidationError(
                "Knowledge delete targets must exist in the work-item base snapshot.",
                {"pages": unknown_deletes},
            )
        coupled = sorted(special) if normalized_upserts or normalized_deletes else []
        state["knowledge_updates"] = {
            "upserts": normalized_upserts,
            "deletes": normalized_deletes,
            "coupled": coupled,
            "rationale": rationale.strip(),
            "sealed": [],
            "change_fingerprint": current_source["fingerprint"],
            "recorded_at": utc_now(),
        }
        save_state_unlocked(repo, state)
        append_event_unlocked(
            repo, work_id, "knowledge_plan_set", state["knowledge_updates"]
        )
        return state["knowledge_updates"]


def scaffold_knowledge(
    repo: Path,
    work_id: str,
    *,
    page: str,
    page_type: str,
    title: str,
    sources: Sequence[str],
    package_name: str | None = None,
    version: str | None = None,
    decision_date: str | None = None,
    decision_status: str | None = None,
) -> dict[str, Any]:
    """Create one planned new Wiki page from its canonical template."""

    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if "base_knowledge" not in state:
            raise ValidationError(
                "Legacy work items do not have a knowledge scaffold contract."
            )
        if state["gates"]["build"].get("status") != "approved" or state[
            "phase"
        ] not in ("verification", "acceptance_review"):
            raise ValidationError(
                "Knowledge scaffold requires current G2 approval and verification phase.",
                {"phase": state["phase"]},
            )
        current_source = git_snapshot(repo)
        if state.get("knowledge_review_required"):
            review = state.get("knowledge_review", {})
            if not (
                isinstance(review, dict)
                and review.get("disposition") == "promote"
                and review.get("recorded_at")
                and review.get("invalidated_at") is None
                and review.get("change_fingerprint")
                == current_source["fingerprint"]
            ):
                raise ValidationError(
                    "A current promote knowledge review is required before scaffolding."
                )
        project = load_project(repo)
        root = project["knowledge"]["root"]
        try:
            normalized_page = knowledge.normalize_page(page, root)
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        updates = state.get("knowledge_updates", {})
        if updates.get("change_fingerprint") != current_source["fingerprint"]:
            raise ValidationError(
                "A current knowledge plan is required before scaffolding."
            )
        if normalized_page not in set(updates.get("upserts", [])):
            raise ValidationError(
                "Knowledge scaffold target must be a planned upsert.",
                {"page": normalized_page},
            )
        if normalized_page in state["base_knowledge"].get("pages", {}):
            raise ValidationError(
                "Knowledge scaffold is only for new planned pages and cannot overwrite existing pages.",
                {"page": normalized_page},
            )
        try:
            result = knowledge.scaffold_page(
                repo,
                assets_root(),
                page=normalized_page,
                page_type=page_type,
                title=title,
                sources=sources,
                work_id=work_id,
                package_name=package_name,
                version=version,
                decision_date=decision_date,
                decision_status=decision_status,
                root=root,
            )
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        append_event_unlocked(
            repo,
            work_id,
            "knowledge_page_scaffolded",
            result,
        )
        return result


def seal_knowledge(
    repo: Path,
    work_id: str,
    pages: Sequence[str],
) -> dict[str, Any]:
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if "base_knowledge" not in state:
            raise ValidationError("Legacy work items do not have a knowledge seal ledger.")
        if state["phase"] not in ("verification", "acceptance_review"):
            raise ValidationError(
                "Knowledge pages may be sealed only during verification or acceptance.",
                {"phase": state["phase"]},
            )
        project = load_project(repo)
        root = project["knowledge"]["root"]
        try:
            normalized = sorted({knowledge.normalize_page(page, root) for page in pages})
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        updates = state.get("knowledge_updates", {})
        allowed = set(updates.get("upserts", [])) | set(updates.get("coupled", []))
        unauthorized = sorted(set(normalized) - allowed)
        if not normalized or unauthorized:
            raise ValidationError(
                "Knowledge seal pages must be planned upserts or coupled index/log pages.",
                {"unauthorized": unauthorized},
            )
        try:
            sealed_records = knowledge.seal_pages(
                repo, normalized, work_id, root=root
            )
        except knowledge.KnowledgeError as exc:
            _raise_knowledge(exc)
        updates["sealed"] = sorted(set(updates.get("sealed", [])) | set(normalized))
        state["knowledge_updates"] = updates
        save_state_unlocked(repo, state)
        append_event_unlocked(
            repo,
            work_id,
            "knowledge_pages_sealed",
            {"pages": normalized, "records": sealed_records},
        )
        return {"pages": sealed_records, "knowledge_updates": updates}


def add_waiver(
    repo: Path,
    work_id: str,
    kind: str,
    target: str,
    reason: str,
    actor: str | None = None,
    gate: str | None = None,
) -> dict[str, Any]:
    if not reason.strip():
        raise ValidationError("Waiver reason must not be empty.")
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        resolved_gate = gate or WAIVER_GATES.get(kind) or _current_gate_for_phase(
            state.get("phase", "")
        )
        if resolved_gate not in GATES:
            raise ValidationError(
                "Waiver gate must be explicit outside a gate-review phase.",
                {"gate": resolved_gate, "allowed": list(GATES)},
            )
        if kind == "review-critical":
            if resolved_gate != "acceptance":
                raise ValidationError(
                    "review-critical waivers are valid only for the acceptance gate."
                )
            if not re.fullmatch(r"F-\d{3}", target.strip()):
                raise ValidationError(
                    "review-critical waivers require one named finding ID target.",
                    {"target": target},
                )
        waiver = {
            "schema_version": SCHEMA_VERSION,
            "id": f"WAIVER-{len(state.get('waivers', [])) + 1:03d}",
            "kind": kind,
            "target": target,
            "reason": reason.strip(),
            "gate": resolved_gate,
            "approved_by": _actor(repo, actor),
            "approved_at": utc_now(),
        }
        state.setdefault("waivers", []).append(waiver)
        save_state_unlocked(repo, state)
        append_event_unlocked(repo, work_id, "waiver_added", waiver)
        return waiver


def update_task(
    repo: Path,
    work_id: str,
    task_id: str,
    action: str,
    evidence: Sequence[str] = (),
    note: str = "",
) -> dict[str, Any]:
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if state["gates"]["build"].get("status") != "approved":
            raise ValidationError("Tasks require a current G2 build approval.")
        if task_id not in state.get("tasks", {}):
            raise ValidationError("Unknown task.", {"task": task_id})
        task = state["tasks"][task_id]
        if action == "start":
            if task["status"] not in ("pending", "blocked"):
                raise ValidationError(
                    "Only pending or blocked tasks can start.",
                    {"task": task_id, "status": task["status"]},
                )
            plan_blocks = _heading_blocks(_read_artifact(repo, state, "plan.md"))
            dependencies = _task_dependency_graph(plan_blocks).get(task_id, [])
            incomplete_dependencies = [
                dependency
                for dependency in dependencies
                if state["tasks"].get(dependency, {}).get("status") != "completed"
            ]
            if incomplete_dependencies:
                raise ValidationError(
                    "Task dependencies are not complete.",
                    {"task": task_id, "dependencies": incomplete_dependencies},
                )
            task.update({"status": "in_progress", "started_at": utc_now()})
            state["phase"] = "implementation"
            state["blocker"] = None
        elif action == "complete":
            if task["status"] != "in_progress":
                raise ValidationError(
                    "A task must be in progress before completion.",
                    {"task": task_id, "status": task["status"]},
                )
            unknown = [item for item in evidence if item not in state.get("evidence", {})]
            if unknown:
                raise ValidationError("Unknown evidence IDs.", {"evidence": unknown})
            if not evidence and not note.strip():
                raise ValidationError("Task completion requires evidence or a completion note.")
            task.update(
                {
                    "status": "completed",
                    "completed_at": utc_now(),
                    "evidence": sorted(set(evidence)),
                    "note": note.strip(),
                }
            )
            if all(
                item.get("status") == "completed"
                for item in state["tasks"].values()
            ):
                state["phase"] = "verification"
        elif action == "block":
            if not note.strip():
                raise ValidationError("Blocking a task requires a reason.")
            if task["status"] not in ("pending", "in_progress", "blocked"):
                raise ValidationError(
                    "Only pending, in-progress, or blocked tasks can be blocked.",
                    {"task": task_id, "status": task["status"]},
                )
            task.update({"status": "blocked", "note": note.strip()})
            state["blocker"] = {"task": task_id, "reason": note.strip(), "at": utc_now()}
        else:
            raise ValidationError("Unknown task action.", {"action": action})
        save_state_unlocked(repo, state)
        append_event_unlocked(
            repo,
            work_id,
            f"task_{action}",
            {"task": task_id, "evidence": list(evidence), "note": note.strip()},
        )
        return task


def _next_evidence_id(state: dict[str, Any]) -> str:
    numbers = [
        int(item.split("-")[1])
        for item in state.get("evidence", {})
        if re.fullmatch(r"EVID-\d{3}", item)
    ]
    next_number = max(numbers, default=0) + 1
    if next_number > 999:
        raise ValidationError("Evidence ID space is exhausted for this work item.")
    return f"EVID-{next_number:03d}"


def _redact(text: str) -> str:
    pattern = re.compile(
        r"(?i)\b(api[_-]?key|token|password|secret)\b(\s*[:=]\s*)([^\s]+)"
    )
    return pattern.sub(r"\1\2[REDACTED]", text)


def _review_report_path(repo: Path, work_id: str, report_file: str | Path) -> Path:
    if not isinstance(report_file, (str, Path)) or not str(report_file).strip():
        raise ValidationError("Review report file is required.")
    relative = Path(report_file)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError(
            "Review report file must be repo-relative and cannot contain '..'.",
            {"report_file": str(report_file)},
        )
    candidate = ensure_within(repo, repo / relative)
    incoming = ensure_within(
        repo,
        devweave_root(repo) / "cache" / "incoming" / work_id,
    )
    try:
        candidate.relative_to(incoming)
    except ValueError as exc:
        raise ValidationError(
            "Review report file must stay inside the work-item incoming cache.",
            {"report_file": normalize_relpath(report_file)},
        ) from exc
    if not candidate.is_file():
        raise ValidationError(
            "Review report file is missing or is not a file.",
            {"report_file": normalize_relpath(report_file)},
        )
    return candidate


def _review_log_path(repo: Path, work_id: str, evidence_id: str) -> Path:
    cache_root = ensure_within(repo, devweave_root(repo) / "cache")
    logs_root = ensure_within(cache_root, cache_root / "logs")
    work_logs = ensure_within(logs_root, logs_root / work_id)
    return ensure_within(work_logs, work_logs / f"{evidence_id}.log")


def _review_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Review report field '{field}' must be a non-empty string.")
    normalized = value.strip()
    if len(normalized) > REVIEW_MAX_TEXT_CHARS:
        raise ValidationError(
            f"Review report field '{field}' is too large.",
            {"field": field, "max_chars": REVIEW_MAX_TEXT_CHARS},
        )
    return _redact(normalized)


def _load_review_report(
    repo: Path,
    state: dict[str, Any],
    report_file: str | Path,
    source: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    path = _review_report_path(repo, state["id"], report_file)
    project = load_project(repo)
    try:
        limit = int(project.get("evidence", {}).get("raw_log_limit_bytes", MAX_RAW_LOG_BYTES))
    except (TypeError, ValueError) as exc:
        raise ValidationError("Project evidence raw_log_limit_bytes must be an integer.") from exc
    if limit <= 0:
        raise ValidationError("Project evidence raw_log_limit_bytes must be greater than zero.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError("Review report file could not be read.", {"path": str(path)}) from exc
    if len(raw) > limit:
        raise ValidationError(
            "Review report exceeds the configured raw log limit.",
            {"bytes": len(raw), "limit": limit},
        )
    try:
        text = raw.decode("utf-8")
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("Review report must be valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise ValidationError("Review report must be a JSON object.")
    required = {
        "result",
        "severity",
        "summary",
        "source_fingerprint",
        "covers",
        "tasks",
        "findings",
    }
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing or extra:
        raise ValidationError(
            "Review report fields do not match the fixed envelope.",
            {"missing": missing, "unknown": extra},
        )
    result = value.get("result")
    severity = value.get("severity")
    if result not in REVIEW_RESULTS:
        raise ValidationError(
            "Review report result is invalid.",
            {"result": result, "allowed": list(REVIEW_RESULTS)},
        )
    if severity not in REVIEW_SEVERITIES:
        raise ValidationError(
            "Review report severity is invalid.",
            {"severity": severity, "allowed": list(REVIEW_SEVERITIES)},
        )
    summary = _review_text(value.get("summary"), "summary")
    fingerprint = value.get("source_fingerprint")
    if not isinstance(fingerprint, str) or fingerprint != source["fingerprint"]:
        raise ValidationError(
            "Review report source fingerprint is not current.",
            {"reported": fingerprint, "current": source["fingerprint"]},
        )
    covers = value.get("covers")
    tasks = value.get("tasks")
    if not isinstance(covers, list) or not all(isinstance(item, str) for item in covers):
        raise ValidationError("Review report covers must be a string array.")
    if not isinstance(tasks, list) or not all(isinstance(item, str) for item in tasks):
        raise ValidationError("Review report tasks must be a string array.")
    covers = sorted(set(covers))
    tasks = sorted(set(tasks))
    _validate_evidence_id_syntax(covers, tasks)
    requirement_blocks = _heading_blocks(_read_artifact(repo, state, "requirements.md"))
    plan_blocks = _heading_blocks(_read_artifact(repo, state, "plan.md"))
    known_acceptance = {item for item in requirement_blocks if item.startswith("AC-")}
    known_tasks = {item for item in plan_blocks if item.startswith("TASK-")}
    unknown_covers = sorted(set(covers) - known_acceptance)
    unknown_tasks = sorted(set(tasks) - known_tasks)
    if unknown_covers or unknown_tasks:
        raise ValidationError(
            "Review report contains unknown AC/TASK coverage.",
            {"unknown_covers": unknown_covers, "unknown_tasks": unknown_tasks},
        )

    findings_value = value.get("findings")
    if not isinstance(findings_value, list) or len(findings_value) > REVIEW_MAX_FINDINGS:
        raise ValidationError(
            "Review report findings must be a bounded array.",
            {"max_findings": REVIEW_MAX_FINDINGS},
        )
    findings: list[dict[str, str]] = []
    finding_ids: set[str] = set()
    for finding in findings_value:
        if not isinstance(finding, dict):
            raise ValidationError("Each review finding must be an object.")
        finding_keys = {"id", "severity", "title", "evidence", "recommendation"}
        missing_finding = sorted(finding_keys - set(finding))
        extra_finding = sorted(set(finding) - finding_keys)
        if missing_finding or extra_finding:
            raise ValidationError(
                "Review finding fields do not match the fixed envelope.",
                {"missing": missing_finding, "unknown": extra_finding},
            )
        finding_id = finding.get("id")
        if not isinstance(finding_id, str) or not re.fullmatch(r"F-\d{3}", finding_id):
            raise ValidationError("Review findings require an ID such as F-001.")
        if finding_id in finding_ids:
            raise ValidationError("Review finding IDs must be unique.", {"id": finding_id})
        finding_ids.add(finding_id)
        finding_severity = finding.get("severity")
        if finding_severity not in ("advisory", "critical"):
            raise ValidationError(
                "Review finding severity must be advisory or critical.",
                {"id": finding_id},
            )
        findings.append(
            {
                "id": finding_id,
                "severity": finding_severity,
                "title": _review_text(finding.get("title"), f"{finding_id}.title"),
                "evidence": _review_text(finding.get("evidence"), f"{finding_id}.evidence"),
                "recommendation": _review_text(
                    finding.get("recommendation"), f"{finding_id}.recommendation"
                ),
            }
        )
    critical_findings = [item for item in findings if item["severity"] == "critical"]
    if result == "passed" and (severity == "critical" or critical_findings):
        raise ValidationError("A passed review cannot contain critical findings.")
    if result == "unavailable" and (severity != "none" or findings):
        raise ValidationError("An unavailable review must have none severity and no findings.")
    if result == "critical" and (severity != "critical" or not critical_findings):
        raise ValidationError("A critical review requires at least one critical finding.")
    sanitized = {
        "result": result,
        "severity": severity,
        "summary": summary,
        "source_fingerprint": source["fingerprint"],
        "covers": covers,
        "tasks": tasks,
        "findings": findings,
    }
    stored = canonical_json(sanitized)
    if len(stored) > limit:
        raise ValidationError(
            "Redacted review report exceeds the configured raw log limit.",
            {"bytes": len(stored), "limit": limit},
        )
    return sanitized, stored


def _write_evidence_unlocked(
    repo: Path,
    state: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    state.setdefault("evidence", {})[evidence["id"]] = evidence
    atomic_write_json(
        work_root(repo, state["id"]) / "evidence" / f"{evidence['id']}.json",
        evidence,
    )
    save_state_unlocked(repo, state)
    append_event_unlocked(repo, state["id"], "evidence_added", evidence)


def record_review(
    repo: Path,
    work_id: str,
    *,
    reviewer_id: str,
    report_file: str | Path,
) -> dict[str, Any]:
    reviewer_id = _review_text(reviewer_id, "reviewer_id")
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if state.get("risk", {}).get("level") != "high":
            raise ValidationError(
                "Independent review record is available only for high-risk work."
            )
        if state.get("phase") not in ("verification", "acceptance_review"):
            raise ValidationError(
                "Independent review may be recorded only during G3 verification or acceptance review.",
                {"phase": state.get("phase")},
            )
        source = git_snapshot(repo)
        report, stored_report = _load_review_report(repo, state, report_file, source)
        evidence_id = _next_evidence_id(state)
        log_path = _review_log_path(repo, work_id, evidence_id)
        atomic_write_bytes(log_path, stored_report)
        result = report["result"]
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "id": evidence_id,
            "kind": "review",
            "status": "passed" if result == "passed" else "failed",
            "summary": report["summary"],
            "covers": report["covers"],
            "tasks": report["tasks"],
            "observed_result": (
                "success" if result == "passed" else "failure" if result == "critical" else "neutral"
            ),
            "source_fingerprint": source["fingerprint"],
            "git_head": source["head"],
            "created_at": utc_now(),
            "stale": False,
            "binds_current_source": True,
            "command_id": None,
            "exit_code": None,
            "expectation": None,
            "raw_log": normalize_relpath(log_path.relative_to(repo)),
            "log_truncated": False,
            "review": {
                "result": result,
                "severity": report["severity"],
                "reviewer_id": reviewer_id,
                "context_mode": REVIEW_CONTEXT_MODE,
                "report_sha256": sha256_bytes(stored_report),
                "findings": report["findings"],
                "covers": report["covers"],
                "tasks": report["tasks"],
            },
        }
        _write_evidence_unlocked(repo, state, evidence)
        append_event_unlocked(
            repo,
            work_id,
            "review_recorded",
            {
                "evidence_id": evidence_id,
                "result": result,
                "severity": report["severity"],
                "reviewer_id": reviewer_id,
                "report_sha256": evidence["review"]["report_sha256"],
            },
        )
        if evidence["status"] == "passed":
            state["last_verification"] = {
                "evidence_id": evidence_id,
                "source_fingerprint": source["fingerprint"],
                "at": utc_now(),
            }
            save_state_unlocked(repo, state)
        return evidence


def add_evidence(
    repo: Path,
    work_id: str,
    *,
    kind: str,
    status: str,
    summary: str,
    covers: Sequence[str] = (),
    tasks: Sequence[str] = (),
    observed_result: str = "neutral",
    binds_current_source: bool | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if kind == "review":
        raise ValidationError(
            "Review evidence must be recorded through the machine-only review record interface."
        )
    _validate_evidence_id_syntax(covers, tasks)
    if status not in ("passed", "failed", "waived"):
        raise ValidationError("Unknown evidence status.", {"status": status})
    if observed_result not in ("success", "failure", "neutral"):
        raise ValidationError(
            "Unknown observed result.", {"observed_result": observed_result}
        )
    if not summary.strip():
        raise ValidationError("Evidence summary must not be empty.")
    normalized_metrics = normalize_evidence_metrics(metrics)
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        evidence_id = _next_evidence_id(state)
        source = git_snapshot(repo)
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "id": evidence_id,
            "kind": kind,
            "status": status,
            "summary": _redact(summary.strip()),
            "covers": sorted(set(covers)),
            "tasks": sorted(set(tasks)),
            "observed_result": observed_result,
            "source_fingerprint": source["fingerprint"],
            "git_head": source["head"],
            "created_at": utc_now(),
            "stale": False,
            "binds_current_source": (
                kind not in ("reproduction", "baseline")
                if binds_current_source is None
                else binds_current_source
            ),
            "command_id": None,
            "exit_code": None,
            "expectation": None,
            "raw_log": None,
            "log_truncated": False,
        }
        if normalized_metrics is not None:
            evidence["metrics"] = normalized_metrics
        _write_evidence_unlocked(repo, state, evidence)
        if evidence["status"] == "passed" and evidence["binds_current_source"]:
            state["last_verification"] = {
                "evidence_id": evidence_id,
                "source_fingerprint": source["fingerprint"],
                "at": utc_now(),
            }
            save_state_unlocked(repo, state)
        return evidence


def _command_by_id(project: dict[str, Any], command_id: str) -> dict[str, Any]:
    matches = [item for item in project.get("commands", []) if item.get("id") == command_id]
    if len(matches) != 1:
        raise ValidationError(
            "Verification command is missing or duplicated.",
            {"command": command_id, "matches": len(matches)},
        )
    command = matches[0]
    argv = command.get("argv")
    if not isinstance(argv, list) or not argv or not all(
        isinstance(item, str) and item for item in argv
    ):
        raise ValidationError(
            "Verification command argv must be a non-empty string array.",
            {"command": command_id},
        )
    return command


def _verification_command(
    repo: Path, project: dict[str, Any], command_id: str
) -> tuple[dict[str, Any], Path, int]:
    command = _command_by_id(project, command_id)
    cwd = ensure_within(repo, repo / command.get("cwd", "."))
    timeout = int(command.get("timeout_seconds", 900))
    if timeout <= 0:
        raise ValidationError(
            "Verification command timeout must be greater than zero.",
            {"command": command_id, "timeout_seconds": timeout},
        )
    if not cwd.is_dir():
        raise ValidationError(
            "Verification command cwd must be an existing directory.",
            {"command": command_id, "cwd": str(cwd)},
        )
    return command, cwd, timeout


def _as_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")


def _execute_verification_command(
    command: dict[str, Any], cwd: Path, timeout: int
) -> dict[str, Any]:
    started_at = utc_now()
    started_monotonic = time.monotonic()
    timed_out = False
    execution_error: str | None = None
    try:
        result = subprocess.run(
            command["argv"],
            cwd=cwd,
            capture_output=True,
            shell=False,
            timeout=timeout,
            check=False,
        )
        exit_code: int | None = result.returncode
        stdout = _as_bytes(result.stdout)
        stderr = _as_bytes(result.stderr)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = _as_bytes(exc.stdout)
        stderr = _as_bytes(exc.stderr)
    except OSError as exc:
        exit_code = None
        stdout = b""
        stderr = str(exc).encode("utf-8", errors="replace")
        execution_error = f"{type(exc).__name__}: {exc}"
    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "execution_error": execution_error,
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_ms": int((time.monotonic() - started_monotonic) * 1000),
    }


def _record_verification_execution(
    repo: Path,
    work_id: str,
    *,
    project: dict[str, Any],
    command_id: str,
    command: dict[str, Any],
    execution: dict[str, Any],
    source: dict[str, Any],
    kind: str,
    covers: Sequence[str],
    tasks: Sequence[str],
    expectation: str,
    batch_id: str | None = None,
    batch_index: int | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    exit_code = execution["exit_code"]
    timed_out = execution["timed_out"]
    stdout = execution["stdout"]
    stderr = execution["stderr"]
    expectation_met = (
        (expectation == "any" and exit_code is not None)
        or (expectation == "zero" and exit_code == 0)
        or (expectation == "nonzero" and exit_code not in (None, 0))
    )
    raw = (
        b"STDOUT\n"
        + stdout
        + b"\nSTDERR\n"
        + stderr
        + (b"\nTIMED OUT\n" if timed_out else b"")
    )
    limit = int(project.get("evidence", {}).get("raw_log_limit_bytes", MAX_RAW_LOG_BYTES))
    truncated = len(raw) > limit
    stored_raw = raw[-limit:] if truncated else raw
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        evidence_id = _next_evidence_id(state)
        log_path = devweave_root(repo) / "cache" / "logs" / work_id / f"{evidence_id}.log"
        atomic_write_bytes(log_path, stored_raw)
        tail = (stdout + b"\n" + stderr)[-4000:].decode("utf-8", errors="replace")
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "id": evidence_id,
            "kind": kind,
            "status": "passed" if expectation_met and not timed_out else "failed",
            "summary": _redact(tail.strip() or f"{command_id} produced no output."),
            "covers": sorted(set(covers)),
            "tasks": sorted(set(tasks)),
            "observed_result": "failure" if exit_code != 0 else "success",
            "source_fingerprint": source["fingerprint"],
            "git_head": source["head"],
            "created_at": utc_now(),
            "started_at": execution["started_at"],
            "finished_at": execution["finished_at"],
            "duration_ms": execution["duration_ms"],
            "stale": False,
            "binds_current_source": kind not in ("reproduction", "baseline"),
            "command_id": command_id,
            "argv": command["argv"],
            "cwd": normalize_relpath(command.get("cwd", ".")),
            "exit_code": exit_code,
            "expectation": expectation,
            "timed_out": timed_out,
            "execution_error": execution["execution_error"],
            "raw_log": normalize_relpath(log_path.relative_to(repo)),
            "log_truncated": truncated,
        }
        if batch_id is not None:
            evidence["verification_batch_id"] = batch_id
            evidence["verification_batch_index"] = batch_index
        metrics_with_duration = dict(metrics or {})
        metrics_with_duration["duration_ms"] = execution["duration_ms"]
        normalized_metrics = normalize_evidence_metrics(metrics_with_duration) or {}
        verification_metrics = normalized_metrics.setdefault("verification", {})
        if batch_id is None:
            verification_metrics.update(
                {
                    "selected": 1,
                    "skipped": 0,
                    "dependency_closure_added": 0,
                    "cache_hit": False,
                }
            )
        else:
            verification_metrics.setdefault("selected", 1)
            verification_metrics.setdefault("skipped", 0)
            verification_metrics.setdefault("dependency_closure_added", 0)
            verification_metrics.setdefault("cache_hit", False)
        evidence["metrics"] = normalized_metrics
        _write_evidence_unlocked(repo, state, evidence)
        if evidence["status"] == "passed" and evidence["binds_current_source"]:
            state["last_verification"] = {
                "evidence_id": evidence_id,
                "source_fingerprint": source["fingerprint"],
                "at": utc_now(),
            }
            if state["phase"] == "implementation" and all(
                item.get("status") == "completed"
                for item in state.get("tasks", {}).values()
            ):
                state["phase"] = "verification"
            save_state_unlocked(repo, state)
        return evidence


def run_verification(
    repo: Path,
    work_id: str,
    *,
    command_id: str,
    kind: str,
    covers: Sequence[str] = (),
    tasks: Sequence[str] = (),
    expectation: str = "zero",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if kind == "review":
        raise ValidationError(
            "Review evidence must be recorded through the machine-only review record interface."
        )
    _validate_evidence_id_syntax(covers, tasks)
    if expectation not in ("zero", "nonzero", "any"):
        raise ValidationError("Unknown exit expectation.", {"expectation": expectation})
    if metrics is not None:
        metrics = normalize_evidence_metrics(metrics)
    project = load_project(repo)
    command, cwd, timeout = _verification_command(repo, project, command_id)
    execution = _execute_verification_command(command, cwd, timeout)
    source = git_snapshot(repo)
    return _record_verification_execution(
        repo,
        work_id,
        project=project,
        command_id=command_id,
        command=command,
        execution=execution,
        source=source,
        kind=kind,
        covers=covers,
        tasks=tasks,
        expectation=expectation,
        metrics=metrics,
    )


def _verification_profile_commands(
    repo: Path,
    project: dict[str, Any],
    profile: str,
    changed_paths: Sequence[str] | None = None,
) -> tuple[list[str], dict[str, tuple[dict[str, Any], Path, int]], dict[str, Any]]:
    if profile not in RISK_LEVELS:
        raise ValidationError("Unknown verification profile.", {"profile": profile})
    configured_ids = list(project.get("verification_profiles", {}).get(profile, []))
    command_ids = list(configured_ids)
    if len(command_ids) != len(set(command_ids)):
        raise ValidationError("Verification profile contains duplicate command IDs.", {"profile": profile})
    prepared = {
        command_id: _verification_command(repo, project, command_id)
        for command_id in command_ids
    }
    skipped: list[dict[str, str]] = []
    selection_mode = "full"
    if changed_paths is not None:
        selection_mode = "affected-paths"
        normalized_paths = _normalize_verification_paths(changed_paths)
        high_profile = profile == "high"
        if not high_profile:
            retained: list[str] = []
            for command_id in configured_ids:
                command = prepared[command_id][0]
                if command.get("release_only"):
                    skipped.append(
                        {"command_id": command_id, "reason": "release-only"}
                    )
                elif not _command_metadata_present(command):
                    skipped.append(
                        {"command_id": command_id, "reason": "legacy-unclassified"}
                    )
                elif not _command_matches_paths(command, normalized_paths):
                    skipped.append(
                        {"command_id": command_id, "reason": "no-affected-path-intersection"}
                    )
                else:
                    retained.append(command_id)
            command_ids = retained
            prepared = {command_id: prepared[command_id] for command_id in command_ids}
        # High profile is intentionally a full set even when paths are given.
        # Keep the metadata in the batch so callers can see that path filtering
        # was requested but policy did not reduce coverage.
    elif profile != "high":
        retained = []
        for command_id in command_ids:
            command = prepared[command_id][0]
            if command.get("release_only"):
                skipped.append({"command_id": command_id, "reason": "release-only"})
            else:
                retained.append(command_id)
        command_ids = retained
        prepared = {command_id: prepared[command_id] for command_id in command_ids}
    if profile != "high":
        # A non-high selection must never resurrect a release-only command via
        # dependency closure. Resolve the complete dependency graph first so a
        # release-only command nested more than one level deep is handled just
        # like a direct dependency.
        command_cache: dict[str, dict[str, Any]] = {}
        for command_id in configured_ids:
            if command_id in prepared:
                command_cache[command_id] = prepared[command_id][0]
            else:
                command_cache[command_id] = _verification_command(
                    repo, project, command_id
                )[0]
        release_dependency_cache: dict[str, str | None] = {}
        release_dependency_visiting: set[str] = set()

        def command_for_dependency(command_id: str) -> dict[str, Any]:
            command = command_cache.get(command_id)
            if command is None:
                command, _cwd, _timeout = _verification_command(
                    repo, project, command_id
                )
                command_cache[command_id] = command
            return command

        def release_only_dependency(command_id: str) -> str | None:
            if command_id in release_dependency_cache:
                return release_dependency_cache[command_id]
            if command_id in release_dependency_visiting:
                raise ValidationError(
                    "Verification command dependencies contain a cycle.",
                    {"command": command_id},
                )
            release_dependency_visiting.add(command_id)
            result: str | None = None
            for dependency in command_for_dependency(command_id).get("depends_on", []):
                dependency_command = command_for_dependency(dependency)
                if dependency_command.get("release_only"):
                    result = dependency
                    break
                result = release_only_dependency(dependency)
                if result is not None:
                    break
            release_dependency_visiting.remove(command_id)
            release_dependency_cache[command_id] = result
            return result

        release_blocked: set[str] = set()
        for command_id in list(command_ids):
            dependency = release_only_dependency(command_id)
            if dependency is not None:
                release_blocked.add(command_id)
                skipped.append(
                    {
                        "command_id": command_id,
                        "reason": f"release-only-dependency:{dependency}",
                    }
                )
        if release_blocked:
            command_ids = [
                command_id
                for command_id in command_ids
                if command_id not in release_blocked
            ]
            prepared = {
                command_id: prepared[command_id] for command_id in command_ids
            }
    selected = set(command_ids)
    closure_added: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def add_dependency(command_id: str) -> None:
        if command_id in visiting:
            raise ValidationError(
                "Verification command dependencies contain a cycle.",
                {"command": command_id},
            )
        if command_id in visited:
            return
        visiting.add(command_id)
        command, cwd, timeout = _verification_command(repo, project, command_id)
        prepared[command_id] = (command, cwd, timeout)
        for dependency in command.get("depends_on", []):
            if dependency not in selected:
                selected.add(dependency)
                command_ids.append(dependency)
                closure_added.append(dependency)
            add_dependency(dependency)
        visiting.remove(command_id)
        visited.add(command_id)

    for command_id in list(command_ids):
        add_dependency(command_id)
    # Dependencies are executed before their dependents. Preserve profile order
    # for independent commands while moving closure additions ahead of users.
    ordered: list[str] = []
    emitted: set[str] = set()

    def emit_dependencies(command_id: str) -> None:
        if command_id in emitted:
            return
        for dependency in prepared[command_id][0].get("depends_on", []):
            emit_dependencies(dependency)
        emitted.add(command_id)
        ordered.append(command_id)

    for command_id in list(command_ids):
        emit_dependencies(command_id)
    command_ids = ordered
    selected_after_closure = set(command_ids)
    skipped = [
        item for item in skipped if item["command_id"] not in selected_after_closure
    ]
    # A selective run may retain a command whose dependency is legacy/untyped;
    # dependency closure always wins over path filtering. High policy is kept
    # explicit in the returned selection metadata for reviewers.
    return command_ids, prepared, {
        "mode": selection_mode,
        "requested_paths": list(changed_paths or []),
        "selected": list(command_ids),
        "skipped": skipped,
        "dependency_closure_added": closure_added,
        "high_profile_full_set": profile == "high",
    }


def run_verification_profile(
    repo: Path,
    work_id: str,
    *,
    profile: str,
    kind: str,
    covers: Sequence[str] = (),
    tasks: Sequence[str] = (),
    expectation: str = "zero",
    max_parallel: int = 3,
    changed_paths: Sequence[str] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if kind == "review":
        raise ValidationError(
            "Review evidence must be recorded through the machine-only review record interface."
        )
    _validate_evidence_id_syntax(covers, tasks)
    if expectation not in ("zero", "nonzero", "any"):
        raise ValidationError("Unknown exit expectation.", {"expectation": expectation})
    if max_parallel <= 0:
        raise ValidationError("Verification max parallel must be greater than zero.")
    if metrics is not None:
        metrics = normalize_evidence_metrics(metrics)
    project = load_project(repo)
    command_ids, prepared, selection = _verification_profile_commands(
        repo, project, profile, changed_paths
    )
    selection_metrics = {
        "verification": {
            "selected": len(selection["selected"]),
            "skipped": len(selection["skipped"]),
            "dependency_closure_added": len(selection["dependency_closure_added"]),
            "cache_hit": False,
        }
    }
    if metrics is not None:
        normalized_input_metrics = normalize_evidence_metrics(metrics) or {}
        normalized_input_metrics["verification"] = {
            **dict(normalized_input_metrics.get("verification", {})),
            **selection_metrics["verification"],
        }
        metrics = normalized_input_metrics
    else:
        metrics = selection_metrics
    batch_id = f"VB-{uuid.uuid4().hex[:12]}"
    statuses: dict[str, str] = {command_id: "pending" for command_id in command_ids}
    records: dict[str, dict[str, Any]] = {}

    while True:
        for command_id in command_ids:
            if statuses[command_id] != "pending":
                continue
            dependencies = prepared[command_id][0].get("depends_on", [])
            blocked_by = [
                dependency
                for dependency in dependencies
                if statuses[dependency] in ("failed", "blocked")
            ]
            if blocked_by:
                statuses[command_id] = "blocked"
                records[command_id] = {
                    "command_id": command_id,
                    "status": "blocked",
                    "blocked_by": blocked_by,
                }

        pending = [command_id for command_id in command_ids if statuses[command_id] == "pending"]
        if not pending:
            break
        ready = [
            command_id
            for command_id in pending
            if all(statuses[dependency] == "passed" for dependency in prepared[command_id][0].get("depends_on", []))
        ]
        if not ready:
            raise ValidationError(
                "Verification profile cannot make progress.",
                {"profile": profile, "pending": pending},
            )
        selected: list[str] = []
        groups: set[str] = set()
        for command_id in ready:
            group = prepared[command_id][0].get("exclusive_group", "")
            if group and group in groups:
                continue
            selected.append(command_id)
            if group:
                groups.add(group)
            if len(selected) >= max_parallel:
                break

        executions: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=len(selected), thread_name_prefix="devweave-verify") as executor:
            futures = {
                command_id: executor.submit(
                    _execute_verification_command,
                    prepared[command_id][0],
                    prepared[command_id][1],
                    prepared[command_id][2],
                )
                for command_id in selected
            }
            for command_id, future in futures.items():
                executions[command_id] = future.result()

        source = git_snapshot(repo)
        for command_id in selected:
            command, _cwd, _timeout = prepared[command_id]
            evidence = _record_verification_execution(
                repo,
                work_id,
                project=project,
                command_id=command_id,
                command=command,
                execution=executions[command_id],
                source=source,
                kind=kind,
                covers=covers,
                tasks=tasks,
                expectation=expectation,
                batch_id=batch_id,
                batch_index=command_ids.index(command_id),
                metrics=metrics,
            )
            status = "passed" if evidence["status"] == "passed" else "failed"
            statuses[command_id] = status
            records[command_id] = {
                "command_id": command_id,
                "status": status,
                "duration_ms": evidence["duration_ms"],
                "evidence_id": evidence["id"],
                "evidence": evidence,
            }

    ordered_records = [records[command_id] for command_id in command_ids]
    ok = all(record["status"] == "passed" for record in ordered_records)
    return {
        "ok": ok,
        "work": work_id,
        "batch": {
            "id": batch_id,
            "profile": profile,
            "max_parallel": max_parallel,
            "selection": selection,
            "commands": ordered_records,
        },
    }


def revise_work(repo: Path, work_id: str, from_phase: str, reason: str) -> dict[str, Any]:
    if from_phase not in ("requirements", "design", "implementation"):
        raise ValidationError("Unknown revision phase.", {"phase": from_phase})
    if not reason.strip():
        raise ValidationError("Revision reason must not be empty.")
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        if state.get("status") == "closed":
            raise ValidationError("Closed work cannot be revised.")
        if from_phase == "requirements":
            gates = GATES
            phase = "requirements"
        elif from_phase == "design":
            gates = ("build", "acceptance")
            phase = "design"
        else:
            gates = ("acceptance",)
            phase = "implementation"
        for gate in gates:
            _mark_gate_stale(state["gates"][gate])
        state["phase"] = phase
        state["last_verification"] = None
        state["blocker"] = None
        for item in state.get("evidence", {}).values():
            if item.get("binds_current_source"):
                item["stale"] = True
        save_state_unlocked(repo, state)
        append_event_unlocked(
            repo,
            work_id,
            "revision_requested",
            {"from": from_phase, "reason": reason.strip()},
        )
        return state


def close_work(repo: Path, work_id: str) -> dict[str, Any]:
    with WorkLock(repo, work_id):
        state = load_state(repo, work_id)
        sync_state_unlocked(repo, state)
        if state.get("status") == "closed":
            return state
        gate = state["gates"]["acceptance"]
        current = acceptance_fingerprint(repo, state)
        if gate.get("status") != "approved" or gate.get("fingerprint") != current:
            raise ValidationError("A current G3 acceptance approval is required before close.")
        state["status"] = "closed"
        state["phase"] = "closed"
        state["closed_at"] = utc_now()
        save_state_unlocked(repo, state)
        append_event_unlocked(repo, work_id, "work_closed", {"closed_at": state["closed_at"]})
        return state


def instructions(repo: Path, state: dict[str, Any]) -> dict[str, Any]:
    phase = state["phase"]
    current_gate = _current_gate_for_phase(phase)
    gate_is_approved = (
        current_gate is not None
        and state["gates"][current_gate].get("status") == "approved"
    )
    next_action = {
        "requirements": "complete_requirements_or_request_g1",
        "scope_review": "request_g1",
        "design": "complete_design_or_request_g2",
        "build_review": "request_g2",
        "implementation": "run_next_task",
        "verification": "verify_or_request_g3",
        "acceptance_review": "close" if gate_is_approved else "request_g3",
        "closed": "none",
    }.get(phase, "inspect_state")
    payload = {
        "work": state["id"],
        "kind": state["kind"],
        "risk": state["risk"]["level"],
        "phase": phase,
        "status": state["status"],
        "reference": PHASE_REFERENCES.get(phase, "references/contracts.md"),
        "pending_gate": None if gate_is_approved else current_gate,
        "next_action": next_action,
        "tasks": state.get("tasks", {}),
        "blocker": state.get("blocker"),
        "gates": state["gates"],
    }
    payload["knowledge"] = work_knowledge_status(repo, state)
    if phase in ("verification", "acceptance_review") and not gate_is_approved:
        incomplete_tasks = any(
            task.get("status") != "completed"
            for task in state.get("tasks", {}).values()
        )
        review = payload["knowledge"].get("review", {})
        planned = payload["knowledge"].get("planned") or {}
        if incomplete_tasks:
            next_action = "run_next_task"
        elif review.get("required") and not review.get("current"):
            next_action = "record_knowledge_review"
        elif review.get("disposition") == "promote":
            content_targets = set(planned.get("upserts", [])) | set(
                planned.get("deletes", [])
            )
            if not content_targets:
                next_action = "plan_knowledge_updates"
            else:
                seal_targets = set(planned.get("upserts", [])) | set(
                    planned.get("coupled", [])
                )
                if not seal_targets.issubset(set(planned.get("sealed", []))):
                    next_action = "promote_and_seal_knowledge"
        payload["next_action"] = next_action
        payload["knowledge"]["next_action"] = next_action
    if phase in ("requirements", "scope_review"):
        payload["knowledge"]["read_order"] = [
            f"{knowledge_root(repo)}/index.md",
            "at_most_five_related_pages",
            "raw_sources_only_for_recorded_gaps",
        ]
    elif phase in ("design", "build_review"):
        payload["knowledge"]["write_policy"] = "read_only"
    elif phase in ("verification", "acceptance_review"):
        payload["knowledge"]["write_policy"] = "planned_pages_and_coupled_index_log_only"
    return payload


def bind_session(repo: Path, session_id: str, work_id: str) -> dict[str, Any]:
    state = load_state(repo, work_id)
    if state.get("status") == "closed":
        raise ValidationError("Cannot bind a session to closed work.")
    safe_session = re.sub(r"[^A-Za-z0-9._-]+", "-", session_id)
    path = devweave_root(repo) / "cache" / "sessions" / f"{safe_session}.json"
    payload = {"session_id": session_id, "work": work_id, "bound_at": utc_now()}
    atomic_write_json(path, payload)
    return payload


def load_session_binding(repo: Path, session_id: str) -> dict[str, Any] | None:
    safe_session = re.sub(r"[^A-Za-z0-9._-]+", "-", session_id)
    path = devweave_root(repo) / "cache" / "sessions" / f"{safe_session}.json"
    if not path.exists():
        return None
    try:
        return read_json(path)
    except ValidationError:
        return None


DOCTOR_PROBE_TIMEOUT_SECONDS = 5
DOCTOR_LAUNCHER_TIMEOUT_SECONDS = 15
EXPECTED_HOOK_MATCHER = "^(Bash|apply_patch|Edit|Write)$"


def _doctor_output(result: subprocess.CompletedProcess[bytes]) -> str:
    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    detail = stdout or stderr or f"exit code {result.returncode}"
    return detail[:240]


def _doctor_process(
    argv: Sequence[str],
    cwd: Path,
    *,
    input_bytes: bytes = b"",
    timeout_seconds: int = DOCTOR_PROBE_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            input=input_bytes,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return False, f"{argv[0]} not found"
    except subprocess.TimeoutExpired:
        return False, f"{argv[0]} timed out after {timeout_seconds}s"
    except OSError as exc:
        return False, f"{argv[0]} failed: {type(exc).__name__}: {exc}"
    return result.returncode == 0, _doctor_output(result)


def _doctor_executable(
    repo: Path,
    name: str,
    args: Sequence[str],
) -> tuple[bool, str]:
    executable = shutil.which(name)
    if executable is None:
        return False, f"{name} not found on PATH"
    ok, detail = _doctor_process([executable, *args], repo)
    return ok, f"{executable}: {detail}"


def _doctor_hook_contract(repo: Path) -> tuple[bool, str, str | None]:
    path = repo / ".codex" / "hooks.json"
    if not path.exists():
        return False, f"missing {path}; trust the repository hook after it is installed", None
    try:
        hook = read_json(path)
    except (OSError, DevWeaveError) as exc:
        return False, f"cannot read hook: {exc}", None
    groups = hook.get("hooks", {}).get("PreToolUse")
    if not isinstance(groups, list) or len(groups) != 1:
        return False, "PreToolUse must contain exactly one guard group", None
    group = groups[0]
    if not isinstance(group, dict) or group.get("matcher") != EXPECTED_HOOK_MATCHER:
        return False, f"matcher must be {EXPECTED_HOOK_MATCHER!r}", None
    handlers = group.get("hooks")
    if not isinstance(handlers, list) or len(handlers) != 1:
        return False, "PreToolUse guard group must contain exactly one handler", None
    command = handlers[0]
    if not isinstance(command, dict) or command.get("type") != "command":
        return False, "PreToolUse handler must be a command hook", None
    if command.get("timeout") != 30:
        return False, "command hook timeout must be 30 seconds", None
    if command.get("statusMessage") != "Checking DevWeave gates":
        return False, "command hook statusMessage is missing or incorrect", None
    posix = command.get("command")
    windows = command.get("commandWindows")
    if not isinstance(posix, str) or "python3 -X utf8 -B" not in posix:
        return False, "POSIX command must use python3 -X utf8 -B", None
    if not isinstance(posix, str) or "$(git rev-parse --show-toplevel)" not in posix:
        return False, "POSIX command must resolve the Git root", None
    if not isinstance(windows, str):
        return False, "Windows commandWindows adapter is missing", None
    required_windows = (
        "powershell.exe -NoLogo -NoProfile -NonInteractive -Command",
        "py -3 -X utf8 -B",
        "Join-Path (git rev-parse --show-toplevel)",
    )
    missing = [fragment for fragment in required_windows if fragment not in windows]
    if missing:
        return False, f"Windows launcher is missing: {', '.join(missing)}", None
    if "$repo" in posix or "$repo" in windows:
        return False, "hook launcher must not use the $repo shell variable", None
    return True, "schema valid; trust this repository hook once in Codex", windows


def _doctor_launcher_probe(repo: Path, command_windows: str | None) -> tuple[bool, str]:
    if not command_windows:
        return False, "launcher probe skipped because commandWindows is unavailable"
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        return False, "powershell.exe not found; launcher probe unavailable"
    payload = json.dumps(
        {
            "cwd": str(repo),
            "session_id": "",
            "tool_name": "Bash",
            "tool_input": {"command": "git status --short"},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    probe_cwds = [repo]
    nested = repo / "vscode-extension"
    if nested.is_dir():
        probe_cwds.append(nested)
    for cwd in probe_cwds:
        try:
            result = subprocess.run(
                [
                    powershell,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command_windows,
                ],
                cwd=cwd,
                input=payload,
                capture_output=True,
                check=False,
                timeout=DOCTOR_LAUNCHER_TIMEOUT_SECONDS,
            )
        except FileNotFoundError:
            return False, "powershell.exe disappeared before launcher probe"
        except subprocess.TimeoutExpired:
            return False, f"launcher probe timed out after {DOCTOR_LAUNCHER_TIMEOUT_SECONDS}s at {cwd}"
        except OSError as exc:
            return False, f"launcher probe failed at {cwd}: {type(exc).__name__}: {exc}"
        if result.returncode != 0:
            return False, f"launcher exited {result.returncode} at {cwd}: {_doctor_output(result)}"
        if result.stdout:
            return False, f"read-only Bash launcher must be silent at {cwd}"
    locations = ", ".join(str(cwd) for cwd in probe_cwds)
    return True, f"commandWindows probe passed at {locations}"


def doctor(repo: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add(
        "python",
        sys.version_info >= (3, 11),
        ".".join(str(item) for item in sys.version_info[:3]),
    )
    git_ok = _git(repo, ["rev-parse", "--is-inside-work-tree"], check=False).returncode == 0
    add("git", git_ok, str(repo))
    add("project", project_path(repo).exists(), str(project_path(repo)))
    add(
        "skill",
        (skill_root() / "SKILL.md").exists(),
        str(skill_root() / "SKILL.md"),
    )
    hook_ok, hook_detail, command_windows = _doctor_hook_contract(repo)
    add("hook", hook_ok, hook_detail)
    if os.name == "nt":
        py_ok, py_detail = _doctor_executable(repo, "py", ["-3", "--version"])
        add("py-3", py_ok, py_detail)
        cmd_ok, cmd_detail = _doctor_executable(repo, "cmd.exe", ["/d", "/s", "/c", "ver"])
        add("cmd", cmd_ok, cmd_detail)
        powershell_ok, powershell_detail = _doctor_executable(
            repo,
            "powershell.exe",
            ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        )
        add("powershell", powershell_ok, powershell_detail)
        pwsh_ok, pwsh_detail = _doctor_executable(
            repo,
            "pwsh",
            ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        )
        add("pwsh", pwsh_ok, pwsh_detail)
        add("hook-schema", hook_ok, hook_detail)
        probe_ok, probe_detail = _doctor_launcher_probe(repo, command_windows)
        add("launcher-probe", probe_ok, probe_detail)
    else:
        detail = "Windows-only prerequisite probe skipped on this non-Windows host."
        for name in ("py-3", "cmd", "powershell", "pwsh", "hook-schema", "launcher-probe"):
            add(name, True, detail)
    if project_path(repo).exists():
        try:
            project = load_project(repo)
            command_ids = [item.get("id") for item in project.get("commands", [])]
            add(
                "commands",
                len(command_ids) == len(set(command_ids)),
                f"{len(command_ids)} configured command(s)",
            )
            root = project["knowledge"]["root"]
            try:
                inspection = knowledge.inspect_wiki(repo, root=root)
                compatible = inspection["status"] == "compatible"
                if compatible:
                    detail = f"{root}/ is compatible"
                elif inspection["status"] in ("missing", "empty"):
                    detail = f"{root}/ is {inspection['status']}; run init or start to bootstrap it"
                else:
                    reasons = "; ".join(
                        f"{item['path']}: {item['reason']}"
                        for item in inspection["conflicts"]
                    )
                    detail = f"knowledge_conflict: {reasons}"
            except knowledge.KnowledgeError as exc:
                compatible = False
                detail = f"knowledge_conflict: {exc.message}"
            add("knowledge", compatible, detail)
        except DevWeaveError as exc:
            add("commands", False, exc.message)
    return {"ok": all(item["ok"] for item in checks), "checks": checks}

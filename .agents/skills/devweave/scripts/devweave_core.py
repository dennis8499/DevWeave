from __future__ import annotations

import fnmatch
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = 1
KINDS = ("new", "feature", "refactor", "bug")
RISK_LEVELS = ("low", "standard", "high")
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
FRAMEWORK_PREFIXES = (
    ".devweave/",
    ".agents/skills/devweave/",
    ".codex/",
)
MAX_RAW_LOG_BYTES = 5_000_000
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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_relpath(path: str | Path) -> str:
    normalized = Path(path).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def is_framework_path(path: str) -> bool:
    normalized = normalize_relpath(path)
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in FRAMEWORK_PREFIXES)


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
    if len(command_ids) != len(set(command_ids)):
        errors.append("command IDs must be unique")
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
    }


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
    with WorkLock(repo, "project"):
        root = devweave_root(repo)
        root.mkdir(parents=True, exist_ok=True)
        (root / "cache" / "sessions").mkdir(parents=True, exist_ok=True)
        (root / "work-items").mkdir(parents=True, exist_ok=True)
        (root / "baseline" / "capabilities").mkdir(parents=True, exist_ok=True)
        if not project_path(repo).exists():
            atomic_write_json(project_path(repo), project_defaults())
        for target, asset in (
            ("product.md", "baseline-product.md.tmpl"),
            ("architecture.md", "baseline-architecture.md.tmpl"),
            ("quality.md", "baseline-quality.md.tmpl"),
        ):
            output = root / "baseline" / target
            if not output.exists():
                atomic_write_text(output, _render_asset(asset, {}))
        _ensure_gitignore(repo)
    return load_project(repo)


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
    filtered = sorted(path for path in paths if not is_framework_path(path))
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
    return sorted(path for path in paths if not is_framework_path(path))


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


def create_work(
    repo: Path,
    kind: str,
    title: str,
    risk: str = "standard",
    risk_rationale: str = "",
) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValidationError("Unknown work kind.", {"kind": kind, "allowed": list(KINDS)})
    if risk not in RISK_LEVELS:
        raise ValidationError(
            "Unknown risk level.", {"risk": risk, "allowed": list(RISK_LEVELS)}
        )
    if not title.strip():
        raise ValidationError("Work title must not be empty.")
    if not project_path(repo).exists():
        init_project(repo)
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
    base_baseline = state.get("base_baseline")
    if (
        not isinstance(base_baseline, dict)
        or not isinstance(base_baseline.get("files"), dict)
        or not isinstance(base_baseline.get("fingerprint"), str)
    ):
        errors.append("base_baseline is invalid")
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
    material += canonical_json(
        {
            "risk": state["risk"],
            "scope": state["scope"],
            "waivers": _waivers_for_gate(state, "scope"),
            "discovery_evidence": _discovery_evidence(state),
        }
    )
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
    material += canonical_json(
        {
            "source": source["fingerprint"],
            "evidence": evidence,
            "baseline": _baseline_fingerprint(repo, state),
            "waivers": _waivers_for_gate(state, "acceptance"),
        }
    )
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


def _waiver_exists(state: dict[str, Any], kind: str, target: str | None = None) -> bool:
    return any(
        waiver.get("kind") == kind
        and (target is None or waiver.get("target") == target)
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
        if state["risk"]["level"] == "high":
            required_kinds.add("review")
        observed_kinds = {item.get("kind") for item in source_bound_evidence}
        missing_kinds = sorted(required_kinds - observed_kinds)
        if missing_kinds:
            errors.append(
                f"Missing required passing evidence kinds: {', '.join(missing_kinds)}"
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
) -> dict[str, Any]:
    _validate_evidence_id_syntax(covers, tasks)
    if status not in ("passed", "failed", "waived"):
        raise ValidationError("Unknown evidence status.", {"status": status})
    if observed_result not in ("success", "failure", "neutral"):
        raise ValidationError(
            "Unknown observed result.", {"observed_result": observed_result}
        )
    if not summary.strip():
        raise ValidationError("Evidence summary must not be empty.")
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


def run_verification(
    repo: Path,
    work_id: str,
    *,
    command_id: str,
    kind: str,
    covers: Sequence[str] = (),
    tasks: Sequence[str] = (),
    expectation: str = "zero",
) -> dict[str, Any]:
    _validate_evidence_id_syntax(covers, tasks)
    if expectation not in ("zero", "nonzero", "any"):
        raise ValidationError("Unknown exit expectation.", {"expectation": expectation})
    project = load_project(repo)
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
    started_at = utc_now()
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
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    except OSError as exc:
        exit_code = None
        stdout = b""
        stderr = str(exc).encode("utf-8", errors="replace")
        execution_error = f"{type(exc).__name__}: {exc}"
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
        source = git_snapshot(repo)
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
            "started_at": started_at,
            "stale": False,
            "binds_current_source": kind not in ("reproduction", "baseline"),
            "command_id": command_id,
            "argv": command["argv"],
            "cwd": normalize_relpath(command.get("cwd", ".")),
            "exit_code": exit_code,
            "expectation": expectation,
            "timed_out": timed_out,
            "execution_error": execution_error,
            "raw_log": normalize_relpath(log_path.relative_to(repo)),
            "log_truncated": truncated,
        }
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
    return {
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
    add(
        "hook",
        (repo / ".codex" / "hooks.json").exists(),
        "Project hooks require one-time trust in Codex.",
    )
    if project_path(repo).exists():
        try:
            project = load_project(repo)
            command_ids = [item.get("id") for item in project.get("commands", [])]
            add(
                "commands",
                len(command_ids) == len(set(command_ids)),
                f"{len(command_ids)} configured command(s)",
            )
        except DevWeaveError as exc:
            add("commands", False, exc.message)
    return {"ok": all(item["ok"] for item in checks), "checks": checks}

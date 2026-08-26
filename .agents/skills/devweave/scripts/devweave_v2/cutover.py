"""Hash-bound, retry-safe tracked-tree cutover from DevWeave V1 to V2."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .canonical import dumps, sha256
from .cutover_hashing import (
    PRE_FINALIZER_MANAGED_DELETIONS,
    canonical_file_sha256,
    git_file_sha256,
)
from .cutover_git import git as _git
from .cutover_git import git_files as _git_files
from .cutover_provenance import bounded_branch as _branch_value
from .cutover_provenance import git_anchor_issues
from .cutover_provenance import git_sha1 as _git_hash_value
from .cutover_provenance import manifest_provenance
from .cutover_provenance import sha256_digest as _sha256_value
from .cutover_provenance import validate_completion_record
from .errors import DevWeaveError, ErrorCode
from .version import VERSION

MANIFEST_SCHEMA_VERSION = 3
MAX_MANIFEST_ENTRIES = 2_000
TRANSITION_RUN_ID = "20260825-163914-feature-devweave-v2-app-server-harness"
TRANSITION_COMPLETION_PATH = f"docs/exec-plans/completed/{TRANSITION_RUN_ID}.json"
LEGACY_TRANSITION_STATE_PATH = f".devweave/work-items/{TRANSITION_RUN_ID}/state.json"

REPLACEMENT_PATHS = (
    (".agents/skills/devweave/assets/v2-cutover/AGENTS.md", "AGENTS.md"),
    (".agents/skills/devweave/assets/v2-skill/SKILL.md", ".agents/skills/devweave/SKILL.md"),
    (
        ".agents/skills/devweave/assets/v2-skill/references/planning.md",
        ".agents/skills/devweave/references/planning.md",
    ),
    (
        ".agents/skills/devweave/assets/v2-skill/references/implementation.md",
        ".agents/skills/devweave/references/implementation.md",
    ),
    (
        ".agents/skills/devweave/assets/v2-skill/references/verification.md",
        ".agents/skills/devweave/references/verification.md",
    ),
    (".agents/skills/devweave/assets/v2-cutover/project.json", ".devweave/project.json"),
)

LEGACY_ROOTS = (
    ".devweave/baseline/",
    ".devweave/work-items/",
    "wiki/",
    ".agents/skills/codebase-design/",
    ".agents/skills/diagnosing-bugs/",
    ".agents/skills/grill-me/",
    ".agents/skills/grilling/",
    ".agents/skills/tdd/",
    ".agents/skills/devweave/assets/",
    "vscode-extension/assets/",
)

LEGACY_EXACT_PATHS = frozenset(
    {
        ".codex/hooks.json",
        "skills-lock.json",
        ".agents/skills/devweave/scripts/command_policy.py",
        ".agents/skills/devweave/scripts/devweave.py",
        ".agents/skills/devweave/scripts/devweave_core.py",
        ".agents/skills/devweave/scripts/guard.py",
        ".agents/skills/devweave/scripts/knowledge_core.py",
        "tests/devweave_test_support.py",
        "vscode-extension/webview/help-content.ts",
    }
)

LEGACY_EXTENSION_ROOT_MODULES = frozenset(
    {
        "bootstrap-compat.ts", "bootstrap.ts", "clipboard.ts", "dashboard-sections.ts",
        "dashboard.ts", "filesystem.ts", "model.ts", "plan-mode.ts", "presentation.ts",
        "preview-gate.ts", "prompt.ts", "protocol.ts", "refresh-coordinator.ts",
        "render-scheduler.ts", "snapshot.ts", "tree.ts", "vscode-bootstrap.ts",
        "vscode-filesystem.ts", "wiki-results-mount.ts", "wiki-search.ts", "work-selection.ts",
    }
)

V2_EXTENSION_TESTS = frozenset(
    {
        "app-server-session.test.ts", "package-version.test.ts", "release-transaction.test.ts",
        "security.test.ts", "ui-evidence.test.ts", "webview-contract.test.ts",
        "workspace-controller.test.ts",
    }
)

V2_REFERENCE_PATHS = frozenset(
    destination
    for _source, destination in REPLACEMENT_PATHS
    if destination.startswith(".agents/skills/devweave/references/")
)


def generate_manifest(repository: Path, *, base_ref: str) -> dict[str, Any]:
    root = repository.resolve()
    resolved_base = _git(root, "rev-parse", "--verify", f"{base_ref}^{{commit}}").strip()
    prepared_from_head = _git(root, "rev-parse", "HEAD").strip()
    prepared_from_branch = _git(root, "branch", "--show-current").strip()
    if not prepared_from_branch:
        raise DevWeaveError(ErrorCode.CONFLICT, "Cutover manifest cannot be prepared from detached HEAD.")
    tracked = set(_git_files(root))
    replacements: list[dict[str, str]] = []
    for source, destination in REPLACEMENT_PATHS:
        source_path = _safe_path(root, source)
        destination_path = _safe_path(root, destination)
        if not source_path.is_file():
            raise DevWeaveError(
                ErrorCode.NOT_FOUND,
                "Cutover replacement source is missing.",
                {"source": source, "destination": destination},
            )
        after = canonical_file_sha256(source_path)
        replacements.append(
            {
                "source": source,
                "source_sha256": after,
                "destination": destination,
                "before_sha256": canonical_file_sha256(destination_path) if destination_path.is_file() else "0" * 64,
                "after_sha256": after,
            }
        )

    deletion_paths = {path for path in tracked if _is_legacy(path)}
    deletion_paths.update(source for source, _destination in REPLACEMENT_PATHS)
    deletion_paths.update(_legacy_files_on_disk(root))
    deletions = []
    for relative in sorted(deletion_paths):
        path = _safe_path(root, relative)
        if path.exists() or path.is_symlink():
            deletion_sha256 = canonical_file_sha256(path)
        elif relative in PRE_FINALIZER_MANAGED_DELETIONS:
            revision = "HEAD" if relative in tracked else base_ref
            deletion_sha256 = git_file_sha256(root, revision, relative)
        else:
            raise DevWeaveError(
                ErrorCode.NOT_FOUND,
                "A manifest deletion target is missing.",
                {"path": relative},
            )
        deletions.append({"path": relative, "sha256": deletion_sha256})

    if len(deletions) + len(replacements) > MAX_MANIFEST_ENTRIES:
        raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Cutover manifest contains too many entries.")
    retained: list[dict[str, str]] = []
    completion_path = _safe_path(root, TRANSITION_COMPLETION_PATH)
    if completion_path.is_file():
        validate_completion_record(completion_path, transition_run_id=TRANSITION_RUN_ID)
        retained.append(
            {
                "path": TRANSITION_COMPLETION_PATH,
                "sha256": canonical_file_sha256(completion_path),
            }
        )
    provenance = manifest_provenance(
        root,
        completion_path=completion_path,
        transition_state_path=_safe_path(root, LEGACY_TRANSITION_STATE_PATH),
        transition_run_id=TRANSITION_RUN_ID,
        prepared_from_head=prepared_from_head,
        prepared_from_branch=prepared_from_branch,
        resolved_base=resolved_base,
    )
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "product_version": VERSION,
        "prepared_from_branch": prepared_from_branch,
        "prepared_from_head": prepared_from_head,
        "base_branch": provenance["base_branch"],
        "base_ref": resolved_base,
        "source_fingerprint": provenance["source_fingerprint"],
        "replacements": replacements,
        "deletions": deletions,
        "retained": retained,
    }
    return {**payload, "manifest_sha256": sha256(payload)}


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, dumps(manifest).encode("utf-8"))


class CutoverFinalizer:
    def __init__(self, repository: Path, manifest_path: Path) -> None:
        self.repository = repository.resolve()
        self.manifest_path = manifest_path.resolve()
        self.manifest = _load_manifest(self.repository, self.manifest_path)

    @property
    def manifest_sha256(self) -> str:
        return str(self.manifest["manifest_sha256"])

    def check(self) -> dict[str, Any]:
        report = self._preflight()
        return {
            "status": report["status"],
            "manifest_sha256": self.manifest_sha256,
            "pending_replacements": report["pending_replacements"],
            "pending_deletions": report["pending_deletions"],
            "completed_replacements": report["completed_replacements"],
            "completed_deletions": report["completed_deletions"],
            "retained_records": report["retained_records"],
            "completion_record_ready": report["completion_record_ready"],
        }

    def apply(self, *, approved_manifest_sha256: str, fail_after: int | None = None) -> dict[str, Any]:
        if approved_manifest_sha256 != self.manifest_sha256:
            raise DevWeaveError(
                ErrorCode.FORBIDDEN,
                "The approved cutover manifest hash does not match.",
                {"expected": self.manifest_sha256},
            )
        report = self._preflight()
        if not report["completion_record_ready"]:
            raise DevWeaveError(
                ErrorCode.BLOCKED,
                "Cutover requires a hash-bound completed transition ExecPlan.",
                {"path": TRANSITION_COMPLETION_PATH},
            )
        if report["status"] == "already_applied":
            return {"status": "already_applied", "manifest_sha256": self.manifest_sha256, "mutations": 0}

        mutations = 0
        for item in self.manifest["replacements"]:
            destination = _safe_path(self.repository, item["destination"])
            if destination.is_file() and canonical_file_sha256(destination) == item["after_sha256"]:
                continue
            source = _safe_path(self.repository, item["source"])
            _atomic_write(destination, source.read_bytes())
            mutations = self._after_mutation(mutations, fail_after)

        for item in self.manifest["deletions"]:
            path = _safe_path(self.repository, item["path"])
            if not path.exists():
                continue
            path.unlink()
            mutations = self._after_mutation(mutations, fail_after)

        _remove_empty_legacy_directories(self.repository)
        final = self._preflight()
        if final["status"] != "already_applied":
            raise DevWeaveError(ErrorCode.INTERNAL, "Cutover did not converge to the final state.", final)
        return {"status": "applied", "manifest_sha256": self.manifest_sha256, "mutations": mutations}

    @staticmethod
    def _after_mutation(current: int, fail_after: int | None) -> int:
        result = current + 1
        if fail_after is not None and result == fail_after:
            raise RuntimeError(f"Injected cutover failure after {result} mutations.")
        return result

    def _preflight(self) -> dict[str, Any]:
        errors: list[dict[str, str]] = []
        pending_replacements = completed_replacements = 0
        pending_deletions = completed_deletions = 0
        retained_records = 0

        errors.extend(
            git_anchor_issues(
                self.repository,
                manifest_path=self.manifest_path,
                manifest=self.manifest,
                completion_path=_safe_path(self.repository, TRANSITION_COMPLETION_PATH),
                completion_relative=TRANSITION_COMPLETION_PATH,
                transition_run_id=TRANSITION_RUN_ID,
            )
        )
        tracked_legacy = {path for path in _git_files(self.repository) if _is_legacy(path)}
        declared_deletions = {item["path"] for item in self.manifest["deletions"]}
        for path in sorted(tracked_legacy - declared_deletions):
            errors.append({"path": path, "reason": "unlisted tracked legacy path"})

        for item in self.manifest["replacements"]:
            source = _safe_path(self.repository, item["source"])
            destination = _safe_path(self.repository, item["destination"])
            destination_hash = canonical_file_sha256(destination) if destination.is_file() else None
            if destination_hash == item["after_sha256"]:
                completed_replacements += 1
                continue
            destination_is_expected_absent = destination_hash is None and item["before_sha256"] == "0" * 64
            if destination_hash != item["before_sha256"] and not destination_is_expected_absent:
                errors.append({"path": item["destination"], "reason": "replacement destination hash mismatch"})
                continue
            if not source.is_file() or canonical_file_sha256(source) != item["source_sha256"]:
                errors.append({"path": item["source"], "reason": "replacement source hash mismatch"})
                continue
            pending_replacements += 1

        for item in self.manifest["deletions"]:
            path = _safe_path(self.repository, item["path"])
            if not path.exists():
                completed_deletions += 1
            elif not path.is_file() or canonical_file_sha256(path) != item["sha256"]:
                errors.append({"path": item["path"], "reason": "deletion target hash mismatch"})
            else:
                pending_deletions += 1

        declared_retained = {item["path"] for item in self.manifest["retained"]}
        completion_path = _safe_path(self.repository, TRANSITION_COMPLETION_PATH)
        if completion_path.exists() and TRANSITION_COMPLETION_PATH not in declared_retained:
            errors.append({"path": TRANSITION_COMPLETION_PATH, "reason": "unlisted completion record"})
        for item in self.manifest["retained"]:
            path = _safe_path(self.repository, item["path"])
            if not path.is_file() or canonical_file_sha256(path) != item["sha256"]:
                errors.append({"path": item["path"], "reason": "retained record hash mismatch"})
                continue
            try:
                validate_completion_record(path, transition_run_id=TRANSITION_RUN_ID)
            except DevWeaveError:
                errors.append({"path": item["path"], "reason": "retained completion record is invalid"})
                continue
            retained_records += 1

        if errors:
            raise DevWeaveError(
                ErrorCode.CONFLICT,
                "Cutover preflight found path or hash drift; no mutation was performed.",
                {"issues": errors[:64], "issue_count": len(errors)},
            )
        status = "already_applied" if pending_replacements == 0 and pending_deletions == 0 else "ready"
        return {
            "status": status,
            "pending_replacements": pending_replacements,
            "pending_deletions": pending_deletions,
            "completed_replacements": completed_replacements,
            "completed_deletions": completed_deletions,
            "retained_records": retained_records,
            "completion_record_ready": retained_records == 1,
        }

def _load_manifest(repository: Path, path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DevWeaveError(ErrorCode.INVALID_JSON, "Cutover manifest is unavailable or invalid JSON.") from exc
    required = {
        "schema_version", "product_version", "prepared_from_branch", "prepared_from_head",
        "base_branch", "base_ref", "source_fingerprint", "replacements", "deletions",
        "retained", "manifest_sha256",
    }
    if not isinstance(raw, dict) or set(raw) != required:
        raise DevWeaveError(ErrorCode.UNKNOWN_FIELD, "Cutover manifest fields do not match the strict contract.")
    if raw["schema_version"] != MANIFEST_SCHEMA_VERSION or raw["product_version"] != VERSION:
        raise DevWeaveError(ErrorCode.SCHEMA_VERSION, "Cutover manifest version is unsupported.")
    payload = {key: value for key, value in raw.items() if key != "manifest_sha256"}
    if raw["manifest_sha256"] != sha256(payload):
        raise DevWeaveError(ErrorCode.CONFLICT, "Cutover manifest canonical hash mismatch.")
    _branch_value(raw["prepared_from_branch"], "prepared_from_branch")
    _branch_value(raw["base_branch"], "base_branch")
    _git_hash_value(raw["prepared_from_head"], "prepared_from_head")
    _git_hash_value(raw["base_ref"], "base_ref")
    _sha256_value(raw["source_fingerprint"], "source_fingerprint")
    if not isinstance(raw["replacements"], list) or not isinstance(raw["deletions"], list) or not isinstance(raw["retained"], list):
        raise DevWeaveError(ErrorCode.INVALID_TYPE, "Cutover operations must be arrays.")
    if len(raw["replacements"]) + len(raw["deletions"]) + len(raw["retained"]) > MAX_MANIFEST_ENTRIES:
        raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Cutover manifest contains too many entries.")

    exact_replacements = {(source, destination) for source, destination in REPLACEMENT_PATHS}
    actual_replacements: set[tuple[str, str]] = set()
    for item in raw["replacements"]:
        _strict_item(item, {"source", "source_sha256", "destination", "before_sha256", "after_sha256"})
        source = _relative(item["source"])
        destination = _relative(item["destination"])
        actual_replacements.add((source, destination))
        for field in ("source_sha256", "before_sha256", "after_sha256"):
            _hash_value(item[field], field)
        if item["source_sha256"] != item["after_sha256"]:
            raise DevWeaveError(ErrorCode.CONFLICT, "Replacement source and final hashes differ.")
    if actual_replacements != exact_replacements:
        raise DevWeaveError(ErrorCode.FORBIDDEN, "Cutover replacement allowlist drifted.")

    seen: set[str] = set()
    for item in raw["deletions"]:
        _strict_item(item, {"path", "sha256"})
        relative = _relative(item["path"])
        if relative in seen or not _is_legacy(relative):
            raise DevWeaveError(ErrorCode.FORBIDDEN, "Cutover deletion is duplicated or outside the legacy allowlist.", {"path": relative})
        seen.add(relative)
        _hash_value(item["sha256"], "sha256")
    for source, _destination in REPLACEMENT_PATHS:
        if source not in seen:
            raise DevWeaveError(ErrorCode.REQUIRED_FIELD, "Replacement sources must be deleted after cutover.", {"path": source})
    if len(raw["retained"]) > 1:
        raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Cutover may bind only the transition completion record.")
    for item in raw["retained"]:
        _strict_item(item, {"path", "sha256"})
        if _relative(item["path"]) != TRANSITION_COMPLETION_PATH:
            raise DevWeaveError(ErrorCode.FORBIDDEN, "Cutover retained path is not allowlisted.")
        _hash_value(item["sha256"], "sha256")
    _safe_path(repository, path.relative_to(repository).as_posix())
    return raw


def _strict_item(value: Any, fields: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise DevWeaveError(ErrorCode.UNKNOWN_FIELD, "Cutover operation fields do not match the strict contract.")


def _hash_value(value: Any, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise DevWeaveError(ErrorCode.INVALID_VALUE, f"Cutover {field} must be lowercase SHA-256.")


def _relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "Cutover paths must be normalized repository-relative paths.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "Cutover path escapes the repository.", {"path": value})
    return path.as_posix()


def _safe_path(repository: Path, relative: str) -> Path:
    normalized = _relative(relative)
    current = repository
    for part in PurePosixPath(normalized).parts:
        current = current / part
        if current.is_symlink():
            raise DevWeaveError(ErrorCode.FORBIDDEN, "Cutover path crosses a symlink.", {"path": normalized})
    try:
        current.resolve(strict=False).relative_to(repository)
    except ValueError as exc:
        raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "Cutover path escapes the repository.") from exc
    return current


def _is_legacy(path: str) -> bool:
    if path in LEGACY_EXACT_PATHS or any(path.startswith(prefix) for prefix in LEGACY_ROOTS):
        return True
    if path.startswith(".agents/skills/devweave/references/"):
        return path not in V2_REFERENCE_PATHS
    if path.startswith("vscode-extension/src/") and path.count("/") == 2:
        return path.rsplit("/", 1)[-1] in LEGACY_EXTENSION_ROOT_MODULES
    if path.startswith("vscode-extension/test/unit/"):
        return path.rsplit("/", 1)[-1] not in V2_EXTENSION_TESTS
    if path.startswith("tests/test_") and path.endswith(".py"):
        name = path.rsplit("/", 1)[-1]
        return not name.startswith("test_v2_") and name != "test_app_server_e2e.py"
    return path.startswith("vscode-extension/") and path.endswith(".vsix") and path.count("/") == 1


def _legacy_files_on_disk(repository: Path) -> set[str]:
    result = {path for path in LEGACY_EXACT_PATHS if _safe_path(repository, path).is_file()}
    for prefix in LEGACY_ROOTS:
        root = _safe_path(repository, prefix.rstrip("/"))
        if not root.exists():
            continue
        for directory, names, files in os.walk(root, topdown=True, followlinks=False):
            directory_path = Path(directory)
            for name in list(names):
                if (directory_path / name).is_symlink():
                    raise DevWeaveError(ErrorCode.FORBIDDEN, "Legacy root contains a symlink.", {"path": str(directory_path / name)})
            for name in files:
                path = directory_path / name
                if path.is_symlink():
                    raise DevWeaveError(ErrorCode.FORBIDDEN, "Legacy root contains a symlink.", {"path": str(path)})
                result.add(path.relative_to(repository).as_posix())
    return result


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.devweave-{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _remove_empty_legacy_directories(repository: Path) -> None:
    roots: Iterable[str] = (*LEGACY_ROOTS, ".agents/skills/devweave/references/")
    for relative in sorted(roots, key=lambda value: value.count("/"), reverse=True):
        root = _safe_path(repository, relative.rstrip("/"))
        if not root.exists() or root.is_symlink():
            continue
        for directory, _names, _files in os.walk(root, topdown=False, followlinks=False):
            try:
                Path(directory).rmdir()
            except OSError:
                pass

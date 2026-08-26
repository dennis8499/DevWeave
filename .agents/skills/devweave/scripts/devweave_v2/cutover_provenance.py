"""Git and review provenance required before a destructive V2 cutover."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cutover_git import git, git_status_paths
from .errors import DevWeaveError, ErrorCode
from .run_state import validate_exec_plan

MAX_COMPLETION_RECORD_BYTES = 1_000_000


def manifest_provenance(
    repository: Path,
    *,
    completion_path: Path,
    transition_state_path: Path,
    transition_run_id: str,
    prepared_from_head: str,
    prepared_from_branch: str,
    resolved_base: str,
) -> dict[str, str]:
    if completion_path.is_file():
        plan = validate_completion_record(completion_path, transition_run_id=transition_run_id)
        report = transition_report(plan)
        expected = {
            "base_branch": plan["base_branch"],
            "base_ref": plan["base_ref"],
            "run_branch": plan["run_branch"],
            "repository_head": prepared_from_head,
        }
        for field, value in expected.items():
            if report[field] != value:
                raise DevWeaveError(ErrorCode.CONFLICT, f"Transition completion {field} is stale.")
        if plan["run_branch"] != prepared_from_branch or plan["base_ref"] != resolved_base:
            raise DevWeaveError(ErrorCode.CONFLICT, "Transition completion Git anchors do not match the manifest checkout.")
        source_fingerprint = report["source_fingerprint"]
        base_branch = plan["base_branch"]
    else:
        state = _legacy_transition_state(transition_state_path, transition_run_id)
        base = state.get("base_source", {})
        last_verification = state.get("last_verification", {})
        base_branch = bounded_branch(base.get("branch"), "base_source.branch")
        if base.get("head") != resolved_base:
            raise DevWeaveError(ErrorCode.CONFLICT, "Legacy transition base ref does not match the manifest base.")
        source_fingerprint = sha256_digest(
            last_verification.get("source_fingerprint"),
            "last_verification.source_fingerprint",
        )
    if git(repository, "rev-parse", "--verify", f"{base_branch}^{{commit}}").strip() != resolved_base:
        raise DevWeaveError(ErrorCode.CONFLICT, "Recorded base branch has moved from the immutable base ref.")
    return {"base_branch": base_branch, "source_fingerprint": source_fingerprint}


def git_anchor_issues(
    repository: Path,
    *,
    manifest_path: Path,
    manifest: dict[str, Any],
    completion_path: Path,
    completion_relative: str,
    transition_run_id: str,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    current_head = git(repository, "rev-parse", "HEAD").strip()
    current_branch = git(repository, "branch", "--show-current").strip()
    if current_head != manifest["prepared_from_head"]:
        issues.append({"path": ".git/HEAD", "reason": "prepared HEAD mismatch"})
    if current_branch != manifest["prepared_from_branch"]:
        issues.append({"path": ".git/HEAD", "reason": "prepared branch mismatch"})
    try:
        resolved_base = git(
            repository, "rev-parse", "--verify", f"{manifest['base_branch']}^{{commit}}",
        ).strip()
    except DevWeaveError:
        resolved_base = ""
    if resolved_base != manifest["base_ref"]:
        issues.append({"path": ".git/refs", "reason": "base branch moved from manifest base ref"})

    allowed_dirty = {manifest_path.relative_to(repository).as_posix()}
    for item in manifest["replacements"]:
        allowed_dirty.update((item["source"], item["destination"]))
    allowed_dirty.update(item["path"] for item in manifest["deletions"])
    allowed_dirty.update(item["path"] for item in manifest["retained"])
    for path in sorted(set(git_status_paths(repository)) - allowed_dirty):
        issues.append({"path": path, "reason": "dirty path is not hash-bound by the finalizer manifest"})

    if completion_path.is_file():
        try:
            plan = validate_completion_record(completion_path, transition_run_id=transition_run_id)
            report = transition_report(plan)
            expected = {
                "base_branch": manifest["base_branch"],
                "base_ref": manifest["base_ref"],
                "run_branch": manifest["prepared_from_branch"],
                "repository_head": manifest["prepared_from_head"],
                "source_fingerprint": manifest["source_fingerprint"],
            }
            for field, value in expected.items():
                if report[field] != value:
                    issues.append({"path": completion_relative, "reason": f"completion {field} mismatch"})
            resolved_source = git(
                repository, "rev-parse", "--verify", f"{report['source_head']}^{{commit}}",
            ).strip()
            merge_base = git(repository, "merge-base", resolved_source, manifest["prepared_from_head"]).strip()
            if merge_base != resolved_source:
                issues.append({"path": completion_relative, "reason": "reviewed source is not an ancestor of prepared HEAD"})
        except DevWeaveError:
            issues.append({"path": completion_relative, "reason": "completion provenance is invalid"})
    return issues


def validate_completion_record(path: Path, *, transition_run_id: str) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            raise DevWeaveError(ErrorCode.FORBIDDEN, "Transition completion record must be a regular file.")
        if path.stat().st_size > MAX_COMPLETION_RECORD_BYTES:
            raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Transition completion record exceeds its size bound.")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except DevWeaveError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DevWeaveError(ErrorCode.INVALID_JSON, "Transition completion record is invalid JSON.") from exc
    plan = validate_exec_plan(raw)
    if plan["run_id"] != transition_run_id or plan["status"] != "completed" or plan["phase"] != "closed":
        raise DevWeaveError(ErrorCode.CONFLICT, "Transition completion record is not the closed V2 cutover ExecPlan.")
    if (
        not plan["completion_requested"]
        or plan["verification"]["status"] != "passed"
        or plan["review"]["status"] != "passed"
        or any(task["status"] != "completed" or not task["commit_ref"] for task in plan["tasks"].values())
        or any(gate["status"] != "approved" for gate in plan["gates"].values())
    ):
        raise DevWeaveError(ErrorCode.BLOCKED, "Transition completion record lacks closed, committed proof.")
    transition_report(plan)
    return plan


def transition_report(plan: dict[str, Any]) -> dict[str, str]:
    verification = plan["verification"]
    report_id = verification["current_report_id"]
    if report_id != "transition" or report_id not in verification["reports"]:
        raise DevWeaveError(ErrorCode.CONFLICT, "Transition completion lacks its current transition report.")
    report = verification["reports"][report_id]
    required = {
        "base_branch", "base_ref", "run_branch", "repository_head", "source_head",
        "source_digest", "source_fingerprint",
    }
    if not isinstance(report, dict) or not required.issubset(report):
        raise DevWeaveError(ErrorCode.REQUIRED_FIELD, "Transition report lacks Git and source bindings.")
    result = {
        "base_branch": bounded_branch(report["base_branch"], "transition.base_branch"),
        "base_ref": git_sha1(report["base_ref"], "transition.base_ref"),
        "run_branch": bounded_branch(report["run_branch"], "transition.run_branch"),
        "repository_head": git_sha1(report["repository_head"], "transition.repository_head"),
        "source_head": git_sha1(report["source_head"], "transition.source_head"),
        "source_fingerprint": sha256_digest(report["source_fingerprint"], "transition.source_fingerprint"),
    }
    if report["source_digest"] != result["source_fingerprint"] or plan["review"]["source_fingerprint"] != result["source_fingerprint"]:
        raise DevWeaveError(ErrorCode.CONFLICT, "Transition verification and review source bindings differ.")
    return result


def sha256_digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise DevWeaveError(ErrorCode.INVALID_VALUE, f"Cutover {field} must be lowercase SHA-256.")
    return value


def git_sha1(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise DevWeaveError(ErrorCode.INVALID_VALUE, f"Cutover {field} must be lowercase Git SHA-1.")
    return value


def bounded_branch(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256 or any(char in value for char in "\r\n\0"):
        raise DevWeaveError(ErrorCode.INVALID_VALUE, f"Cutover {field} is not a valid bounded branch name.")
    return value


def _legacy_transition_state(path: Path, transition_run_id: str) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_COMPLETION_RECORD_BYTES:
            raise DevWeaveError(ErrorCode.BLOCKED, "Legacy transition state is unavailable for manifest provenance.")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except DevWeaveError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DevWeaveError(ErrorCode.INVALID_JSON, "Legacy transition state is invalid JSON.") from exc
    if not isinstance(raw, dict) or raw.get("id") != transition_run_id:
        raise DevWeaveError(ErrorCode.CONFLICT, "Legacy transition state does not identify the authorized run.")
    return raw

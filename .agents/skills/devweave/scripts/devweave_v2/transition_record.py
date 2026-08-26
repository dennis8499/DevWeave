"""One-time, fail-closed projection of the accepted V1 transition into a V2 ExecPlan."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .canonical import dumps, primitive
from .cutover import TRANSITION_COMPLETION_PATH, TRANSITION_RUN_ID
from .errors import DevWeaveError, ErrorCode
from .plan_contracts import RunPlanDraft
from .plan_store import PlanStore
from .project_config import ProjectConfig
from .run_state import new_exec_plan, validate_exec_plan
from .version import SCHEMA_VERSION

WORK_ROOT = f".devweave/work-items/{TRANSITION_RUN_ID}"
MAX_TRANSITION_JSON_BYTES = 2_000_000
MAX_TRANSITION_MARKDOWN_BYTES = 1_000_000
TASK_PATHS: dict[str, tuple[str, ...]] = {
    # The closed V1 projection retains representative source slices but never
    # reissues historical authority over protected host/runtime roots.
    "TASK-001": ("fixtures/devweave_v2", "vscode-extension/package.json"),
    "TASK-002": ("tests/test_v2_run_service.py",),
    "TASK-003": ("docs/generated",),
    "TASK-004": ("tests/test_v2_verification.py",),
    "TASK-005": ("tests/test_v2_mcp.py",),
    "TASK-006": ("tests/test_v2_cli_host.py",),
    "TASK-007": ("vscode-extension/src/app-server/session.ts", "vscode-extension/test/unit/app-server-session.test.ts"),
    "TASK-008": (
        "vscode-extension/src/controller/approval-broker.ts",
        "vscode-extension/src/controller/host-bridge-client.ts",
        "vscode-extension/src/controller/review-coordinator.ts",
        "vscode-extension/src/controller/workspace-controller.ts",
        "vscode-extension/test/unit/workspace-controller.test.ts",
    ),
    "TASK-009": ("vscode-extension/src", "vscode-extension/webview", "vscode-extension/test"),
    "TASK-010": ("AGENTS.md", "ARCHITECTURE.md"),
    "TASK-011": ("docs/generated/v2-cutover-manifest.json", "vscode-extension"),
    "TASK-012": ("tests", "vscode-extension/test"),
}


def record_transition_completion(
    repository: Path,
    *,
    work_id: str,
    expected_source_head: str,
) -> dict[str, Any]:
    root = repository.resolve()
    if work_id != TRANSITION_RUN_ID:
        raise DevWeaveError(ErrorCode.FORBIDDEN, "Only the authorized V2 transition may be projected.")
    _require_hash(expected_source_head, "expected_source_head")
    _require_clean_repository(root)

    state = _read_json(root / WORK_ROOT / "state.json", "Legacy transition state")
    _validate_closed_state(state)
    requirements = _heading_ids(root / WORK_ROOT / "requirements.md", ("REQ", "NFR"))
    acceptance = _heading_ids(root / WORK_ROOT / "requirements.md", ("AC",))
    decisions = _decision_rows(root / WORK_ROOT / "design.md")
    tasks = _task_rows(root / WORK_ROOT / "plan.md")
    verification = _current_verification(state, expected_source_head, acceptance)
    review = _single_current_review(state, expected_source_head, acceptance)
    project = _read_json(root / ".agents/skills/devweave/assets/v2-cutover/project.json", "Staged V2 project")
    parsed_project = ProjectConfig.from_dict(project)
    if set(tasks) != set(TASK_PATHS) or set(tasks) != set(state["tasks"]):
        raise DevWeaveError(ErrorCode.CONFLICT, "Transition task projection does not match the closed state.")

    draft = RunPlanDraft.from_dict(
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": TRANSITION_RUN_ID,
            "revision": 1,
            "goal": "Deliver and certify DevWeave 2.0.0 as a Codex app-server harness.",
            "scope": state["scope"]["paths"],
            "non_goals": [
                "No V1 dual-read or mutation compatibility after cutover.",
                "No remote push, pull request, merge, branch reset, or automatic switch-back.",
                "No certification claim outside the verified Windows x64 and VS Code boundary.",
            ],
            "requirements": requirements,
            "acceptance_criteria": acceptance,
            "decisions": decisions,
            "tasks": [tasks[task_id] for task_id in sorted(tasks)],
            "verification_plan": primitive(parsed_project.verification_plan),
            "risk": "high",
            "risk_rationale": state["risk"]["rationale"],
        }
    )
    branch = _git(root, "branch", "--show-current").strip()
    if branch != f"devweave/20260825-163914-app-server-harness":
        raise DevWeaveError(ErrorCode.CONFLICT, "Transition completion must be recorded on the authorized run branch.")
    accepted_at = state["gates"]["acceptance"]["approved_at"]
    plan = new_exec_plan(
        draft,
        base_branch=state["base_source"]["branch"],
        base_ref=state["base_source"]["head"],
        run_branch=branch,
        now=state["created_at"],
    )
    for gate_id, legacy_id in (("scope", "scope"), ("design", "build"), ("acceptance", "acceptance")):
        gate = state["gates"][legacy_id]
        plan["gates"][gate_id] = {
            "status": "approved",
            "fingerprint": plan["definition_fingerprint"],
            "approved_revision": 1,
            "decided_at": gate["approved_at"],
            "commit_ref": expected_source_head,
        }
    for task_id, task in plan["tasks"].items():
        legacy = state["tasks"][task_id]
        task.update({"status": "completed", "progress": legacy["note"], "commit_ref": expected_source_head})

    findings = review["review"].get("findings", [])
    source_fingerprint = verification["source_fingerprint"]
    repository_head = _git(root, "rev-parse", "HEAD").strip()
    review_details = review["review"]
    plan.update(
        {
            "status": "completed",
            "phase": "closed",
            "verification": {
                "status": "passed",
                "evidence_ids": [verification["id"], review["id"]],
                "current_report_id": "transition",
                "reports": {
                    "transition": {
                        "acceptance_path": f"{WORK_ROOT}/acceptance.md",
                        "acceptance_sha256": _file_hash(root / WORK_ROOT / "acceptance.md"),
                        "base_branch": state["base_source"]["branch"],
                        "base_ref": state["base_source"]["head"],
                        "repository_head": repository_head,
                        "run_branch": branch,
                        "source_head": expected_source_head,
                        "source_digest": source_fingerprint,
                        "source_fingerprint": source_fingerprint,
                        "v1_export_json_sha256": _file_hash(root / "docs/generated/v1-export.json"),
                        "v1_export_markdown_sha256": _file_hash(root / "docs/generated/v1-export.md"),
                    }
                },
            },
            "review": {
                "mode": "detached_fix_reverify",
                "max_rounds": 3,
                "round": 1,
                "status": "passed",
                "finding_ids": [item["id"] for item in findings],
                "source_fingerprint": source_fingerprint,
                "reviewer_thread_id": review_details["reviewer_id"],
                "review_turn_id": review_details.get("review_turn_id") or f"transition:{review['id']}",
            },
            "completion_requested": True,
            "archive_ref": expected_source_head,
            "blockers": [],
            "applied_mutations": ["run-start", "transition-import"],
            "updated_at": accepted_at,
        }
    )
    validated = validate_exec_plan(plan)
    store = PlanStore(root)
    target = store.path_for(TRANSITION_RUN_ID, completed=True)
    if target.is_file():
        existing = validate_exec_plan(_read_json(target, "Completed transition ExecPlan"))
        if dumps(existing) == dumps(validated):
            return _result(root, target, validated, "already_recorded")
        raise DevWeaveError(ErrorCode.CONFLICT, "A different transition completion record already exists.")
    if store.path_for(TRANSITION_RUN_ID).exists():
        raise DevWeaveError(ErrorCode.CONFLICT, "An active V2 transition ExecPlan already exists.")
    store.create(validated)
    archived = store.complete(TRANSITION_RUN_ID)
    return _result(root, archived, validated, "recorded")


def _validate_closed_state(state: Any) -> None:
    if not isinstance(state, dict) or state.get("id") != TRANSITION_RUN_ID or state.get("status") != "closed":
        raise DevWeaveError(ErrorCode.BLOCKED, "Legacy transition work must be closed before projection.")
    if state.get("risk", {}).get("level") != "high":
        raise DevWeaveError(ErrorCode.CONFLICT, "Transition risk is not high.")
    if any(item.get("status") != "completed" for item in state.get("tasks", {}).values()):
        raise DevWeaveError(ErrorCode.BLOCKED, "Every transition task must be completed before projection.")
    if any(state.get("gates", {}).get(gate, {}).get("status") != "approved" for gate in ("scope", "build", "acceptance")):
        raise DevWeaveError(ErrorCode.GATE_REQUIRED, "G1, G2, and G3 must be approved before projection.")
    if state.get("knowledge_review", {}).get("disposition") not in {"promote", "no-update"}:
        raise DevWeaveError(ErrorCode.BLOCKED, "Knowledge Review must be recorded before projection.")


def _current_verification(
    state: dict[str, Any], expected_source_head: str, acceptance_ids: list[str]
) -> dict[str, Any]:
    evidence_id = state.get("last_verification", {}).get("evidence_id")
    evidence = state.get("evidence", {}).get(evidence_id)
    if not isinstance(evidence, dict):
        raise DevWeaveError(ErrorCode.BLOCKED, "Current verification evidence is missing.")
    if (
        evidence.get("status") != "passed"
        or evidence.get("observed_result") != "success"
        or evidence.get("stale")
        or not evidence.get("binds_current_source")
        or not set(acceptance_ids).issubset(evidence.get("covers", []))
    ):
        raise DevWeaveError(ErrorCode.BLOCKED, "Transition verification evidence is not current and passing.")
    if evidence.get("git_head") != expected_source_head:
        raise DevWeaveError(ErrorCode.CONFLICT, "Expected source HEAD does not match verification evidence.")
    return evidence


def _single_current_review(
    state: dict[str, Any], expected_source_head: str, acceptance_ids: list[str]
) -> dict[str, Any]:
    reviews = [
        item for item in state.get("evidence", {}).values()
        if isinstance(item, dict) and item.get("kind") == "review" and not item.get("stale")
    ]
    if len(reviews) != 1:
        raise DevWeaveError(ErrorCode.BLOCKED, "Exactly one current independent review record is required.")
    review = reviews[0]
    details = review.get("review", {})
    if (
        review.get("status") != "passed"
        or not review.get("binds_current_source")
        or review.get("git_head") != expected_source_head
        or details.get("context_mode") != "isolated_read_only"
        or details.get("result") != "passed"
        or not details.get("reviewer_id")
        or not details.get("report_sha256")
        or not set(acceptance_ids).issubset(details.get("covers", []))
    ):
        raise DevWeaveError(ErrorCode.BLOCKED, "Independent review is not current, isolated, and passing.")
    if any(item.get("severity") == "critical" for item in details.get("findings", [])):
        raise DevWeaveError(ErrorCode.BLOCKED, "Independent review contains a critical finding.")
    return review


def _task_rows(path: Path) -> dict[str, dict[str, Any]]:
    text = _read_text(path)
    matches = list(re.finditer(r"^## (TASK-\d{3}): (.+)$", text, flags=re.MULTILINE))
    result: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(matches):
        task_id, title = match.groups()
        section = text[match.end(): matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        traces = _line_values(section, "Traces")
        dependencies = _line_values(section, "Dependencies")
        result[task_id] = {
            "task_id": task_id,
            "title": title.strip(),
            "requirement_ids": [item for item in traces if item.startswith(("REQ-", "NFR-"))],
            "acceptance_ids": [item for item in traces if item.startswith("AC-")],
            "declared_paths": list(TASK_PATHS.get(task_id, ())),
            "dependencies": [] if dependencies == ["none"] else dependencies,
        }
    return result


def _decision_rows(path: Path) -> list[dict[str, str]]:
    text = _read_text(path)
    return [
        {"decision_id": decision_id, "summary": summary.strip()}
        for decision_id, summary in re.findall(r"^## (DEC-\d{3}): (.+)$", text, flags=re.MULTILINE)
    ]


def _heading_ids(path: Path, prefixes: tuple[str, ...]) -> list[str]:
    text = _read_text(path)
    expression = "|".join(re.escape(prefix) for prefix in prefixes)
    values = re.findall(rf"^## ((?:{expression})-\d{{3}}):", text, flags=re.MULTILINE)
    return list(dict.fromkeys(values))


def _line_values(section: str, label: str) -> list[str]:
    match = re.search(rf"^- {re.escape(label)}: (.+)$", section, flags=re.MULTILINE)
    if not match:
        raise DevWeaveError(ErrorCode.INVALID_VALUE, f"Transition task is missing {label}.")
    return [item.strip() for item in match.group(1).split(",") if item.strip()]


def _result(repository: Path, target: Path, plan: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "path": target.relative_to(repository).as_posix(),
        "sha256": _file_hash(target),
        "run_id": plan["run_id"],
        "source_head": plan["verification"]["reports"]["transition"]["source_head"],
    }


def _read_json(path: Path, label: str) -> Any:
    try:
        data = path.read_bytes()
        if len(data) > MAX_TRANSITION_JSON_BYTES:
            raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, f"{label} exceeds the transition JSON bound.")
        return json.loads(data.decode("utf-8"))
    except DevWeaveError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DevWeaveError(ErrorCode.INVALID_JSON, f"{label} is unavailable or invalid JSON.") from exc


def _read_text(path: Path) -> str:
    try:
        data = path.read_bytes()
        if len(data) > MAX_TRANSITION_MARKDOWN_BYTES:
            raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Transition Markdown exceeds its read bound.")
        return data.decode("utf-8")
    except DevWeaveError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise DevWeaveError(ErrorCode.NOT_FOUND, "Transition artifact is unavailable.", {"path": str(path)}) from exc


def _file_hash(path: Path) -> str:
    try:
        data = path.read_bytes().replace(b"\r\n", b"\n")
    except OSError as exc:
        raise DevWeaveError(ErrorCode.NOT_FOUND, "Transition provenance file is unavailable.", {"path": str(path)}) from exc
    return hashlib.sha256(data).hexdigest()


def _require_hash(value: str, field: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise DevWeaveError(ErrorCode.INVALID_VALUE, f"{field} must be a lowercase Git SHA-1.")


def _require_clean_repository(repository: Path) -> None:
    if _git(repository, "status", "--porcelain=v1", "--untracked-files=all"):
        raise DevWeaveError(ErrorCode.CONFLICT, "Transition completion projection requires a clean repository.")


def _git(repository: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=repository, check=True, capture_output=True,
            text=True, encoding="utf-8", errors="strict", shell=False,
        )
    except subprocess.CalledProcessError as exc:
        raise DevWeaveError(ErrorCode.COMMAND_FAILED, "Git transition preflight failed.") from exc
    return result.stdout

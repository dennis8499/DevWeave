from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

from devweave_core import (
    DevWeaveError,
    ExecutionError,
    GATES,
    KINDS,
    KNOWLEDGE_CONTENT_TYPES,
    RISK_LEVELS,
    ValidationError,
    WorkLock,
    add_evidence,
    add_waiver,
    approve_gate,
    atomic_write_json,
    bind_session,
    bootstrap_knowledge_work,
    close_work,
    create_work,
    doctor,
    find_repo_root,
    init_project,
    instructions,
    list_work,
    load_project,
    normalize_relpath,
    project_path,
    record_review,
    resolve_work,
    revise_work,
    run_verification,
    scaffold_knowledge,
    seal_knowledge,
    set_baseline_updates,
    set_knowledge_context,
    set_knowledge_plan,
    set_knowledge_review,
    set_risk,
    set_scope,
    sync_state,
    update_task,
    validate_work,
    work_knowledge_status,
)


def emit(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit(
            {
                "ok": False,
                "error": {
                    "code": "usage_error",
                    "message": message,
                    "details": {"usage": self.format_usage().strip()},
                },
            }
        )
        raise SystemExit(2)


def state_summary(
    state: dict[str, Any], repo: Path | None = None
) -> dict[str, Any]:
    tasks = state.get("tasks", {})
    evidence = state.get("evidence", {})
    stale_evidence = sorted(
        evidence_id
        for evidence_id, item in evidence.items()
        if item.get("stale")
    )
    summary = {
        "id": state["id"],
        "title": state["title"],
        "kind": state["kind"],
        "risk": state["risk"]["level"],
        "status": state["status"],
        "phase": state["phase"],
        "gates": state["gates"],
        "task_progress": {
            "completed": sum(item.get("status") == "completed" for item in tasks.values()),
            "total": len(tasks),
        },
        "evidence_progress": {
            "total": len(evidence),
            "passed": sum(item.get("status") == "passed" for item in evidence.values()),
            "failed": sum(item.get("status") == "failed" for item in evidence.values()),
            "stale": len(stale_evidence),
        },
        "stale_evidence": stale_evidence,
        "blocker": state.get("blocker"),
        "updated_at": state["updated_at"],
    }
    if repo is not None:
        summary["knowledge"] = work_knowledge_status(repo, state)
    if state.get("knowledge_profile"):
        summary["knowledge_profile"] = state["knowledge_profile"]
    return summary


def command_init(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    return {"ok": True, "project": init_project(repo), "root": str(repo)}


def command_start(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = create_work(
        repo,
        kind=args.kind,
        title=args.title,
        risk=args.risk,
        risk_rationale=args.rationale,
    )
    return {"ok": True, "work": state_summary(state, repo)}


def command_status(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    if not project_path(repo).exists():
        return {"ok": True, "initialized": False, "root": str(repo), "work_items": []}
    if args.all:
        items = list_work(repo, include_closed=args.include_closed)
        items = [
            sync_state(repo, item["id"])
            if item.get("status") != "closed"
            else item
            for item in items
        ]
        return {
            "ok": True,
            "initialized": True,
            "work_items": [state_summary(item, repo) for item in items],
        }
    if not args.work and not list_work(repo, include_closed=args.include_closed):
        return {
            "ok": True,
            "initialized": True,
            "work_items": [],
            "message": "No eligible DevWeave work item exists.",
        }
    state = resolve_work(repo, args.work, include_closed=args.include_closed)
    if state["status"] != "closed":
        state = sync_state(repo, state["id"])
    return {"ok": True, "initialized": True, "work": state_summary(state, repo)}


def command_instructions(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    state = sync_state(repo, state["id"])
    return {"ok": True, "instructions": instructions(repo, state)}


def command_validate(args: argparse.Namespace, repo: Path) -> tuple[dict[str, Any], int]:
    state = resolve_work(repo, args.work, include_closed=args.include_closed)
    if state["status"] != "closed":
        state = sync_state(repo, state["id"])
    report = validate_work(repo, state, args.gate)
    payload = {"ok": report.ok, "work": state_summary(state), "validation": report.as_dict()}
    return payload, 0 if report.ok else 2


def command_bind(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    if args.session_id:
        binding = bind_session(repo, args.session_id, state["id"])
        binding["status"] = "bound"
        guard_confirmation_required = False
    else:
        binding = {
            "work": state["id"],
            "session_id": None,
            "bound_at": None,
            "status": "awaiting_hook",
            "note": (
                "The CLI cannot observe the Codex session ID. Treat the session as bound "
                "only when the PreToolUse hook confirms it in additional context."
            ),
        }
        guard_confirmation_required = True
    return {
        "ok": True,
        "binding": binding,
        "guard_confirmation_required": guard_confirmation_required,
    }


def command_risk(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    updated = set_risk(
        repo,
        state["id"],
        args.level,
        args.rationale,
        args.downgrade_rationale,
    )
    return {"ok": True, "work": state_summary(updated)}


def command_scope(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    updated = set_scope(repo, state["id"], args.path, args.rationale)
    return {"ok": True, "work": state_summary(updated), "scope": updated["scope"]}


def command_baseline(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    updated = set_baseline_updates(repo, state["id"], args.target, args.rationale)
    return {
        "ok": True,
        "work": state_summary(updated),
        "baseline_updates": updated["baseline_updates"],
    }


def command_knowledge(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    if args.knowledge_action == "bootstrap":
        result = bootstrap_knowledge_work(repo)
        state = result["work"]
        return {
            "ok": True,
            "action": result["action"],
            "work": state_summary(state, repo) if state else None,
            "bootstrap": result["bootstrap"],
        }
    if args.knowledge_action == "status":
        state: dict[str, Any] | None = None
        if args.work:
            state = resolve_work(repo, args.work, include_closed=True)
            if state.get("status") != "closed":
                state = sync_state(repo, state["id"])
        else:
            candidates = list_work(repo)
            if len(candidates) == 1:
                state = sync_state(repo, candidates[0]["id"])
            elif len(candidates) > 1:
                state = resolve_work(repo, None)
        return {
            "ok": True,
            "work": state["id"] if state else None,
            "knowledge": work_knowledge_status(repo, state),
        }
    state = resolve_work(repo, args.work)
    if args.knowledge_action == "context":
        context = set_knowledge_context(
            repo, state["id"], args.page, args.gap
        )
        return {"ok": True, "work": state["id"], "knowledge_context": context}
    if args.knowledge_action == "review":
        review = set_knowledge_review(
            repo,
            state["id"],
            args.disposition,
            args.rationale,
        )
        refreshed = resolve_work(repo, state["id"])
        return {
            "ok": True,
            "work": state["id"],
            "knowledge_review": review,
            "knowledge": work_knowledge_status(repo, refreshed),
        }
    if args.knowledge_action == "plan":
        updates = set_knowledge_plan(
            repo,
            state["id"],
            args.upsert,
            args.delete,
            args.rationale,
        )
        return {"ok": True, "work": state["id"], "knowledge_updates": updates}
    if args.knowledge_action == "scaffold":
        scaffold = scaffold_knowledge(
            repo,
            state["id"],
            page=args.page,
            page_type=args.page_type,
            title=args.title,
            sources=args.source,
            package_name=args.package_name,
            version=args.version,
            decision_date=args.decision_date,
            decision_status=args.decision_status,
        )
        return {"ok": True, "work": state["id"], "scaffold": scaffold}
    if args.knowledge_action == "seal":
        result = seal_knowledge(repo, state["id"], args.page)
        return {"ok": True, "work": state["id"], **result}
    raise ValidationError(
        "Unknown knowledge action.", {"action": args.knowledge_action}
    )


def command_task(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    task = update_task(
        repo,
        state["id"],
        args.task,
        args.action,
        evidence=args.evidence,
        note=args.note,
    )
    return {"ok": True, "work": state["id"], "task": args.task, "state": task}


def command_evidence(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    evidence = add_evidence(
        repo,
        state["id"],
        kind=args.kind,
        status=args.status,
        summary=args.summary,
        covers=args.covers,
        tasks=args.task,
        observed_result=args.observed_result,
        binds_current_source=args.binds_current_source,
    )
    return {"ok": True, "work": state["id"], "evidence": evidence}


def command_review(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    if args.review_action != "record":
        raise ValidationError("Unknown review action.", {"action": args.review_action})
    evidence = record_review(
        repo,
        state["id"],
        reviewer_id=args.reviewer_id,
        report_file=args.report_file,
    )
    return {"ok": True, "work": state["id"], "evidence": evidence}


def command_verify(args: argparse.Namespace, repo: Path) -> tuple[dict[str, Any], int]:
    state = resolve_work(repo, args.work)
    evidence = run_verification(
        repo,
        state["id"],
        command_id=args.command,
        kind=args.kind,
        covers=args.covers,
        tasks=args.task,
        expectation=args.expect,
    )
    payload = {"ok": evidence["status"] == "passed", "work": state["id"], "evidence": evidence}
    return payload, 0 if payload["ok"] else 4


def command_waiver(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    waiver = add_waiver(
        repo,
        state["id"],
        kind=args.kind,
        target=args.target,
        reason=args.reason,
        actor=args.actor,
        gate=args.gate,
    )
    return {"ok": True, "work": state["id"], "waiver": waiver}


def command_approve(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    updated = approve_gate(repo, state["id"], args.gate, args.actor)
    return {"ok": True, "work": state_summary(updated)}


def command_revise(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    updated = revise_work(repo, state["id"], args.from_phase, args.reason)
    return {"ok": True, "work": state_summary(updated)}


def command_close(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    state = resolve_work(repo, args.work)
    updated = close_work(repo, state["id"])
    return {"ok": True, "work": state_summary(updated)}


def command_doctor(args: argparse.Namespace, repo: Path) -> tuple[dict[str, Any], int]:
    report = doctor(repo)
    return report, 0 if report["ok"] else 2


def command_project(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    return {"ok": True, "project": load_project(repo)}


def command_command(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    if not project_path(repo).exists():
        init_project(repo)
    with WorkLock(repo, "project"):
        project = load_project(repo)
        commands = project.setdefault("commands", [])
        if args.command_action == "list":
            return {"ok": True, "commands": commands, "profiles": project["verification_profiles"]}
        if args.command_action == "remove":
            before = len(commands)
            project["commands"] = [item for item in commands if item.get("id") != args.id]
            for profile in project.get("verification_profiles", {}).values():
                while args.id in profile:
                    profile.remove(args.id)
            atomic_write_json(project_path(repo), project)
            return {"ok": True, "removed": before - len(project["commands"]), "id": args.id}
        argv = list(args.argv)
        if argv and argv[0] == "--":
            argv = argv[1:]
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise ValidationError("Command argv must not be empty.")
        if args.timeout <= 0:
            raise ValidationError("Command timeout must be greater than zero.")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", args.id):
            raise ValidationError("Command ID must use letters, digits, dot, underscore, or hyphen.")
        raw_cwd = Path(args.cwd)
        if raw_cwd.is_absolute() or ".." in raw_cwd.parts:
            raise ValidationError("Command cwd must be repo-relative and cannot contain '..'.")
        command_cwd = (repo / raw_cwd).resolve()
        try:
            command_cwd.relative_to(repo.resolve())
        except ValueError as exc:
            raise ValidationError("Command cwd must stay inside the repository.") from exc
        if not command_cwd.is_dir():
            raise ValidationError("Command cwd must be an existing directory.")
        entry = {
            "id": args.id,
            "argv": argv,
            "cwd": normalize_relpath(args.cwd),
            "timeout_seconds": args.timeout,
            "required_for": sorted(set(args.required_for)),
        }
        project["commands"] = [item for item in commands if item.get("id") != args.id]
        project["commands"].append(entry)
        project["commands"].sort(key=lambda item: item["id"])
        profiles = project.setdefault(
            "verification_profiles", {level: [] for level in RISK_LEVELS}
        )
        for level in RISK_LEVELS:
            profile = profiles.setdefault(level, [])
            if level in entry["required_for"] and args.id not in profile:
                profile.append(args.id)
                profile.sort()
            if level not in entry["required_for"] and args.id in profile:
                profile.remove(args.id)
        atomic_write_json(project_path(repo), project)
        return {"ok": True, "command": entry, "profiles": profiles}


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="devweave",
        description="Deterministic state and evidence engine for the DevWeave skill.",
    )
    parser.add_argument("--repo", default=".", help="Path inside the target Git repository.")
    parser.add_argument("--json", action="store_true", help="Accepted for compatibility; output is always JSON.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.set_defaults(handler=command_init)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--kind", choices=KINDS, required=True)
    start_parser.add_argument("--title", required=True)
    start_parser.add_argument("--risk", choices=RISK_LEVELS, default="standard")
    start_parser.add_argument("--rationale", default="")
    start_parser.set_defaults(handler=command_start)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--work")
    status_parser.add_argument("--all", action="store_true")
    status_parser.add_argument("--include-closed", action="store_true")
    status_parser.set_defaults(handler=command_status)

    instructions_parser = subparsers.add_parser("instructions")
    instructions_parser.add_argument("--work")
    instructions_parser.set_defaults(handler=command_instructions)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--work")
    validate_parser.add_argument("--gate", choices=GATES)
    validate_parser.add_argument("--include-closed", action="store_true")
    validate_parser.set_defaults(handler=command_validate)

    bind_parser = subparsers.add_parser("bind")
    bind_parser.add_argument("--work")
    bind_parser.add_argument("--session-id")
    bind_parser.set_defaults(handler=command_bind)

    risk_parser = subparsers.add_parser("risk")
    risk_parser.add_argument("--work")
    risk_parser.add_argument("--level", choices=RISK_LEVELS, required=True)
    risk_parser.add_argument("--rationale", required=True)
    risk_parser.add_argument("--downgrade-rationale")
    risk_parser.set_defaults(handler=command_risk)

    scope_parser = subparsers.add_parser("scope")
    scope_parser.add_argument("--work")
    scope_parser.add_argument(
        "--path",
        action="append",
        default=[],
        required=True,
        help=(
            "Repo-relative path or glob. Repeat in one call; each call replaces "
            "the full scope set."
        ),
    )
    scope_parser.add_argument("--rationale", required=True)
    scope_parser.set_defaults(handler=command_scope)

    baseline_parser = subparsers.add_parser("baseline")
    baseline_parser.add_argument("--work")
    baseline_parser.add_argument("--target", action="append", default=[])
    baseline_parser.add_argument("--rationale", required=True)
    baseline_parser.set_defaults(handler=command_baseline)

    knowledge_parser = subparsers.add_parser("knowledge")
    knowledge_subparsers = knowledge_parser.add_subparsers(
        dest="knowledge_action", required=True
    )
    knowledge_bootstrap_parser = knowledge_subparsers.add_parser("bootstrap")
    knowledge_bootstrap_parser.set_defaults(handler=command_knowledge)
    knowledge_status_parser = knowledge_subparsers.add_parser("status")
    knowledge_status_parser.add_argument("--work")
    knowledge_status_parser.set_defaults(handler=command_knowledge)
    knowledge_context_parser = knowledge_subparsers.add_parser("context")
    knowledge_context_parser.add_argument("--work")
    knowledge_context_parser.add_argument(
        "--page", action="append", default=[], required=True
    )
    knowledge_context_parser.add_argument("--gap", action="append", default=[])
    knowledge_context_parser.set_defaults(handler=command_knowledge)
    knowledge_review_parser = knowledge_subparsers.add_parser("review")
    knowledge_review_parser.add_argument("--work")
    knowledge_review_parser.add_argument(
        "--disposition", choices=("promote", "no-update"), required=True
    )
    knowledge_review_parser.add_argument("--rationale", required=True)
    knowledge_review_parser.set_defaults(handler=command_knowledge)
    knowledge_plan_parser = knowledge_subparsers.add_parser("plan")
    knowledge_plan_parser.add_argument("--work")
    knowledge_plan_parser.add_argument("--upsert", action="append", default=[])
    knowledge_plan_parser.add_argument("--delete", action="append", default=[])
    knowledge_plan_parser.add_argument("--rationale", required=True)
    knowledge_plan_parser.set_defaults(handler=command_knowledge)
    knowledge_scaffold_parser = knowledge_subparsers.add_parser("scaffold")
    knowledge_scaffold_parser.add_argument("--work")
    knowledge_scaffold_parser.add_argument("--page", required=True)
    knowledge_scaffold_parser.add_argument(
        "--type",
        dest="page_type",
        choices=KNOWLEDGE_CONTENT_TYPES,
        required=True,
    )
    knowledge_scaffold_parser.add_argument("--title", required=True)
    knowledge_scaffold_parser.add_argument(
        "--source", action="append", default=[], required=True
    )
    knowledge_scaffold_parser.add_argument("--package-name")
    knowledge_scaffold_parser.add_argument("--version")
    knowledge_scaffold_parser.add_argument("--decision-date")
    knowledge_scaffold_parser.add_argument(
        "--decision-status",
        choices=("proposed", "accepted", "deprecated", "superseded"),
    )
    knowledge_scaffold_parser.set_defaults(handler=command_knowledge)
    knowledge_seal_parser = knowledge_subparsers.add_parser("seal")
    knowledge_seal_parser.add_argument("--work")
    knowledge_seal_parser.add_argument(
        "--page", action="append", default=[], required=True
    )
    knowledge_seal_parser.set_defaults(handler=command_knowledge)

    task_parser = subparsers.add_parser("task")
    task_parser.add_argument("action", choices=("start", "complete", "block"))
    task_parser.add_argument("--work")
    task_parser.add_argument("--task", required=True)
    task_parser.add_argument("--evidence", action="append", default=[])
    task_parser.add_argument("--note", default="")
    task_parser.set_defaults(handler=command_task)

    evidence_parser = subparsers.add_parser("evidence")
    evidence_parser.add_argument("action", choices=("add",))
    evidence_parser.add_argument("--work")
    evidence_parser.add_argument("--kind", required=True)
    evidence_parser.add_argument("--status", choices=("passed", "failed", "waived"), required=True)
    evidence_parser.add_argument("--summary", required=True)
    evidence_parser.add_argument("--covers", action="append", default=[])
    evidence_parser.add_argument("--task", action="append", default=[])
    evidence_parser.add_argument(
        "--observed-result",
        choices=("success", "failure", "neutral"),
        default="neutral",
    )
    binding_group = evidence_parser.add_mutually_exclusive_group()
    binding_group.add_argument(
        "--binds-current-source",
        action="store_true",
        dest="binds_current_source",
    )
    binding_group.add_argument(
        "--does-not-bind-current-source",
        action="store_false",
        dest="binds_current_source",
    )
    evidence_parser.set_defaults(handler=command_evidence, binds_current_source=None)

    review_parser = subparsers.add_parser(
        "review",
        help="Machine-only independent review evidence interface.",
    )
    review_subparsers = review_parser.add_subparsers(
        dest="review_action", required=True
    )
    review_record_parser = review_subparsers.add_parser("record")
    review_record_parser.add_argument("--work")
    review_record_parser.add_argument("--reviewer-id", required=True)
    review_record_parser.add_argument("--report-file", required=True)
    review_record_parser.set_defaults(handler=command_review)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--work")
    verify_parser.add_argument("--command", required=True)
    verify_parser.add_argument("--kind", required=True)
    verify_parser.add_argument("--covers", action="append", default=[])
    verify_parser.add_argument("--task", action="append", default=[])
    verify_parser.add_argument("--expect", choices=("zero", "nonzero", "any"), default="zero")
    verify_parser.set_defaults(handler=command_verify)

    waiver_parser = subparsers.add_parser("waiver")
    waiver_parser.add_argument("action", choices=("add",))
    waiver_parser.add_argument("--work")
    waiver_parser.add_argument("--kind", required=True)
    waiver_parser.add_argument("--target", default="")
    waiver_parser.add_argument("--reason", required=True)
    waiver_parser.add_argument("--actor")
    waiver_parser.add_argument("--gate", choices=GATES)
    waiver_parser.set_defaults(handler=command_waiver)

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("--work")
    approve_parser.add_argument("--gate", choices=GATES)
    approve_parser.add_argument("--actor")
    approve_parser.set_defaults(handler=command_approve)

    revise_parser = subparsers.add_parser("revise")
    revise_parser.add_argument("--work")
    revise_parser.add_argument(
        "--from",
        dest="from_phase",
        choices=("requirements", "design", "implementation"),
        required=True,
    )
    revise_parser.add_argument("--reason", required=True)
    revise_parser.set_defaults(handler=command_revise)

    close_parser = subparsers.add_parser("close")
    close_parser.add_argument("--work")
    close_parser.set_defaults(handler=command_close)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.set_defaults(handler=command_doctor)

    project_parser = subparsers.add_parser("project")
    project_parser.set_defaults(handler=command_project)

    command_parser = subparsers.add_parser("command")
    command_subparsers = command_parser.add_subparsers(dest="command_action", required=True)
    command_list = command_subparsers.add_parser("list")
    command_list.set_defaults(handler=command_command)
    command_remove = command_subparsers.add_parser("remove")
    command_remove.add_argument("--id", required=True)
    command_remove.set_defaults(handler=command_command)
    command_set = command_subparsers.add_parser("set")
    command_set.add_argument("--id", required=True)
    command_set.add_argument("--cwd", default=".")
    command_set.add_argument("--timeout", type=int, default=900)
    command_set.add_argument(
        "--required-for",
        nargs="*",
        choices=RISK_LEVELS,
        default=[],
    )
    command_set.add_argument("argv", nargs=argparse.REMAINDER)
    command_set.set_defaults(handler=command_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo = find_repo_root(args.repo)
        result = args.handler(args, repo)
        if isinstance(result, tuple):
            payload, exit_code = result
        else:
            payload, exit_code = result, 0
        emit(payload)
        return exit_code
    except DevWeaveError as exc:
        emit(
            {
                "ok": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                },
            }
        )
        return exc.exit_code
    except KeyboardInterrupt:
        emit(
            {
                "ok": False,
                "error": {"code": "interrupted", "message": "Operation interrupted."},
            }
        )
        return 130
    except Exception as exc:
        emit(
            {
                "ok": False,
                "error": {
                    "code": "internal_error",
                    "message": str(exc),
                    "type": type(exc).__name__,
                },
            }
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())

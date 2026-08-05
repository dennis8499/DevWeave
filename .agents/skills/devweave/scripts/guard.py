from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from devweave_core import (
    ARTIFACT_NAMES,
    DevWeaveError,
    bind_session,
    find_repo_root,
    load_project,
    load_session_binding,
    project_path,
    path_matches_scope,
    resolve_work,
    sync_state,
)


FORBIDDEN_SHELL_OPERATORS = re.compile(r"(?:&&|\|\||[;|><]|\r|\n)")
PATCH_PATH = re.compile(
    r"^\*\*\*\s+(?:(?:Add|Update|Delete)\s+File:|Move to:)\s+(.+?)\s*$",
    re.MULTILINE,
)
WORK_ARGUMENT = re.compile(
    r"(?:^|\s)--work(?:\s+|=)(?P<quote>[\"']?)(?P<work>[A-Za-z0-9._-]+)(?P=quote)(?:\s|$)"
)
READ_ONLY_PREFIXES = (
    "git status",
    "git diff",
    "git log",
    "git show",
    "git ls-files",
    "git rev-parse",
    "git branch --show-current",
    "rg ",
    "rg --files",
    "get-content ",
    "get-childitem ",
    "select-string ",
    "test-path ",
    "resolve-path ",
    "get-command ",
    "where.exe ",
    "python --version",
    "python3 --version",
    "py -3 --version",
    "git --version",
)


def allow_with_context(message: str | None = None) -> dict[str, Any] | None:
    if not message:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }


def deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _command(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    value = tool_input.get("command", "")
    return value if isinstance(value, str) else ""


def _is_devweave_cli(command: str) -> bool:
    if FORBIDDEN_SHELL_OPERATORS.search(command):
        return False
    tokens = [token.strip("\"'") for token in _tokens(command)]
    if len(tokens) < 2:
        return False
    launcher = Path(tokens[0]).name.lower()
    if not (
        launcher in ("py", "py.exe")
        or re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", launcher)
    ):
        return False
    script_indexes = [
        index
        for index, token in enumerate(tokens[1:], start=1)
        if Path(token.replace("\\", "/")).name.lower() == "devweave.py"
    ]
    if len(script_indexes) != 1:
        return False
    return all(
        re.fullmatch(r"-(?:B|u|3(?:\.\d+)?)", token) is not None
        for token in tokens[1 : script_indexes[0]]
    )


def _work_from_command(command: str) -> str | None:
    match = WORK_ARGUMENT.search(command)
    return match.group("work") if match else None


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return []


def _matches_configured_command(repo: Path, command: str) -> bool:
    try:
        project = load_project(repo)
    except DevWeaveError:
        return False
    tokens = [token.strip("\"'") for token in _tokens(command)]
    if not tokens:
        return False
    for configured in project.get("commands", []):
        argv = configured.get("argv", [])
        if tokens == argv:
            return True
    return False


def _is_read_only(repo: Path, command: str) -> bool:
    if FORBIDDEN_SHELL_OPERATORS.search(command):
        return False
    lowered = command.strip().lower()
    return any(lowered == prefix.rstrip() or lowered.startswith(prefix) for prefix in READ_ONLY_PREFIXES)


def _patch_paths(command: str, repo: Path) -> list[str]:
    paths: list[str] = []
    for match in PATCH_PATH.findall(command):
        path = match.strip().replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        candidate = Path(path)
        resolved = candidate.resolve() if candidate.is_absolute() else (repo / candidate).resolve()
        try:
            path = resolved.relative_to(repo.resolve()).as_posix()
        except ValueError:
            path = "../__outside_repository__"
        paths.append(path)
    return paths


def _allowed_artifact_path(work_id: str, path: str) -> bool:
    base = f".devweave/work-items/{work_id}/"
    if not path.startswith(base):
        return False
    relative = path[len(base) :]
    return relative in ARTIFACT_NAMES


def _knowledge_path(path: str, root: str) -> bool:
    normalized_root = root.strip("/").replace("\\", "/").lower()
    normalized = path.replace("\\", "/").lower()
    return normalized == normalized_root or normalized.startswith(normalized_root + "/")


def _mentions_knowledge_path(command: str, root: str) -> bool:
    normalized = command.replace("\\", "/").lower()
    target = root.strip("/").replace("\\", "/").lower()
    return bool(re.search(rf"(?<![A-Za-z0-9_.-]){re.escape(target)}(?:/|\b)", normalized))


def _allow_patch_for_state(
    state: dict[str, Any], paths: list[str], knowledge_root: str = "wiki"
) -> bool:
    if not paths:
        return False
    build_ready = state["gates"]["build"].get("status") == "approved"
    updates = state.get("knowledge_updates", {})
    allowed_knowledge = set(updates.get("upserts", [])) | set(
        updates.get("deletes", [])
    ) | set(updates.get("coupled", []))
    for path in paths:
        if path.startswith("../") or Path(path).is_absolute():
            return False
        if _allowed_artifact_path(state["id"], path):
            continue
        if path.startswith(".devweave/baseline/"):
            if build_ready and state["phase"] in ("verification", "acceptance_review"):
                continue
            return False
        if path.startswith(".devweave/"):
            return False
        if _knowledge_path(path, knowledge_root):
            if (
                "base_knowledge" in state
                and build_ready
                and state.get("phase") in ("verification", "acceptance_review")
                and path in allowed_knowledge
            ):
                continue
            return False
        if not build_ready:
            return False
        in_scope = path_matches_scope(path, state.get("scope", {}).get("paths", []))
        waived = any(
            waiver.get("kind") == "out-of-scope"
            and waiver.get("target") == path
            and waiver.get("reason", "").strip()
            for waiver in state.get("waivers", [])
        )
        if not in_scope and not waived:
            return False
    return True


def handle_hook(payload: dict[str, Any], repo: Path | None = None) -> dict[str, Any] | None:
    cwd = payload.get("cwd") or os.getcwd()
    try:
        repo = repo or find_repo_root(cwd)
    except DevWeaveError:
        return None
    if not project_path(repo).exists():
        return None
    try:
        project = load_project(repo)
    except DevWeaveError as exc:
        return deny(f"DevWeave 專案設定無法讀取：{exc.message}")
    if not project.get("managed", False):
        return None

    session_id = str(payload.get("session_id") or "")
    tool_name = str(payload.get("tool_name") or "")
    command = _command(payload)

    if tool_name == "Bash" and _is_devweave_cli(command):
        if re.search(r"(?:^|\s)bind(?:\s|$)", command):
            work_id = _work_from_command(command)
            try:
                state = resolve_work(repo, work_id)
                if not session_id:
                    return deny("Codex 未提供 session ID，無法綁定 DevWeave 工作項。")
                bind_session(repo, session_id, state["id"])
                return allow_with_context(
                    f"目前 Codex session 已綁定 DevWeave 工作項 {state['id']}。"
                )
            except DevWeaveError as exc:
                return deny(f"無法綁定 DevWeave 工作項：{exc.message}")
        return None

    binding = load_session_binding(repo, session_id) if session_id else None
    state: dict[str, Any] | None = None
    if binding:
        try:
            state = sync_state(repo, binding["work"])
            if state.get("status") == "closed":
                state = None
        except (DevWeaveError, KeyError):
            state = None

    if tool_name == "Bash":
        if _is_read_only(repo, command):
            return None
        if state is None:
            return deny(
                "此 repo 已由 DevWeave 管理。請先用 $devweave 建立或選擇工作項，"
                "再執行可能修改專案的命令。"
            )
        if _matches_configured_command(repo, command):
            return None
        if _mentions_knowledge_path(command, project["knowledge"]["root"]):
            return deny(
                "Wiki 寫入必須在 verification/acceptance 階段透過已規劃的精確路徑；"
                "shell 命令無法可靠驗證路徑，請使用 patch/edit/write 或 DevWeave knowledge CLI。"
            )
        if state["gates"]["build"].get("status") != "approved":
            return deny(
                f"工作項 {state['id']} 尚未通過 G2 設計與開發核准；"
                "目前只允許唯讀或已設定的驗證命令。"
            )
        return None

    if tool_name in ("apply_patch", "Edit", "Write"):
        if state is None:
            return deny(
                "此 repo 已由 DevWeave 管理。Codex 寫入前必須先綁定 active work item。"
            )
        paths = _patch_paths(command, repo)
        if not _allow_patch_for_state(
            state, paths, project["knowledge"]["root"]
        ):
            return deny(
                f"工作項 {state['id']} 的目前 gate 不允許這次寫入。"
                "G2 前僅能修改該工作項的 Markdown artifacts；"
                "living baseline 與已規劃 Wiki pages 只能在驗證階段更新。"
            )
        return None

    return None


def _read_hook_payload() -> dict[str, Any]:
    raw = sys.stdin.buffer.read()
    return json.loads(raw.decode("utf-8"))


def _write_hook_json(value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def main() -> int:
    try:
        payload = _read_hook_payload()
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        _write_hook_json(deny(f"DevWeave guard 無法解析 hook input：{exc}"))
        return 0
    try:
        result = handle_hook(payload)
    except Exception as exc:
        result = deny(f"DevWeave guard 執行失敗並採取 fail-closed：{type(exc).__name__}: {exc}")
    if result is not None:
        _write_hook_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

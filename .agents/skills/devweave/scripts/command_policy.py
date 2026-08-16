"""Single-source command policy evaluation for DevWeave.

The module deliberately owns policy predicates that used to be duplicated by
the Guard, verification runner, and G3 validator.  It has no DevWeave ledger
side effects; callers provide the context and persist the returned decision or
plan through the normal typed core paths.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shlex
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


POLICY_VERSION = 2
COMMAND_WRITES = ("none", "generated", "tracked-artifact")
PHASE_ORDER = {
    "requirements": 0,
    "scope_review": 1,
    "design": 2,
    "build_review": 3,
    "implementation": 4,
    "verification": 5,
    "acceptance_review": 6,
    "closed": 7,
}
RISK_ORDER = {"low": 0, "standard": 1, "high": 2}
EXECUTOR_CHANNEL = "devweave_executor"
READ_ONLY_CHANNEL = "read_only_direct"


class PolicyError(ValueError):
    """Raised when an input cannot be safely normalized as policy."""


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: str
    message: str
    execution_channel: str
    command_id: str | None = None
    policy_digest: str | None = None
    command_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "message": self.message,
            "execution_channel": self.execution_channel,
            "command_id": self.command_id,
            "policy_digest": self.policy_digest,
            "command_digest": self.command_digest,
        }


@dataclass(frozen=True)
class ReadOnlyDecision:
    allowed: bool
    reason_code: str
    argv: tuple[str, ...] = ()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _repo_rel(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise PolicyError(f"{field} must be a string")
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return "."
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:($|/)", normalized):
        raise PolicyError(f"{field} must be repository-relative")
    if ".." in Path(normalized).parts:
        raise PolicyError(f"{field} must not contain '..'")
    return normalized


def _string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PolicyError(f"{field} must be a string array")
    return list(value)


def _path_list(value: Any, *, field: str) -> list[str]:
    return [_repo_rel(item, field=field) for item in _string_list(value, field=field)]


def _normalize_command(command: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    if not isinstance(command, Mapping):
        raise PolicyError(f"commands[{index}] must be an object")
    command_id = command.get("id")
    if not isinstance(command_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", command_id):
        raise PolicyError(f"commands[{index}].id is invalid")
    argv = _string_list(command.get("argv"), field=f"commands[{index}].argv")
    if not argv or any(not item for item in argv):
        raise PolicyError(f"commands[{index}].argv must not be empty")
    cwd = _repo_rel(command.get("cwd", "."), field=f"commands[{index}].cwd")
    writes = command.get("writes", "none")
    if writes not in COMMAND_WRITES:
        raise PolicyError(
            f"commands[{index}].writes must be one of {', '.join(COMMAND_WRITES)}"
        )
    outputs = _path_list(command.get("outputs", []), field=f"commands[{index}].outputs")
    affected = _path_list(
        command.get("affected_paths", []),
        field=f"commands[{index}].affected_paths",
    )
    depends_on = _string_list(
        command.get("depends_on", []), field=f"commands[{index}].depends_on"
    )
    release_only = command.get("release_only", False)
    if not isinstance(release_only, bool):
        raise PolicyError(f"commands[{index}].release_only must be boolean")
    timeout = command.get("timeout_seconds", command.get("timeout", 60))
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise PolicyError(f"commands[{index}].timeout_seconds must be positive")
    expected = command.get("expected_success_exit_codes", [0])
    if (
        not isinstance(expected, list)
        or not expected
        or any(isinstance(item, bool) or not isinstance(item, int) for item in expected)
    ):
        raise PolicyError(
            f"commands[{index}].expected_success_exit_codes must be an integer array"
        )
    allowed_risk = command.get("allowed_risk", ["low", "standard", "high"])
    if not isinstance(allowed_risk, list) or any(item not in RISK_ORDER for item in allowed_risk):
        raise PolicyError(f"commands[{index}].allowed_risk is invalid")
    # Read-only diagnostics may run while gathering evidence; write commands
    # are independently gated by the current G2 status.
    min_phase = command.get("min_phase", "requirements")
    if min_phase not in PHASE_ORDER:
        raise PolicyError(f"commands[{index}].min_phase is invalid")
    exclusive_group = command.get("exclusive_group")
    if exclusive_group is not None and not isinstance(exclusive_group, str):
        raise PolicyError(f"commands[{index}].exclusive_group must be a string or null")
    env_allowlist = command.get("env_allowlist", [])
    env_allowlist = _string_list(env_allowlist, field=f"commands[{index}].env_allowlist")
    network = command.get("network", "deny")
    if network not in ("deny", "allow"):
        raise PolicyError(f"commands[{index}].network must be deny or allow")
    normalized = copy.deepcopy(dict(command))
    normalized.update(
        {
            "id": command_id,
            "argv": argv,
            "cwd": cwd,
            "writes": writes,
            "outputs": outputs,
            "affected_paths": affected,
            "depends_on": depends_on,
            "release_only": release_only,
            "timeout_seconds": timeout,
            "expected_success_exit_codes": sorted(set(expected)),
            "allowed_risk": sorted(set(allowed_risk), key=lambda item: RISK_ORDER[item]),
            "min_phase": min_phase,
            "exclusive_group": exclusive_group,
            "env_allowlist": sorted(set(env_allowlist)),
            "network": network,
        }
    )
    if "required_for" in command:
        normalized["required_for"] = _string_list(
            command["required_for"], field=f"commands[{index}].required_for"
        )
    if "resolved_executable" in command and not isinstance(command["resolved_executable"], str):
        raise PolicyError(f"commands[{index}].resolved_executable must be a string")
    if "executable_sha256" in command and not isinstance(command["executable_sha256"], str):
        raise PolicyError(f"commands[{index}].executable_sha256 must be a string")
    return normalized


def normalize_project_policy(project: Mapping[str, Any], repo: Path | None = None) -> dict[str, Any]:
    """Validate and return a canonical, detached v2 project policy."""

    if not isinstance(project, Mapping):
        raise PolicyError("project policy must be an object")
    if project.get("command_policy_version") != POLICY_VERSION:
        raise PolicyError("project command_policy_version must be 2; legacy fallback is forbidden")
    raw_commands = project.get("commands")
    if not isinstance(raw_commands, list):
        raise PolicyError("project.commands must be an array")
    commands = [_normalize_command(command, index=index) for index, command in enumerate(raw_commands)]
    ids = [command["id"] for command in commands]
    if len(ids) != len(set(ids)):
        raise PolicyError("project command IDs must be unique")
    trusted = project.get("trusted_executables", [])
    if not isinstance(trusted, list) or not all(isinstance(item, Mapping) for item in trusted):
        raise PolicyError("project.trusted_executables must be an object array")
    trusted_normalized: list[dict[str, Any]] = []
    for index, item in enumerate(trusted):
        entry = dict(item)
        path = entry.get("path", entry.get("resolved_executable"))
        digest = entry.get("sha256", entry.get("executable_sha256"))
        if not isinstance(path, str) or not path:
            raise PolicyError(f"trusted_executables[{index}].path is required")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise PolicyError(f"trusted_executables[{index}].sha256 must be a SHA-256 hex digest")
        trusted_normalized.append(
            {
                **entry,
                "path": str(Path(path).resolve()),
                "sha256": digest.lower(),
            }
        )
    profiles = project.get("verification_profiles", {})
    if not isinstance(profiles, Mapping):
        raise PolicyError("verification_profiles must be an object")
    normalized_profiles: dict[str, list[str]] = {}
    for profile, values in profiles.items():
        if profile not in RISK_ORDER:
            raise PolicyError(f"verification profile {profile!r} is invalid")
        values = _string_list(values, field=f"verification_profiles.{profile}")
        normalized_profiles[profile] = list(dict.fromkeys(values))
    normalized = copy.deepcopy(dict(project))
    normalized.update(
        {
            "command_policy_version": POLICY_VERSION,
            "trusted_executables": trusted_normalized,
            "commands": commands,
            "verification_profiles": normalized_profiles,
        }
    )
    return normalized


def policy_digest(project_or_policy: Mapping[str, Any]) -> str:
    """Return the deterministic digest for a normalized or raw policy object."""

    if not isinstance(project_or_policy, Mapping):
        raise PolicyError("policy digest input must be an object")
    value = copy.deepcopy(dict(project_or_policy))
    if value.get("command_policy_version") == POLICY_VERSION:
        try:
            value = normalize_project_policy(value)
        except PolicyError:
            # Digesting a malformed candidate is useful to mutation validation;
            # the caller still decides whether to reject it.
            value = copy.deepcopy(dict(project_or_policy))
    return f"sha256:{_digest(value)}"


def command_definition_digest(command: Mapping[str, Any]) -> str:
    if not isinstance(command, Mapping):
        raise PolicyError("command definition must be an object")
    return f"sha256:{_digest(dict(command))}"


def _reject_shell_syntax(command: str) -> str | None:
    if not isinstance(command, str) or not command.strip():
        return "empty_command"
    if any(
        (character.isspace() and character not in " \t")
        or (unicodedata.category(character).startswith("Z") and character not in " \t")
        for character in command
    ):
        return "unsafe_whitespace"
    forbidden = ("&", "|", ";", ">", "<", "`", "(", ")", "{", "}", "^", "!", "%")
    if any(character in command for character in forbidden):
        return "shell_operator_or_expansion"
    if "$" in command:
        return "command_substitution_or_variable"
    return None


def _safe_argument(token: str) -> bool:
    if not token or any(character in token for character in "&|;><`$%{}()\r\n"):
        return False
    return not any(
        (unicodedata.category(character).startswith("Z") and character not in " \t")
        or (character.isspace() and character not in " \t")
        for character in token
    )


def _is_flag(token: str) -> bool:
    return token.startswith("-")


def _allow_flags(tokens: Sequence[str], allowed: set[str], *, value_flags: set[str] = set()) -> bool:
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return all(_safe_argument(item) for item in tokens[index + 1 :])
        if _is_flag(token):
            name = token.split("=", 1)[0]
            if name not in allowed:
                return False
            if name in value_flags and "=" not in token:
                index += 1
                if index >= len(tokens) or not _safe_argument(tokens[index]):
                    return False
        elif not _safe_argument(token):
            return False
        index += 1
    return True


def _safe_git(tokens: list[str]) -> bool:
    if not tokens or tokens[0].lower() not in ("git", "git.exe"):
        return False
    if len(tokens) == 2 and tokens[1] == "--version":
        return True
    if len(tokens) < 2:
        return False
    subcommand = tokens[1].lower()
    args = tokens[2:]
    if subcommand == "status":
        return _allow_flags(
            args,
            {"--short", "--porcelain", "--branch", "--untracked-files", "--ignored", "--ahead-behind", "--no-renames", "--renames"},
            value_flags={"--untracked-files", "--ignored"},
        )
    if subcommand == "diff":
        if any(item in ("--output", "--ext-diff", "--textconv") or item.startswith(("--output=", "--config=", "-c")) for item in args):
            return False
        return _allow_flags(
            args,
            {"--no-ext-diff", "--no-textconv", "--stat", "--shortstat", "--name-only", "--name-status", "--cached", "--staged", "--check", "--color"},
            value_flags={"--color"},
        )
    if subcommand == "log":
        return _allow_flags(
            args,
            {"--oneline", "--decorate", "--stat", "--graph", "--all", "--first-parent", "-n", "--max-count", "--format", "--pretty"},
            value_flags={"-n", "--max-count", "--format", "--pretty"},
        )
    if subcommand == "show":
        return _allow_flags(
            args,
            {"--stat", "--name-only", "--name-status", "--oneline", "--format", "--pretty"},
            value_flags={"--format", "--pretty"},
        )
    if subcommand == "ls-files":
        return _allow_flags(
            args,
            {"--cached", "--deleted", "--modified", "--others", "--exclude-standard", "--stage", "--eol", "--full-name"},
        )
    if subcommand == "rev-parse":
        return _allow_flags(
            args,
            {"--show-toplevel", "--show-prefix", "--is-inside-work-tree", "--git-dir", "--git-common-dir"},
        )
    if subcommand == "branch":
        return args == ["--show-current"]
    return False


def _safe_rg(tokens: list[str]) -> bool:
    if not tokens or tokens[0].lower() not in ("rg", "rg.exe"):
        return False
    args = tokens[1:]
    if not args:
        return False
    if any(item == "--pre" or item == "--pre-glob" or item.startswith(("--pre=", "--pre-glob=")) for item in args):
        return False
    return _allow_flags(
        args,
        {"--files", "--hidden", "--no-hidden", "--no-ignore", "--glob", "-g", "--glob-case-insensitive", "-n", "--line-number", "-F", "--fixed-strings", "-i", "--ignore-case", "-m", "--max-count", "-t", "--type", "--type-not", "--no-messages"},
        value_flags={"--glob", "-g", "-m", "--max-count", "-t", "--type", "--type-not"},
    )


def _safe_powershell(tokens: list[str]) -> bool:
    if not tokens:
        return False
    command = tokens[0].lower()
    allowed_commands = {
        "get-content": {"-path", "-literalpath", "-raw", "-totalcount", "-tail", "-encoding", "-readcount"},
        "get-childitem": {"-path", "-literalpath", "-filter", "-recurse", "-depth", "-file", "-directory", "-force", "-name"},
        "select-string": {"-path", "-literalpath", "-pattern", "-simplematch", "-casesensitive", "-list", "-context", "-quiet"},
        "test-path": {"-path", "-literalpath", "-pathtype", "-isvalid", "-filter"},
        "resolve-path": {"-path", "-literalpath", "-relative", "-type"},
        "get-command": {"-name", "-module", "-listimported", "-all"},
        "where.exe": set(),
    }
    allowed = allowed_commands.get(command)
    if allowed is None:
        return False
    for token in tokens[1:]:
        if token.startswith("-") and token.lower().split("=", 1)[0] not in allowed:
            return False
        if not _safe_argument(token):
            return False
    return True


def parse_read_only_argv(command: str) -> tuple[str, ...]:
    reason = _reject_shell_syntax(command)
    if reason:
        raise PolicyError(reason)
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as exc:
        raise PolicyError("unparseable_shell_argv") from exc
    if not tokens or any(not _safe_argument(token) for token in tokens):
        raise PolicyError("unsafe_argv_token")
    executable = tokens[0]
    if "/" in executable or "\\" in executable or ":" in executable:
        raise PolicyError("noncanonical_executable")
    if _safe_git(tokens) or _safe_rg(tokens) or _safe_powershell(tokens):
        return tuple(tokens)
    if tokens in (["python", "--version"], ["python3", "--version"], ["py", "-3", "--version"], ["git", "--version"]):
        return tuple(tokens)
    raise PolicyError("unknown_read_only_argv")


def evaluate_read_only(command: str) -> ReadOnlyDecision:
    try:
        argv = parse_read_only_argv(command)
    except PolicyError as exc:
        return ReadOnlyDecision(False, str(exc))
    return ReadOnlyDecision(True, "read_only_argv_allowed", argv)


def shell_syntax_safe(command: str) -> bool:
    """Return whether the payload has no shell operator/substitution syntax."""

    return _reject_shell_syntax(command) is None


def _context_value(context: Mapping[str, Any], key: str, default: Any = None) -> Any:
    value = context.get(key, default)
    return value


def _normalize_requested_cwd(value: Any) -> str:
    if value is None:
        return "."
    return _repo_rel(value, field="requested cwd")


def _deny(
    reason: str,
    message: str,
    *,
    channel: str = "deny",
    command_id: str | None = None,
    policy: str | None = None,
    command_digest: str | None = None,
) -> PolicyDecision:
    return PolicyDecision(False, reason, message, channel, command_id, policy, command_digest)


def evaluate(context: Mapping[str, Any]) -> PolicyDecision:
    """Evaluate a read-only payload or configured execution request.

    The function is intentionally total for untrusted input: malformed context
    returns a deny decision rather than raising into an allow fallback.
    """

    try:
        if not isinstance(context, Mapping):
            return _deny("invalid_policy_context", "Policy context must be an object.")
        shell_command = _context_value(context, "shell_command")
        if shell_command is not None:
            read_only = evaluate_read_only(str(shell_command))
            if read_only.allowed:
                return PolicyDecision(True, read_only.reason_code, "Read-only argv is allowlisted.", READ_ONLY_CHANNEL)
            return _deny(read_only.reason_code, "Shell payload is not a safe read-only argv.")

        command = _context_value(context, "command")
        if command is None:
            return _deny("unregistered_command", "Unregistered command must use a typed DevWeave policy.")
        if not isinstance(command, Mapping):
            return _deny("invalid_command_definition", "Configured command definition is invalid.")
        command_id = command.get("id") if isinstance(command.get("id"), str) else None
        command_digest = command_definition_digest(command)
        policy = _context_value(context, "current_policy_digest")
        if _context_value(context, "execution_channel", "bash") != EXECUTOR_CHANNEL:
            return _deny(
                "configured_command_requires_executor",
                "Configured verification commands must run through devweave verify.",
                command_id=command_id,
                policy=policy,
                command_digest=command_digest,
            )
        if not bool(_context_value(context, "session_bound", False)):
            return _deny("session_binding_required", "Configured command requires a bound Work Item session.", command_id=command_id, policy=policy, command_digest=command_digest)
        requested_argv = list(_context_value(context, "argv", []))
        configured_argv = list(command.get("argv", []))
        if requested_argv != configured_argv:
            return _deny("argv_mismatch", "Requested argv does not match the configured command.", command_id=command_id, policy=policy, command_digest=command_digest)
        requested_cwd = _normalize_requested_cwd(_context_value(context, "cwd", "."))
        configured_cwd = _normalize_requested_cwd(command.get("cwd", "."))
        if requested_cwd != configured_cwd:
            return _deny("cwd_mismatch", "Requested cwd does not match the canonical command cwd.", command_id=command_id, policy=policy, command_digest=command_digest)
        phase = _context_value(context, "phase", "requirements")
        if phase not in PHASE_ORDER or PHASE_ORDER[phase] < PHASE_ORDER.get(command.get("min_phase", "implementation"), 99):
            return _deny("phase_not_allowed", "Current phase is before the command minimum phase.", command_id=command_id, policy=policy, command_digest=command_digest)
        work_item = _context_value(context, "work_item", {}) or {}
        risk = work_item.get("risk", "standard") if isinstance(work_item, Mapping) else "standard"
        allowed_risk = command.get("allowed_risk", ["low", "standard", "high"])
        if risk not in allowed_risk:
            return _deny("risk_not_allowed", "Work Item risk is not allowed by the command policy.", command_id=command_id, policy=policy, command_digest=command_digest)
        writes = command.get("writes", "none")
        gate_status = _context_value(context, "gate_status", "pending")
        if writes != "none" and gate_status not in ("approved", "build_approved", "current"):
            return _deny("writes_require_g2", "Commands with writes require a current G2 approval.", command_id=command_id, policy=policy, command_digest=command_digest)
        if command.get("release_only") and not _context_value(context, "release_stage"):
            return _deny("release_context_required", "Release-only commands require explicit release context.", command_id=command_id, policy=policy, command_digest=command_digest)
        expected_policy = command.get("policy_digest")
        if expected_policy and policy and expected_policy != policy:
            return _deny("policy_digest_mismatch", "Command policy digest is stale.", command_id=command_id, policy=policy, command_digest=command_digest)
        return PolicyDecision(True, "configured_command_allowed", "Configured command admitted by the shared policy evaluator.", EXECUTOR_CHANNEL, command_id, policy, command_digest)
    except Exception as exc:
        return _deny("policy_evaluation_error", f"Policy evaluation failed closed: {type(exc).__name__}")


def _path_matches(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/").lstrip("./")
    pattern = pattern.replace("\\", "/").lstrip("./")
    if pattern.endswith("/**"):
        return path == pattern[:-3].rstrip("/") or path.startswith(pattern[:-2].rstrip("/") + "/")
    return path == pattern or path.startswith(pattern.rstrip("/") + "/")


def reconcile_changed_paths(
    before: Mapping[str, str],
    after: Mapping[str, str],
    declared_outputs: Sequence[str],
    writes: str,
) -> dict[str, Any]:
    changed = sorted(
        set(before) ^ set(after)
        | {path for path in set(before) & set(after) if before[path] != after[path]}
    )
    undeclared = sorted(
        path
        for path in changed
        if writes == "none" or not any(_path_matches(path, pattern) for pattern in declared_outputs)
    )
    return {
        "actual_changed_paths": changed,
        "undeclared_paths": undeclared,
        "violation": bool(undeclared),
        "reason": "undeclared_writes" if undeclared else "effects_within_policy",
    }


def _profile_commands(project: Mapping[str, Any], profile: str) -> list[str]:
    profiles = project.get("verification_profiles", {})
    if isinstance(profiles, Mapping) and isinstance(profiles.get(profile), list):
        return list(profiles[profile])
    return [
        command["id"]
        for command in project.get("commands", [])
        if profile in command.get("required_for", [])
    ]


def _command_map(project: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in project.get("commands", []):
        if isinstance(item, Mapping) and isinstance(item.get("id"), str):
            result[item["id"]] = dict(item)
    return result


def build_effective_plan(
    project: Mapping[str, Any],
    work_item: Mapping[str, Any],
    *,
    profile: str,
    affected_paths: Sequence[str] = (),
    release_stage: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic selection/dependency/stage plan without I/O."""

    commands = _command_map(project)
    policy = policy_digest(project)
    required = _profile_commands(project, profile)
    skipped: list[dict[str, str]] = []
    not_applicable: list[dict[str, str]] = []
    selected: list[str] = []
    selected_set: set[str] = set()
    affected = list(affected_paths)

    def mark_skip(command_id: str, reason: str) -> None:
        if not any(item["id"] == command_id for item in skipped):
            skipped.append({"id": command_id, "reason": reason})

    def visit(command_id: str, *, dependency: bool = False) -> bool:
        if command_id in selected_set:
            return True
        command = commands.get(command_id)
        if command is None:
            mark_skip(command_id, "unknown-command")
            return False
        if command.get("release_only") and not release_stage:
            mark_skip(command_id, "release-only")
            return False
        for dependency_id in command.get("depends_on", []):
            if not visit(dependency_id, dependency=True):
                mark_skip(command_id, f"release-only-dependency:{dependency_id}" if commands.get(dependency_id, {}).get("release_only") else f"dependency-not-selected:{dependency_id}")
                return False
        if affected and not dependency and profile != "high" and not command.get("affected_paths"):
            mark_skip(command_id, "legacy-unclassified" if "writes" not in command else "no-affected-path-intersection")
            return False
        if affected and not dependency and profile != "high" and command.get("affected_paths") and not any(
            _path_matches(path, pattern) or _path_matches(pattern, path)
            for path in affected
            for pattern in command["affected_paths"]
        ):
            not_applicable.append({"id": command_id, "reason": "no-affected-path-intersection"})
            return False
        selected_set.add(command_id)
        selected.append(command_id)
        return True

    for command_id in required:
        visit(command_id)

    dependency_closure = {
        command_id: sorted(commands[command_id].get("depends_on", []))
        for command_id in selected
        if command_id in commands
    }
    stages: dict[str, int] = {}

    def stage(command_id: str, visiting: set[str] | None = None) -> int:
        visiting = visiting or set()
        if command_id in stages:
            return stages[command_id]
        if command_id in visiting:
            raise PolicyError("dependency_cycle")
        visiting.add(command_id)
        dependencies = [item for item in commands[command_id].get("depends_on", []) if item in selected_set]
        value = max((stage(item, visiting) + 1 for item in dependencies), default=0)
        stages[command_id] = value
        visiting.remove(command_id)
        return value

    for command_id in selected:
        stage(command_id)
    command_entries: dict[str, dict[str, Any]] = {}
    for command_id in selected:
        command = commands[command_id]
        command_entries[command_id] = {
            "definition_digest": command_definition_digest(command),
            "stage": stages[command_id],
            "depends_on": list(command.get("depends_on", [])),
            "writes": command.get("writes", "none"),
            "outputs": list(command.get("outputs", [])),
            "exclusive_group": command.get("exclusive_group"),
            "expected_success_exit_codes": list(command.get("expected_success_exit_codes", [0])),
            "gate_eligibility": "zero-only",
        }
    # A shared output boundary is exclusive even when the project omitted an
    # explicit group.  This is derived into the frozen plan so the runner and
    # G3 consume the same scheduling decision.
    for left_index, left_id in enumerate(selected):
        left_outputs = command_entries[left_id]["outputs"]
        for right_id in selected[left_index + 1 :]:
            right_outputs = command_entries[right_id]["outputs"]
            shared = any(
                _path_matches(left, right) or _path_matches(right, left)
                for left in left_outputs
                for right in right_outputs
            )
            if shared:
                group = (
                    command_entries[left_id].get("exclusive_group")
                    or command_entries[right_id].get("exclusive_group")
                    or "outputs:" + ",".join(sorted(set(left_outputs + right_outputs)))
                )
                command_entries[left_id]["exclusive_group"] = group
                command_entries[right_id]["exclusive_group"] = group
    body: dict[str, Any] = {
        "schema_version": 1,
        "policy_version": POLICY_VERSION,
        "project_policy_digest": policy,
        "profile": profile,
        "risk": work_item.get("risk", profile),
        "required_commands": list(required),
        "selected_commands": sorted(selected),
        "skipped": sorted(skipped, key=lambda item: item["id"]),
        "not_applicable": sorted(not_applicable, key=lambda item: item["id"]),
        "dependency_closure": dependency_closure,
        "commands": command_entries,
        "source_fingerprint_at_plan": work_item.get("source_fingerprint"),
        "release_stage": release_stage,
        "selection_basis_paths": list(affected_paths),
    }
    plan_id = "plan-" + _digest(body)[:16]
    body["plan_id"] = plan_id
    body["plan_digest"] = f"sha256:{_digest(body)}"
    return body


def derive_evidence_eligibility(plan: Mapping[str, Any], observation: Mapping[str, Any]) -> dict[str, Any]:
    """Derive gate eligibility from a recorded observation; callers cannot set it."""

    def result(value: bool, reason: str) -> dict[str, Any]:
        return {"gate_eligible": value, "eligibility_reason": reason}

    command_id = observation.get("command_id")
    if observation.get("expectation", "zero") != "zero":
        return result(False, "expectation_not_zero_only")
    command = (plan.get("commands", {}) or {}).get(command_id)
    if not isinstance(command, Mapping):
        return result(False, "command_not_in_effective_plan")
    if observation.get("evidence_kind") in ("reproduction", "diagnostic"):
        return result(False, "evidence_kind_not_gate_eligible")
    if observation.get("status") != "passed":
        return result(False, "execution_not_passed")
    if observation.get("execution_channel") != EXECUTOR_CHANNEL:
        return result(False, "execution_channel_not_controlled")
    if observation.get("exit_code") not in command.get("expected_success_exit_codes", [0]):
        return result(False, "exit_code_not_success")
    if observation.get("timed_out") or observation.get("execution_error"):
        return result(False, "execution_error")
    if observation.get("plan_digest") != plan.get("plan_digest"):
        return result(False, "plan_digest_mismatch")
    if observation.get("project_policy_digest") != plan.get("project_policy_digest"):
        return result(False, "project_policy_digest_mismatch")
    if observation.get("command_definition_digest") != command.get("definition_digest"):
        return result(False, "command_definition_digest_mismatch")
    if observation.get("current_source_fingerprint") is not None and observation.get("source_fingerprint") != observation.get("current_source_fingerprint"):
        return result(False, "source_fingerprint_stale")
    changed = observation.get("actual_changed_paths", []) or []
    declared = observation.get("declared_outputs", command.get("outputs", [])) or []
    writes = observation.get("writes", command.get("writes", "none"))
    if writes == "none" and changed:
        return result(False, "undeclared_writes")
    reconciliation = reconcile_changed_paths(
        {path: "before" for path in changed},
        {path: "after" for path in changed},
        declared,
        writes,
    )
    if observation.get("undeclared_paths") or reconciliation["undeclared_paths"]:
        return result(False, "undeclared_writes")
    if observation.get("postcondition_ok", True) is not True or observation.get("promotion_ok", True) is not True:
        return result(False, "postcondition_or_promotion_failed")
    return result(True, "zero_exit_and_current_observed_effects")

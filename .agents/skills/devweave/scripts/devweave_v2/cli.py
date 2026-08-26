"""Stable public V2 CLI; workflow host mutations use a separate entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .architecture_check import ArchitectureChecker
from .canonical import sha256
from .codex_doctor import CodexDoctor
from .errors import DevWeaveError, ErrorCode
from .git_port import GitAdapter
from .project_config import ProjectConfig
from .service_factory import build_run_service, load_project_config
from .v1_export import V1Exporter
from .verification_contracts import RiskLevel
from .version import SCHEMA_VERSION, VERSION

PUBLIC_COMMANDS = ("doctor", "inspect", "check", "verify", "export-v1", "mcp-serve")


class ContractArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise DevWeaveError(ErrorCode.INVALID_ARGUMENT, message)


def build_parser() -> argparse.ArgumentParser:
    parser = ContractArgumentParser(prog="devweave", add_help=True)
    parser.add_argument("--repo", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--codex-path")
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--run")
    subparsers.add_parser("check")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--run", required=True)
    verify.add_argument("--profile", choices=("low", "standard", "high"))
    verify.add_argument("--path", action="append", default=[])
    verify.add_argument("--release", action="store_true")
    export = subparsers.add_parser("export-v1")
    export.add_argument("--source-ref", required=True)
    export.add_argument("--output", required=True)
    subparsers.add_parser("mcp-serve")
    return parser


def envelope(*, ok: bool, result: Any = None, error: DevWeaveError | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": ok,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    if ok:
        payload["result"] = result
    else:
        payload["error"] = (error or DevWeaveError(ErrorCode.INTERNAL, "Unknown error.")).as_dict()
    return payload


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        repository = Path(args.repo).resolve()
        if args.command == "mcp-serve":
            from .mcp_server import run_stdio
            return run_stdio(repository)
        result = _dispatch(args, repository)
        emit(envelope(ok=True, result=result))
        return 0
    except DevWeaveError as exc:
        emit(envelope(ok=False, error=exc))
        return exit_code(exc.code)
    except (OSError, json.JSONDecodeError) as exc:
        error = DevWeaveError(ErrorCode.INVALID_JSON, "A required repository configuration file is unavailable or malformed.")
        emit(envelope(ok=False, error=error))
        print(f"DevWeave diagnostic: {type(exc).__name__}", file=sys.stderr)
        return exit_code(error.code)
    except Exception as exc:
        emit(envelope(ok=False, error=DevWeaveError(ErrorCode.INTERNAL, "Unhandled internal error.")))
        print(f"DevWeave diagnostic: {type(exc).__name__}", file=sys.stderr)
        return 70


def _dispatch(args: argparse.Namespace, repository: Path) -> Any:
    if args.command == "doctor":
        return CodexDoctor().probe(repository=repository, configured_path=args.codex_path)
    if args.command == "inspect":
        service = build_run_service(repository)
        if args.run:
            return service.inspect(args.run)
        if not service.store.active_root.is_dir():
            return {"runs": []}
        return {"runs": [service.inspect(path.stem) for path in sorted(service.store.active_root.glob("*.json"))]}
    if args.command == "check":
        config = load_project_config(repository)
        mcp = repository / ".codex" / "config.toml"
        if not mcp.is_file():
            raise DevWeaveError(ErrorCode.NOT_FOUND, "Project-scoped Codex MCP configuration is missing.")
        text = mcp.read_text(encoding="utf-8")
        if "[mcp_servers.devweave]" not in text or "required = true" not in text:
            raise DevWeaveError(ErrorCode.CONFLICT, "DevWeave MCP configuration is not required/current.")
        architecture = ArchitectureChecker(repository).assert_valid()
        return {
            "status": "passed",
            "schema_version": config.schema_version,
            "verification_commands": len(config.verification_plan.commands),
            "architecture": architecture,
        }
    if args.command == "verify":
        config = load_project_config(repository)
        service = build_run_service(repository)
        if service.verification_engine is None:
            raise DevWeaveError(ErrorCode.BLOCKED, "Verification engine is unavailable.")
        plan = service.inspect(args.run)
        profile = RiskLevel(plan["risk"])
        if args.profile is not None and RiskLevel(args.profile) is not profile:
            raise DevWeaveError(ErrorCode.FORBIDDEN, "CLI verification profile must equal the run risk.")
        mutation_id = f"cli-verify-{plan['revision']}-{sha256({'paths': args.path, 'release': args.release})[:12]}"
        return service.agent().verification_run(
            args.run,
            expected_revision=plan["revision"],
            mutation_id=mutation_id,
            paths=args.path,
            release=args.release,
        )
    if args.command == "export-v1":
        output = (repository / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
        try:
            output.relative_to(repository)
        except ValueError as exc:
            raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "V1 export output must remain inside the repository.") from exc
        json_path, markdown_path = V1Exporter(GitAdapter(repository)).write(args.source_ref, output)
        return {
            "json": json_path.relative_to(repository).as_posix(),
            "markdown": markdown_path.relative_to(repository).as_posix(),
        }
    raise DevWeaveError(ErrorCode.INVALID_ARGUMENT, "Unknown public command.")


def exit_code(code: ErrorCode) -> int:
    if code is ErrorCode.INVALID_ARGUMENT:
        return 2
    if code in {ErrorCode.BLOCKED, ErrorCode.CODEX_UNAVAILABLE, ErrorCode.GATE_REQUIRED, ErrorCode.FORBIDDEN}:
        return 3
    if code in {ErrorCode.NOT_FOUND, ErrorCode.INVALID_JSON, ErrorCode.INVALID_TYPE, ErrorCode.INVALID_VALUE, ErrorCode.UNKNOWN_FIELD, ErrorCode.REQUIRED_FIELD, ErrorCode.SCHEMA_VERSION, ErrorCode.CONFLICT, ErrorCode.STALE_REVISION}:
        return 4
    if code is ErrorCode.COMMAND_FAILED:
        return 5
    return 70


if __name__ == "__main__":
    sys.exit(main())

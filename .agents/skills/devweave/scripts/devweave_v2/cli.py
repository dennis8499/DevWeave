"""Public V2 command-line contract.

Handlers are replaced incrementally by later implementation slices.  The parser
itself is complete here so legacy mutation verbs can never leak into V2.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from .errors import DevWeaveError, ErrorCode
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
        raise DevWeaveError(
            ErrorCode.NOT_IMPLEMENTED,
            "The transitional V2 command handler is not active yet.",
            {"command": args.command},
        )
    except DevWeaveError as exc:
        emit(envelope(ok=False, error=exc))
        return 2 if exc.code is ErrorCode.INVALID_ARGUMENT else 4
    except Exception:
        emit(envelope(ok=False, error=DevWeaveError(ErrorCode.INTERNAL, "Unhandled internal error.")))
        return 70


if __name__ == "__main__":
    sys.exit(main())

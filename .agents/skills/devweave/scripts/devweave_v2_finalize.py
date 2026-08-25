"""Release-only DevWeave V2 cutover manifest and finalizer entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from devweave_v2.canonical import dumps
from devweave_v2.cutover import CutoverFinalizer, generate_manifest, write_manifest
from devweave_v2.errors import DevWeaveError, ErrorCode
from devweave_v2.version import SCHEMA_VERSION


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="devweave-v2-finalize")
    root.add_argument("--repo", default=".")
    commands = root.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare")
    prepare.add_argument("--base-ref", required=True)
    prepare.add_argument("--output", default="docs/generated/v2-cutover-manifest.json")

    check = commands.add_parser("check")
    check.add_argument("--manifest", default="docs/generated/v2-cutover-manifest.json")

    apply = commands.add_parser("apply")
    apply.add_argument("--manifest", default="docs/generated/v2-cutover-manifest.json")
    apply.add_argument("--approved-manifest-sha256", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    repository = Path(arguments.repo).resolve()
    try:
        if arguments.command == "prepare":
            output = _inside(repository, arguments.output)
            manifest = generate_manifest(repository, base_ref=arguments.base_ref)
            write_manifest(output, manifest)
            result = {
                "status": "prepared",
                "path": output.relative_to(repository).as_posix(),
                "manifest_sha256": manifest["manifest_sha256"],
                "replacements": len(manifest["replacements"]),
                "deletions": len(manifest["deletions"]),
            }
        else:
            finalizer = CutoverFinalizer(repository, _inside(repository, arguments.manifest))
            if arguments.command == "check":
                result = finalizer.check()
            else:
                result = finalizer.apply(approved_manifest_sha256=arguments.approved_manifest_sha256)
        sys.stdout.write(dumps({"schema_version": SCHEMA_VERSION, "ok": True, "command": arguments.command, "result": result}))
        return 0
    except DevWeaveError as exc:
        sys.stdout.write(dumps({"schema_version": SCHEMA_VERSION, "ok": False, "command": arguments.command, "error": exc.as_dict()}))
        return 2
    except Exception as exc:  # pragma: no cover - final defensive envelope
        error = DevWeaveError(ErrorCode.INTERNAL, "Unexpected cutover failure.", {"type": type(exc).__name__})
        sys.stdout.write(dumps({"schema_version": SCHEMA_VERSION, "ok": False, "command": arguments.command, "error": error.as_dict()}))
        return 3


def _inside(repository: Path, value: str) -> Path:
    candidate = (repository / value).resolve()
    try:
        candidate.relative_to(repository)
    except ValueError as exc:
        raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "Cutover artifact path escapes the repository.") from exc
    return candidate


if __name__ == "__main__":
    raise SystemExit(main())

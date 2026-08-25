"""Deterministic read-only index of V1 state stored at an immutable Git ref."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .canonical import dumps
from .errors import DevWeaveError, ErrorCode
from .git_port import GitPort
from .version import SCHEMA_VERSION


class V1Exporter:
    def __init__(self, git: GitPort) -> None:
        self.git = git

    def build(self, source_ref: str) -> dict[str, Any]:
        resolved = self.git.resolve_ref(source_ref)
        paths = self.git.list_tree(resolved, ".devweave/work-items")
        state_paths = sorted(path for path in paths if path.endswith("/state.json"))
        evidence_paths = sorted(path for path in paths if "/evidence/" in path and path.endswith(".json"))
        work_items: list[dict[str, Any]] = []
        warnings: list[dict[str, str]] = []
        for path in state_paths:
            work_id = path.split("/")[-2]
            try:
                state = json.loads(self.git.read_tree_file(resolved, path).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, DevWeaveError):
                warnings.append({"code": "unreadable_state", "path": path})
                continue
            prefix = f".devweave/work-items/{work_id}/evidence/"
            count = sum(1 for evidence in evidence_paths if evidence.startswith(prefix))
            work_items.append(
                {
                    "work_id": work_id,
                    "kind": str(state.get("kind", "unknown"))[:64],
                    "title": str(state.get("title", ""))[:512],
                    "status": str(state.get("status", "unknown"))[:64],
                    "closed_at": str(state.get("closed_at") or "")[:64],
                    "evidence_files": count,
                    "state_path": path,
                }
            )
        closed = sum(1 for item in work_items if item["status"] == "closed")
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "devweave_v1_export",
            "source_ref": source_ref,
            "resolved_source_ref": resolved,
            "summary": {
                "work_items": len(work_items),
                "closed_work_items": closed,
                "evidence_files": len(evidence_paths),
                "unconvertible": len(warnings),
            },
            "work_items": sorted(work_items, key=lambda item: item["work_id"]),
            "warnings": sorted(warnings, key=lambda item: (item["code"], item["path"])),
            "recovery": {
                "raw_data_copied": False,
                "method": "git_history",
                "instruction": f"git show {resolved}:<tracked-v1-path>",
            },
        }

    def write(self, source_ref: str, output: Path) -> tuple[Path, Path]:
        payload = self.build(source_ref)
        output.mkdir(parents=True, exist_ok=True)
        json_path = output / "v1-export.json"
        markdown_path = output / "v1-export.md"
        self._atomic_write(json_path, dumps(payload).encode("utf-8"))
        self._atomic_write(markdown_path, render_markdown(payload).encode("utf-8"))
        return json_path, markdown_path

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# DevWeave V1 deterministic export",
        "",
        f"- Source ref: `{payload['resolved_source_ref']}`",
        f"- Work items: {summary['work_items']} ({summary['closed_work_items']} closed)",
        f"- Evidence files: {summary['evidence_files']}",
        f"- Unconvertible records: {summary['unconvertible']}",
        "- Raw payload copied: no; use the recorded Git ref for recovery.",
        "",
        "## Work items",
        "",
        "| Work ID | Status | Evidence | Title |",
        "| --- | --- | ---: | --- |",
    ]
    for item in payload["work_items"]:
        title = item["title"].replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        lines.append(f"| `{item['work_id']}` | {item['status']} | {item['evidence_files']} | {title} |")
    if payload["warnings"]:
        lines.extend(("", "## Warnings", ""))
        lines.extend(f"- `{item['code']}`: `{item['path']}`" for item in payload["warnings"])
    return "\n".join(lines) + "\n"

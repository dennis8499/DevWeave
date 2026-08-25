"""Mechanical repository knowledge, architecture, size, schema, and trace checks."""

from __future__ import annotations

import ast
import json
import posixpath
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .errors import DevWeaveError, ErrorCode
from .schemas import PUBLIC_SCHEMA_TRACES, PUBLIC_SCHEMA_TYPES, schema_catalog

MAX_ROOT_INSTRUCTION_LINES = 100
MAX_ROOT_INSTRUCTION_BYTES = 8_000
MAX_SKILL_LINES = 200
MAX_SKILL_BYTES = 12_000
MAX_MODULE_LINES = 500
MAX_MODULE_BYTES = 30_000
MAX_ISSUES = 256
MAX_NAVIGATION_HOPS = 2

REQUIRED_DOCUMENTS = (
    "AGENTS.md",
    "ARCHITECTURE.md",
    "README.md",
    "docs/index.md",
    "docs/product.md",
    "docs/design.md",
    "docs/reliability.md",
    "docs/security.md",
    "docs/quality.md",
    "docs/architecture-exceptions.json",
    "docs/generated/public-schema-catalog.json",
    "docs/generated/v1-export.json",
    "docs/generated/v1-export.md",
    "docs/generated/v2-cutover-manifest.json",
    "docs/exec-plans/active/README.md",
    "docs/exec-plans/completed/README.md",
    "docs/exec-plans/tech-debt.md",
    ".agents/skills/devweave/SKILL.md",
)

REQUIRED_TOPICS = {
    "architecture": "ARCHITECTURE.md",
    "docs-index": "docs/index.md",
    "product": "docs/product.md",
    "design": "docs/design.md",
    "reliability": "docs/reliability.md",
    "security": "docs/security.md",
    "quality": "docs/quality.md",
    "tech-debt": "docs/exec-plans/tech-debt.md",
}

REQUIRED_NAVIGATION = (
    "ARCHITECTURE.md",
    "docs/index.md",
    "docs/product.md",
    "docs/design.md",
    "docs/reliability.md",
    "docs/security.md",
    "docs/quality.md",
    "docs/exec-plans/tech-debt.md",
    ".agents/skills/devweave/SKILL.md",
)

# Imports may point to the same or a lower-numbered layer, never upward.
PYTHON_LAYERS = {
    "errors": 0, "version": 0,
    "canonical": 1, "contract_utils": 1, "redaction": 1,
    "fingerprints": 2, "plan_contracts": 2, "project_config": 2,
    "risk": 2, "run_state": 2, "schemas": 2, "snapshot_contracts": 2,
    "verification_contracts": 2,
    "architecture_check": 3, "cutover": 3, "git_port": 3, "plan_store": 3, "reducer": 3,
    "v1_export": 3, "verification_engine": 3, "verification_store": 3,
    "codex_doctor": 4, "git_transaction": 4, "run_service": 4, "service_factory": 4,
    "transition_record": 4,
    "__init__": 5, "__main__": 5, "cli": 5, "host_bridge": 5,
    "host_operations": 5, "mcp_server": 5, "mcp_tools": 5,
}

TYPESCRIPT_LAYERS = {
    "vscode-extension/src/v2/contracts.ts": 0,
    "vscode-extension/src/app-server/protocol.ts": 0,
    "vscode-extension/src/app-server/event-reducer.ts": 1,
    "vscode-extension/src/app-server/transport.ts": 1,
    "vscode-extension/src/app-server/session.ts": 2,
    "vscode-extension/src/controller/approval-broker.ts": 2,
    "vscode-extension/src/controller/host-bridge-client.ts": 2,
    "vscode-extension/src/controller/review-coordinator.ts": 2,
    "vscode-extension/src/controller/workspace-controller.ts": 3,
    "vscode-extension/src/evidence/ui-evidence.ts": 4,
    "vscode-extension/src/ui/projection.ts": 4,
    "vscode-extension/src/ui/protocol.ts": 4,
    "vscode-extension/src/extension.ts": 5,
    "vscode-extension/webview/render.ts": 5,
    "vscode-extension/webview/main.ts": 5,
}

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
CANONICAL_TOPIC = re.compile(r"<!--\s*canonical-topic:\s*([a-z0-9-]+)\s*-->", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ArchitectureIssue:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class ArchitectureChecker:
    def __init__(self, repository: Path) -> None:
        self.repository = repository.resolve()
        self._issues: list[ArchitectureIssue] = []
        self._waived: list[ArchitectureIssue] = []
        self._waivers: set[tuple[str, str]] = set()

    def report(self) -> dict[str, Any]:
        self._issues = []
        self._waived = []
        self._waivers = set()
        self._load_exceptions()
        self._check_required_documents()
        self._check_instruction_sizes()
        self._check_markdown_and_navigation()
        self._check_canonical_topics()
        self._check_truth_boundaries()
        self._check_module_sizes()
        self._check_python_dependencies()
        self._check_typescript_dependencies()
        self._check_schema_catalog()
        self._check_traceability()
        issues = sorted(self._issues, key=lambda item: (item.path, item.code, item.message))[:MAX_ISSUES]
        waived = sorted(self._waived, key=lambda item: (item.path, item.code, item.message))[:MAX_ISSUES]
        return {
            "status": "passed" if not issues else "failed",
            "issues": [item.as_dict() for item in issues],
            "waived": [item.as_dict() for item in waived],
            "limits": {
                "navigation_hops": MAX_NAVIGATION_HOPS,
                "module_lines": MAX_MODULE_LINES,
                "root_instruction_lines": MAX_ROOT_INSTRUCTION_LINES,
            },
        }

    def assert_valid(self) -> dict[str, Any]:
        report = self.report()
        if report["status"] != "passed":
            raise DevWeaveError(
                ErrorCode.CONFLICT,
                "Repository architecture check failed.",
                {"issues": report["issues"]},
            )
        return report

    def _load_exceptions(self) -> None:
        relative = "docs/architecture-exceptions.json"
        path = self.repository / relative
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._issues.append(ArchitectureIssue("INVALID_EXCEPTION", relative, "Exception file must be valid UTF-8 JSON."))
            return
        if not isinstance(raw, dict) or set(raw) != {"schema_version", "exceptions"} or raw.get("schema_version") != 2 or not isinstance(raw.get("exceptions"), list):
            self._issues.append(ArchitectureIssue("INVALID_EXCEPTION", relative, "Exception file must use the strict schema-v2 envelope."))
            return
        for index, item in enumerate(raw["exceptions"]):
            item_path = f"{relative}#exceptions[{index}]"
            required = {"code", "path", "owner", "reason", "expires"}
            if not isinstance(item, dict) or set(item) != required or not all(isinstance(item.get(key), str) and item[key].strip() for key in required):
                self._issues.append(ArchitectureIssue("INVALID_EXCEPTION", item_path, "Each exception needs code, path, owner, reason, and expires."))
                continue
            try:
                expires = date.fromisoformat(item["expires"])
            except ValueError:
                self._issues.append(ArchitectureIssue("INVALID_EXCEPTION", item_path, "Exception expiry must be YYYY-MM-DD."))
                continue
            if expires < date.today():
                self._issues.append(ArchitectureIssue("EXPIRED_EXCEPTION", item_path, f"Exception expired on {expires.isoformat()}."))
                continue
            self._waivers.add((item["code"], _normalize(item["path"])))

    def _check_required_documents(self) -> None:
        for relative in REQUIRED_DOCUMENTS:
            if not (self.repository / relative).is_file():
                self._add("MISSING_DOCUMENT", relative, "Required repository knowledge entry is missing.")

    def _check_instruction_sizes(self) -> None:
        self._bounded_file("AGENTS.md", MAX_ROOT_INSTRUCTION_LINES, MAX_ROOT_INSTRUCTION_BYTES, "ROOT_INSTRUCTIONS_TOO_LARGE")
        self._bounded_file(".agents/skills/devweave/SKILL.md", MAX_SKILL_LINES, MAX_SKILL_BYTES, "SKILL_INSTRUCTIONS_TOO_LARGE")
        staged = ".agents/skills/devweave/assets/v2-skill/SKILL.md"
        if (self.repository / staged).is_file():
            self._bounded_file(staged, MAX_SKILL_LINES, MAX_SKILL_BYTES, "SKILL_INSTRUCTIONS_TOO_LARGE")

    def _bounded_file(self, relative: str, line_limit: int, byte_limit: int, code: str) -> None:
        path = self.repository / relative
        if not path.is_file():
            return
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
        if len(lines) > line_limit or len(raw) > byte_limit:
            self._add(code, relative, f"Instruction file is {len(lines)} lines/{len(raw)} bytes; limit is {line_limit}/{byte_limit}.")

    def _check_markdown_and_navigation(self) -> None:
        markdown = self._markdown_files()
        graph: dict[str, set[str]] = {item: set() for item in markdown}
        for relative in markdown:
            path = self.repository / relative
            text = path.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(text):
                resolved = self._resolve_markdown_link(relative, target)
                if resolved is None:
                    continue
                if not (self.repository / resolved).exists():
                    self._add("BROKEN_DOC_LINK", relative, f"Local link target does not exist: {target}")
                    continue
                graph[relative].add(resolved)
        reachable = {"AGENTS.md"}
        frontier = {"AGENTS.md"}
        for _ in range(MAX_NAVIGATION_HOPS):
            frontier = {target for source in frontier for target in graph.get(source, set())} - reachable
            reachable.update(frontier)
        for target in REQUIRED_NAVIGATION:
            if target not in reachable:
                self._add("NAVIGATION_TOO_DEEP", "AGENTS.md", f"{target} must be reachable within {MAX_NAVIGATION_HOPS} local Markdown hops.")

    def _markdown_files(self) -> list[str]:
        paths = [self.repository / name for name in ("AGENTS.md", "ARCHITECTURE.md", "README.md")]
        docs = self.repository / "docs"
        if docs.is_dir():
            paths.extend(docs.rglob("*.md"))
        skill = self.repository / ".agents" / "skills" / "devweave"
        if skill.is_dir():
            paths.append(skill / "SKILL.md")
            references = skill / "references"
            if references.is_dir():
                paths.extend(references.rglob("*.md"))
        result: set[str] = set()
        for path in paths:
            if path.is_file():
                result.add(path.relative_to(self.repository).as_posix())
        return sorted(result)

    def _resolve_markdown_link(self, source: str, raw_target: str) -> str | None:
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or target.startswith("#"):
            return None
        decoded = unquote(parts.path)
        if not decoded:
            return None
        normalized = _normalize(posixpath.join(posixpath.dirname(source), decoded))
        if normalized == ".." or normalized.startswith("../"):
            self._add("DOC_LINK_ESCAPE", source, f"Local link escapes the repository: {raw_target}")
            return None
        return normalized

    def _check_canonical_topics(self) -> None:
        found: dict[str, list[str]] = {}
        for relative in self._markdown_files():
            text = (self.repository / relative).read_text(encoding="utf-8")
            for topic in CANONICAL_TOPIC.findall(text):
                found.setdefault(topic.lower(), []).append(relative)
        for topic, expected in REQUIRED_TOPICS.items():
            paths = found.get(topic, [])
            if paths != [expected]:
                self._add("CANONICAL_TOPIC_DRIFT", expected, f"Topic {topic} must be declared exactly once at {expected}; found {paths}.")
        for topic, paths in found.items():
            if len(paths) > 1:
                for path in paths:
                    self._add("DUPLICATE_CANONICAL_TOPIC", path, f"Canonical topic {topic} is also declared in {', '.join(item for item in paths if item != path)}.")

    def _check_truth_boundaries(self) -> None:
        authority = (
            "AGENTS.md", "ARCHITECTURE.md", "docs/index.md", "docs/product.md",
            "docs/design.md", "docs/reliability.md", "docs/security.md", "docs/quality.md",
        )
        forbidden = re.compile(r"(?<![A-Za-z0-9_.-])(?:wiki/|\.devweave/baseline/)", re.IGNORECASE)
        for relative in authority:
            path = self.repository / relative
            if path.is_file() and forbidden.search(path.read_text(encoding="utf-8")):
                self._add("DUPLICATE_TRUTH_DEPENDENCY", relative, "Canonical V2 knowledge must not depend on legacy Wiki or baseline truth.")
        surfaced = (*authority, ".agents/skills/devweave/SKILL.md", ".agents/skills/devweave/assets/v2-skill/SKILL.md")
        companion = re.compile(r"\b(?:grill-me|grilling|codebase-design|diagnosing-bugs|tdd)\b", re.IGNORECASE)
        for relative in surfaced:
            path = self.repository / relative
            if path.is_file() and companion.search(path.read_text(encoding="utf-8")):
                self._add("LEGACY_SKILL_ROUTING", relative, "V2 guidance must route only through the DevWeave skill.")

    def _check_module_sizes(self) -> None:
        paths = [self.repository / ".agents" / "skills" / "devweave" / "scripts" / "devweave_v2" / f"{name}.py" for name in PYTHON_LAYERS]
        paths.extend(self.repository / relative for relative in TYPESCRIPT_LAYERS)
        for path in paths:
            if not path.is_file():
                continue
            raw = path.read_bytes()
            lines = raw.decode("utf-8").splitlines()
            if len(lines) > MAX_MODULE_LINES or len(raw) > MAX_MODULE_BYTES:
                relative = path.relative_to(self.repository).as_posix()
                self._add("MODULE_TOO_LARGE", relative, f"Module is {len(lines)} lines/{len(raw)} bytes; limit is {MAX_MODULE_LINES}/{MAX_MODULE_BYTES}.")

    def _check_python_dependencies(self) -> None:
        root = self.repository / ".agents" / "skills" / "devweave" / "scripts" / "devweave_v2"
        if not root.is_dir():
            return
        for path in sorted(root.glob("*.py")):
            module = path.stem
            relative = path.relative_to(self.repository).as_posix()
            if module not in PYTHON_LAYERS:
                self._add("UNCLASSIFIED_MODULE", relative, "Python module is absent from the architecture layer map.")
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            except SyntaxError:
                self._add("PYTHON_PARSE_ERROR", relative, "Python module could not be parsed for dependency checks.")
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level != 1 or not node.module:
                    continue
                imported = node.module.split(".", 1)[0]
                if imported in PYTHON_LAYERS and PYTHON_LAYERS[imported] > PYTHON_LAYERS[module]:
                    self._add("REVERSE_DEPENDENCY", relative, f"Layer {PYTHON_LAYERS[module]} module imports higher layer {PYTHON_LAYERS[imported]} module {imported}.")

    def _check_typescript_dependencies(self) -> None:
        import_pattern = re.compile(r"\bfrom\s+[\"']([^\"']+)[\"']")
        for relative, layer in TYPESCRIPT_LAYERS.items():
            path = self.repository / relative
            if not path.is_file():
                continue
            for specifier in import_pattern.findall(path.read_text(encoding="utf-8")):
                if not specifier.startswith("."):
                    continue
                target = _normalize(posixpath.join(posixpath.dirname(relative), specifier))
                candidates = (target, f"{target}.ts", f"{target}/index.ts")
                resolved = next((item for item in candidates if item in TYPESCRIPT_LAYERS), None)
                if resolved is not None and TYPESCRIPT_LAYERS[resolved] > layer:
                    self._add("REVERSE_DEPENDENCY", relative, f"Layer {layer} module imports higher layer {TYPESCRIPT_LAYERS[resolved]} module {resolved}.")

    def _check_schema_catalog(self) -> None:
        catalog_path = "docs/generated/public-schema-catalog.json"
        path = self.repository / catalog_path
        if path.is_file():
            try:
                actual = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                actual = None
            if actual != schema_catalog():
                self._add("PUBLIC_SCHEMA_DRIFT", catalog_path, "Generated public schema catalog does not match the Python registry.")
        typescript_path = "vscode-extension/src/v2/contracts.ts"
        path = self.repository / typescript_path
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        match = re.search(r"PUBLIC_SCHEMA_NAMES\s*=\s*(\[[^;]+\])\s*as const", text, re.DOTALL)
        try:
            names = json.loads(match.group(1)) if match else []
        except json.JSONDecodeError:
            names = []
        if names != sorted(PUBLIC_SCHEMA_TYPES):
            self._add("PUBLIC_SCHEMA_DRIFT", typescript_path, f"TypeScript public schema names must equal {sorted(PUBLIC_SCHEMA_TYPES)}.")
        if not re.search(r"DEVWEAVE_SCHEMA_VERSION\s*=\s*2\s+as const", text):
            self._add("PUBLIC_SCHEMA_DRIFT", typescript_path, "TypeScript schema version must remain 2.")

    def _check_traceability(self) -> None:
        product_path = self.repository / "docs" / "product.md"
        quality_path = self.repository / "docs" / "quality.md"
        if not product_path.is_file() or not quality_path.is_file():
            return
        product = product_path.read_text(encoding="utf-8")
        quality = quality_path.read_text(encoding="utf-8")
        declared = re.findall(r"^###\s+(AC-\d{3}):", product, re.MULTILINE)
        traced = set(re.findall(r"^\|\s*(AC-\d{3})\s*\|", quality, re.MULTILINE))
        duplicates = sorted({item for item in declared if declared.count(item) > 1})
        for acceptance in duplicates:
            self._add("DUPLICATE_ACCEPTANCE", "docs/product.md", f"{acceptance} is declared more than once.")
        for acceptance in sorted(set(declared) - traced):
            self._add("UNTRACED_ACCEPTANCE", "docs/quality.md", f"{acceptance} has no mechanical verification trace.")
        for schema, traces in PUBLIC_SCHEMA_TRACES.items():
            for acceptance in (item for item in traces if item.startswith("AC-")):
                if acceptance not in declared:
                    self._add("UNKNOWN_SCHEMA_TRACE", "docs/product.md", f"Schema {schema} traces unknown {acceptance}.")

    def _add(self, code: str, path: str, message: str) -> None:
        issue = ArchitectureIssue(code, _normalize(path), message)
        if (issue.code, issue.path) in self._waivers:
            self._waived.append(issue)
        elif len(self._issues) < MAX_ISSUES:
            self._issues.append(issue)


def _normalize(value: str) -> str:
    return posixpath.normpath(value.replace("\\", "/"))

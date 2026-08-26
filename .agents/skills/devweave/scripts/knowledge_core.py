"""Dependency-free Wiki knowledge model used by the DevWeave engine.

The module owns deterministic parsing, source/content fingerprints, bootstrap,
lint, and sealing.  It deliberately does not import ``devweave_core`` so the
engine remains the only owner of work locks, state, and event ledgers.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


PAGE_TYPES = {
    "overview",
    "architecture",
    "module",
    "entity",
    "pattern",
    "decision",
    "dependency",
    "guide",
    "synthesis",
    "index",
    "log",
}
PAGE_STATUSES = {"active", "stale", "placeholder"}
REQUIRED_FIELDS = ("title", "type", "sources", "last_updated", "tags", "status")
PROVENANCE_FIELDS = ("source_fingerprint", "verified_by")
TYPE_DIRECTORIES = {
    "architecture": "architecture",
    "module": "modules",
    "entity": "entities",
    "pattern": "patterns",
    "decision": "decisions",
    "dependency": "dependencies",
    "guide": "guides",
    "synthesis": "synthesis",
}
INDEX_SECTIONS = {
    "overview": "Overview",
    "architecture": "Architecture",
    "module": "Modules",
    "entity": "Entities",
    "pattern": "Patterns",
    "decision": "Decisions",
    "dependency": "Dependencies",
    "guide": "Guides",
    "synthesis": "Synthesis",
}
STARTER_FILES = {
    "index.md": "wiki/starter/index.md.tmpl",
    "overview.md": "wiki/starter/overview.md.tmpl",
    "log.md": "wiki/starter/log.md.tmpl",
}
SPECIAL_TYPES = {"index.md": "index", "overview.md": "overview", "log.md": "log"}
FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(?P<header>.*?)\r?\n---[ \t]*(?P<ending>\r?\n|\Z)",
    re.DOTALL,
)
WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
FINGERPRINT_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
WORK_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
TEMPLATE_TOKEN_PATTERN = re.compile(r"<[A-Z][A-Z0-9_]*>")
MAX_SOURCES = 5


class KnowledgeError(Exception):
    """A deterministic knowledge-model failure with a stable machine code."""

    def __init__(self, code: str, message: str, details: Any | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_fingerprint(value: bytes) -> str:
    return f"sha256:{sha256_hex(value)}"


def normalize_root(root: str) -> str:
    value = root.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    value = value.rstrip("/")
    pure = PurePosixPath(value)
    if (
        not value
        or value == "."
        or pure.is_absolute()
        or ".." in pure.parts
        or re.match(r"^[A-Za-z]:", value)
    ):
        raise KnowledgeError("invalid_knowledge_root", "Knowledge root must be repo-relative.", {"root": root})
    return pure.as_posix()


def normalize_page(path: str, root: str = "wiki") -> str:
    knowledge_root = normalize_root(root)
    value = path.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or re.match(r"^[A-Za-z]:", value):
        raise KnowledgeError("invalid_page", "Wiki page must stay inside the knowledge root.", {"page": path})
    normalized = pure.as_posix()
    if normalized == knowledge_root:
        raise KnowledgeError("invalid_page", "Wiki page must name a Markdown file.", {"page": path})
    if not normalized.startswith(knowledge_root + "/"):
        normalized = f"{knowledge_root}/{normalized}"
    relative = normalized[len(knowledge_root) + 1 :]
    if not relative or not relative.endswith(".md"):
        raise KnowledgeError("invalid_page", "Wiki pages must use a .md path.", {"page": path})
    return normalized


def normalize_source(source: str, root: str = "wiki") -> str:
    if not isinstance(source, str) or not source.strip():
        raise KnowledgeError("invalid_source", "Every source must be a non-empty repo-relative path.", {"source": source})
    value = source.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or re.match(r"^[A-Za-z]:", value):
        raise KnowledgeError("invalid_source", "Source paths must stay inside the repository.", {"source": source})
    normalized = pure.as_posix()
    knowledge_root = normalize_root(root)
    forbidden = (knowledge_root, ".devweave", ".git")
    if any(normalized == item or normalized.startswith(item + "/") for item in forbidden):
        raise KnowledgeError(
            "invalid_source",
            "Wiki, DevWeave state, and Git internals cannot be knowledge sources.",
            {"source": source},
        )
    return normalized


def normalize_sources(sources: Sequence[str], root: str = "wiki") -> list[str]:
    if isinstance(sources, (str, bytes)) or not isinstance(sources, Sequence):
        raise KnowledgeError("invalid_source", "sources must be an array of paths.")
    normalized = sorted({normalize_source(item, root) for item in sources})
    if len(normalized) > MAX_SOURCES:
        raise KnowledgeError(
            "too_many_sources",
            f"A Wiki page may list at most {MAX_SOURCES} sources.",
            {"count": len(normalized)},
        )
    return normalized


def _parse_inline_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    try:
        return [item.strip() for item in next(csv.reader([inner], skipinitialspace=True)) if item.strip()]
    except (csv.Error, StopIteration) as exc:
        raise KnowledgeError("invalid_frontmatter", "Invalid inline frontmatter array.") from exc


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        if value[0] == '"':
            try:
                return str(json.loads(value))
            except json.JSONDecodeError:
                return value[1:-1]
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter_text(text: str) -> tuple[dict[str, Any], str, list[str]]:
    """Parse the small YAML subset used by Wiki pages and return body/errors."""

    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}, text, ["missing YAML frontmatter"]
    values: dict[str, Any] = {}
    errors: list[str] = []
    current_list: str | None = None
    for number, raw in enumerate(match.group("header").splitlines(), start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            line = raw.strip()
            if current_list and line.startswith("- "):
                values[current_list].append(_strip_quotes(line[2:]))
            else:
                errors.append(f"line {number}: unsupported indentation")
            continue
        current_list = None
        if ":" not in raw:
            errors.append(f"line {number}: expected key: value")
            continue
        key, raw_value = raw.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or key in values:
            errors.append(f"line {number}: empty or duplicate key")
            continue
        if raw_value == "":
            values[key] = []
            current_list = key
        elif raw_value.startswith("[") and raw_value.endswith("]"):
            values[key] = [_strip_quotes(item) for item in _parse_inline_list(raw_value)]
        else:
            values[key] = _strip_quotes(raw_value)
    return values, text[match.end() :], errors


def _yaml_scalar(value: Any) -> str:
    text = str(value)
    if (
        not text
        or text != text.strip()
        or any(ord(char) < 0x20 for char in text)
        or any(char in text for char in "#:{}[],&*!|>'\"%@`")
    ):
        return json.dumps(text, ensure_ascii=False)
    return text


def render_frontmatter(values: dict[str, Any], body: str) -> str:
    preferred = [*REQUIRED_FIELDS, *PROVENANCE_FIELDS]
    keys = [key for key in preferred if key in values]
    keys.extend(key for key in values if key not in keys)
    lines = ["---"]
    for key in keys:
        value = values[key]
        if isinstance(value, list):
            rendered = ", ".join(_yaml_scalar(item) for item in value)
            lines.append(f"{key}: [{rendered}]")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.extend(("---", ""))
    return "\n".join(lines) + body


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _exclusive_write(path: Path, text: str) -> None:
    """Create one complete file without ever replacing an existing target."""

    path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            created = True
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise KnowledgeError(
            "page_exists",
            "Wiki scaffold target already exists and was not modified.",
            {"page": path.as_posix()},
        ) from exc
    except Exception:
        if created and path.exists():
            path.unlink()
        raise


def _inside_repo(repo: Path, relative: str) -> Path:
    root = repo.resolve()
    candidate = (root / Path(relative)).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise KnowledgeError("path_escape", "Path escapes the repository.", {"path": relative}) from exc
    return candidate


def _read_asset(assets: Path, relative: str, values: dict[str, str]) -> str:
    path = assets / relative
    try:
        return path.read_text(encoding="utf-8").format_map(values)
    except FileNotFoundError as exc:
        raise KnowledgeError("missing_asset", "Bundled Wiki asset is missing.", {"asset": relative}) from exc


def inspect_wiki(repo: Path, *, root: str = "wiki") -> dict[str, Any]:
    """Inspect bootstrap compatibility without mutating repository content."""

    knowledge_root = normalize_root(root)
    wiki = _inside_repo(repo, knowledge_root)
    if not wiki.exists():
        return {"root": knowledge_root, "status": "missing", "compatible": True, "conflicts": []}
    if not wiki.is_dir():
        return {
            "root": knowledge_root,
            "status": "conflict",
            "compatible": False,
            "conflicts": [{"path": knowledge_root, "reason": "knowledge root is not a directory"}],
        }
    existing_entries = list(wiki.iterdir())
    if not existing_entries:
        return {"root": knowledge_root, "status": "empty", "compatible": True, "conflicts": []}
    conflicts: list[dict[str, str]] = []
    for filename, expected_type in SPECIAL_TYPES.items():
        path = wiki / filename
        if not path.exists() and not path.is_symlink():
            continue
        relative = f"{knowledge_root}/{filename}"
        if path.is_symlink() or not path.is_file():
            conflicts.append({"path": relative, "reason": "reserved starter path is not a regular file"})
            continue
        try:
            frontmatter, _, parse_errors = parse_frontmatter_text(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            conflicts.append({"path": relative, "reason": f"expected type {expected_type}"})
            continue
        if parse_errors or frontmatter.get("type") != expected_type:
            conflicts.append({"path": relative, "reason": f"expected type {expected_type}"})
    for directory in TYPE_DIRECTORIES.values():
        path = wiki / directory
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_symlink() or not path.is_dir():
            conflicts.append(
                {
                    "path": f"{knowledge_root}/{directory}",
                    "reason": "reserved starter directory is not a directory",
                }
            )
    return {
        "root": knowledge_root,
        "status": "conflict" if conflicts else "compatible",
        "compatible": not conflicts,
        "conflicts": conflicts,
    }


def bootstrap_wiki(
    repo: Path,
    assets: Path,
    *,
    root: str = "wiki",
    locale: str = "zh-TW",
    today: str | None = None,
) -> dict[str, Any]:
    """Install or non-destructively adopt a compatible Wiki skeleton."""

    knowledge_root = normalize_root(root)
    wiki = _inside_repo(repo, knowledge_root)
    inspection = inspect_wiki(repo, root=root)
    if not inspection["compatible"]:
        raise KnowledgeError(
            "knowledge_conflict",
            "Existing Wiki content is not compatible and was not modified.",
            {"conflicts": inspection["conflicts"]},
        )

    values = {
        "date": today or datetime.now(timezone.utc).date().isoformat(),
        "locale": locale,
    }
    created: list[str] = []
    wiki.mkdir(parents=True, exist_ok=True)
    for directory in TYPE_DIRECTORIES.values():
        target = wiki / directory
        target.mkdir(parents=True, exist_ok=True)
        marker = target / ".gitkeep"
        if not marker.exists():
            _atomic_write(marker, "")
            created.append(f"{knowledge_root}/{directory}/.gitkeep")
    for filename, asset in STARTER_FILES.items():
        target = wiki / filename
        if target.exists():
            continue
        _atomic_write(target, _read_asset(assets, asset, values))
        created.append(f"{knowledge_root}/{filename}")
    return {
        "root": knowledge_root,
        "status": "created" if created else "adopted",
        "created": sorted(created),
    }


def scaffold_page(
    repo: Path,
    assets: Path,
    *,
    page: str,
    page_type: str,
    title: str,
    sources: Sequence[str],
    work_id: str,
    package_name: str | None = None,
    version: str | None = None,
    decision_date: str | None = None,
    decision_status: str | None = None,
    root: str = "wiki",
    today: str | None = None,
) -> dict[str, Any]:
    """Render one canonical content-page template through a no-overwrite seam."""

    content_types = PAGE_TYPES - {"index", "log"}
    if page_type not in content_types:
        raise KnowledgeError(
            "invalid_page_type",
            "Scaffold supports only canonical Wiki content page types.",
            {"type": page_type, "allowed": sorted(content_types)},
        )
    if not isinstance(title, str) or not title.strip():
        raise KnowledgeError("invalid_title", "Wiki scaffold title must not be empty.")
    if not WORK_PATTERN.fullmatch(work_id):
        raise KnowledgeError("invalid_work", "verified_by must be a valid work ID.")
    normalized_page = normalize_page(page, root)
    knowledge_root = normalize_root(root)
    relative = normalized_page[len(knowledge_root) + 1 :]
    location_error = _page_expected_location(relative, page_type)
    if location_error:
        raise KnowledgeError(
            "page_location", location_error, {"page": normalized_page}
        )
    normalized_sources = normalize_sources(sources, knowledge_root)
    if not normalized_sources:
        raise KnowledgeError(
            "missing_source", "Scaffolded Wiki pages require at least one source."
        )
    source_fingerprint(repo, normalized_sources, root=knowledge_root)
    rendered_date = today or datetime.now(timezone.utc).date().isoformat()
    if not _valid_date(rendered_date):
        raise KnowledgeError(
            "invalid_date", "Scaffold date must use YYYY-MM-DD.", {"date": rendered_date}
        )

    extras: dict[str, str] = {}
    if page_type == "dependency":
        if not (package_name or "").strip() or not (version or "").strip():
            raise KnowledgeError(
                "missing_dependency_fields",
                "Dependency scaffold requires package_name and version.",
            )
        extras = {
            "package_name": str(package_name).strip(),
            "version": str(version).strip(),
        }
    elif package_name is not None or version is not None:
        raise KnowledgeError(
            "unexpected_type_fields",
            "package_name and version are valid only for dependency pages.",
        )
    if page_type == "decision":
        if not _valid_date(decision_date) or decision_status not in {
            "proposed",
            "accepted",
            "deprecated",
            "superseded",
        }:
            raise KnowledgeError(
                "invalid_decision_fields",
                "Decision scaffold requires a valid decision_date and decision_status.",
            )
        extras.update(
            {
                "decision_date": str(decision_date),
                "decision_status": str(decision_status),
            }
        )
    elif decision_date is not None or decision_status is not None:
        raise KnowledgeError(
            "unexpected_type_fields",
            "decision_date and decision_status are valid only for decision pages.",
        )

    asset = assets / "wiki" / "templates" / f"{page_type}.md"
    try:
        template = asset.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise KnowledgeError(
            "missing_asset",
            "Bundled Wiki template is missing.",
            {"asset": f"wiki/templates/{page_type}.md"},
        ) from exc
    template_frontmatter, body, parse_errors = parse_frontmatter_text(template)
    if parse_errors or template_frontmatter.get("type") != page_type:
        raise KnowledgeError(
            "invalid_asset",
            "Bundled Wiki template is incompatible.",
            {"asset": f"wiki/templates/{page_type}.md", "errors": parse_errors},
        )
    values: dict[str, Any] = {
        "title": title.strip(),
        "type": page_type,
        "sources": normalized_sources,
        "last_updated": rendered_date,
        "tags": template_frontmatter.get("tags", [page_type]),
        "status": "placeholder",
        "source_fingerprint": "none",
        "verified_by": work_id,
        **extras,
    }
    rendered = render_frontmatter(values, body.replace("<TITLE>", title.strip()))
    target = _inside_repo(repo, normalized_page)
    _exclusive_write(target, rendered)
    return {
        "page": normalized_page,
        "type": page_type,
        "status": "placeholder",
        "sources": normalized_sources,
    }


def _git_z(repo: Path, args: Sequence[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise KnowledgeError(
            "git_failed",
            "Git could not enumerate knowledge sources.",
            {"args": list(args), "stderr": result.stderr.decode("utf-8", errors="replace")},
        )
    return [
        item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    ]


def source_catalog(repo: Path, root: str = "wiki") -> tuple[set[str], set[str]]:
    blocked = (normalize_root(root), ".devweave", ".git")

    def allowed(path: str) -> bool:
        normalized = PurePosixPath(path).as_posix()
        return not any(normalized == item or normalized.startswith(item + "/") for item in blocked)

    listed = {
        path
        for path in _git_z(
            repo,
            ["ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        )
        if allowed(path)
    }
    return listed, set()


def _file_material(repo: Path, relative: str) -> dict[str, str]:
    lexical = repo / Path(relative)
    if lexical.is_symlink():
        return {"path": relative, "kind": "symlink", "content": os.readlink(lexical)}
    safe = _inside_repo(repo, relative)
    if not safe.is_file():
        return {"path": relative, "kind": "missing", "content": "<missing>"}
    digest = hashlib.sha256()
    with safe.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": relative, "kind": "file", "content": digest.hexdigest()}


def source_fingerprint(
    repo: Path,
    sources: Sequence[str],
    *,
    root: str = "wiki",
    catalog: tuple[set[str], set[str]] | None = None,
) -> str:
    normalized = normalize_sources(sources, root)
    if not normalized:
        return "none"
    tracked, untracked = catalog or source_catalog(repo, root)
    all_files = tracked | untracked
    material: list[dict[str, Any]] = []
    for source in normalized:
        lexical = repo / Path(source)
        if lexical.is_symlink():
            material.append({"source": source, "entries": [_file_material(repo, source)]})
            continue
        safe = _inside_repo(repo, source)
        if safe.is_file():
            material.append({"source": source, "entries": [_file_material(repo, source)]})
            continue
        if safe.is_dir() or source == ".":
            prefix = "" if source == "." else source.rstrip("/") + "/"
            members = sorted(path for path in all_files if not prefix or path.startswith(prefix))
            material.append(
                {
                    "source": source,
                    "entries": [_file_material(repo, member) for member in members],
                }
            )
            continue
        raise KnowledgeError("missing_source", "Knowledge source does not exist.", {"source": source})
    return sha256_fingerprint(canonical_json(material))


def _page_expected_location(relative: str, page_type: str) -> str | None:
    if page_type in TYPE_DIRECTORIES:
        expected = TYPE_DIRECTORIES[page_type]
        return None if PurePosixPath(relative).parent.as_posix() == expected else f"{page_type} pages must live under {expected}/"
    expected_special = {"overview": "overview.md", "index": "index.md", "log": "log.md"}.get(page_type)
    if expected_special and relative != expected_special:
        return f"{page_type} page must be {expected_special}"
    return None


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def page_record(
    repo: Path,
    path: Path,
    wiki: Path,
    *,
    root: str,
    catalog: tuple[set[str], set[str]],
) -> dict[str, Any]:
    relative = path.relative_to(wiki).as_posix()
    repo_path = f"{normalize_root(root)}/{relative}"
    text = path.read_text(encoding="utf-8")
    frontmatter, body, parse_errors = parse_frontmatter_text(text)
    sources = frontmatter.get("sources", [])
    normalized_sources: list[str] = []
    computed: str | None = None
    source_error: dict[str, Any] | None = None
    try:
        normalized_sources = normalize_sources(sources, root)
        computed = source_fingerprint(repo, normalized_sources, root=root, catalog=catalog)
    except KnowledgeError as exc:
        source_error = {"code": exc.code, "message": exc.message, "details": exc.details}
    return {
        "path": repo_path,
        "relative": relative,
        "title": frontmatter.get("title"),
        "type": frontmatter.get("type"),
        "status": frontmatter.get("status"),
        "sources": normalized_sources,
        "source_fingerprint": frontmatter.get("source_fingerprint"),
        "computed_source_fingerprint": computed,
        "verified_by": frontmatter.get("verified_by"),
        "last_updated": frontmatter.get("last_updated"),
        "parse_errors": parse_errors,
        "source_error": source_error,
        "body_length": len(body.encode("utf-8")),
        "body_hash": sha256_hex(body.encode("utf-8")),
        "file_hash": sha256_hex(text.encode("utf-8")),
    }


def knowledge_snapshot(repo: Path, *, root: str = "wiki") -> dict[str, Any]:
    knowledge_root = normalize_root(root)
    wiki = _inside_repo(repo, knowledge_root)
    if not wiki.is_dir():
        return {"root": knowledge_root, "files": {}, "pages": {}, "fingerprint": sha256_hex(canonical_json({})), "log": None}
    markdown_paths = sorted(wiki.rglob("*.md"))
    needs_catalog = False
    for markdown in markdown_paths:
        frontmatter, _, _ = parse_frontmatter_text(markdown.read_text(encoding="utf-8"))
        if frontmatter.get("sources"):
            needs_catalog = True
            break
    catalog = source_catalog(repo, root) if needs_catalog else (set(), set())
    files: dict[str, str] = {}
    pages: dict[str, dict[str, Any]] = {}
    for path in sorted(wiki.rglob("*")):
        if not path.is_file():
            continue
        relative = f"{knowledge_root}/{path.relative_to(wiki).as_posix()}"
        files[relative] = sha256_hex(path.read_bytes())
        if path.suffix.lower() == ".md":
            record = page_record(repo, path, wiki, root=root, catalog=catalog)
            pages[relative] = record
    log_record = pages.get(f"{knowledge_root}/log.md")
    log = None
    if log_record:
        log = {"body_length": log_record["body_length"], "body_hash": log_record["body_hash"]}
    return {
        "root": knowledge_root,
        "files": files,
        "pages": pages,
        "fingerprint": sha256_hex(canonical_json(files)),
        "log": log,
    }


def _finding(severity: str, code: str, message: str, page: str | None = None, details: Any | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if page:
        item["page"] = page
    if details is not None:
        item["details"] = details
    return item


def _wikilinks(text: str) -> list[str]:
    visible = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    visible = re.sub(r"`[^`\n]*`", "", visible)
    return WIKILINK_PATTERN.findall(visible)


def _wikilink_target(raw: str) -> str:
    return PurePosixPath(raw.split("|", 1)[0].split("#", 1)[0].strip().replace("\\", "/")).stem


def lint_wiki(
    repo: Path,
    *,
    root: str = "wiki",
    base_snapshot: dict[str, Any] | None = None,
    snapshot: dict[str, Any] | None = None,
    allowed_log_missing_stems: Iterable[str] = (),
) -> dict[str, Any]:
    knowledge_root = normalize_root(root)
    wiki = _inside_repo(repo, knowledge_root)
    allowed_log_targets = {
        PurePosixPath(str(stem).strip().replace("\\", "/")).stem
        for stem in allowed_log_missing_stems
        if str(stem).strip()
    }
    findings: list[dict[str, Any]] = []
    if not wiki.is_dir():
        findings.append(_finding("critical", "missing_wiki", "Knowledge root does not exist.", knowledge_root))
        return {"ok": False, "root": knowledge_root, "summary": {"pages": 0, "critical": 1, "warning": 0}, "findings": findings}
    snapshot = snapshot or knowledge_snapshot(repo, root=root)
    records = snapshot["pages"]
    stems: dict[str, list[str]] = {}
    inbound: Counter[str] = Counter()
    index_counts: Counter[str] = Counter()
    index_sections: dict[str, list[str]] = {}
    for page, record in records.items():
        relative = record["relative"]
        stem = PurePosixPath(relative).stem
        stems.setdefault(stem, []).append(page)
        for error in record["parse_errors"]:
            findings.append(_finding("critical", "frontmatter", error, page))
        frontmatter, _, _ = parse_frontmatter_text((repo / page).read_text(encoding="utf-8"))
        for field in REQUIRED_FIELDS:
            if field not in frontmatter:
                findings.append(_finding("critical", "frontmatter", f"missing required field {field}", page))
        page_type = record.get("type")
        if page_type not in PAGE_TYPES:
            findings.append(_finding("critical", "frontmatter", "invalid page type", page, {"type": page_type}))
        else:
            location_error = _page_expected_location(relative, str(page_type))
            if location_error:
                findings.append(_finding("critical", "page_location", location_error, page))
        if not isinstance(record.get("title"), str) or not str(record.get("title") or "").strip():
            findings.append(_finding("critical", "frontmatter", "title must be a non-empty string", page))
        if record.get("status") not in PAGE_STATUSES:
            findings.append(_finding("critical", "frontmatter", "invalid page status", page, {"status": record.get("status")}))
        if not _valid_date(record.get("last_updated")):
            findings.append(_finding("critical", "frontmatter", "last_updated must be YYYY-MM-DD", page))
        if not isinstance(frontmatter.get("tags"), list):
            findings.append(_finding("critical", "frontmatter", "tags must be an array", page))
        elif not all(isinstance(item, str) and item.strip() for item in frontmatter.get("tags", [])):
            findings.append(_finding("critical", "frontmatter", "tags entries must be non-empty strings", page))
        if page_type == "decision":
            if not _valid_date(frontmatter.get("decision_date")):
                findings.append(_finding("critical", "frontmatter", "decision pages require decision_date", page))
            if frontmatter.get("decision_status") not in {
                "proposed",
                "accepted",
                "deprecated",
                "superseded",
            }:
                findings.append(_finding("critical", "frontmatter", "decision pages require a valid decision_status", page))
        if page_type == "dependency":
            for field in ("package_name", "version"):
                if not isinstance(frontmatter.get(field), str) or not frontmatter.get(field, "").strip():
                    findings.append(_finding("critical", "frontmatter", f"dependency pages require {field}", page))
        if record.get("source_error"):
            error = record["source_error"]
            findings.append(_finding("critical", error["code"], error["message"], page, error.get("details")))
        stored = record.get("source_fingerprint")
        computed = record.get("computed_source_fingerprint")
        if stored is None or record.get("verified_by") is None:
            findings.append(_finding("warning", "unsealed", "Page has not been sealed with source provenance.", page))
        elif stored != "none" and not isinstance(stored, str):
            findings.append(_finding("critical", "frontmatter", "source_fingerprint must be none or sha256:<hex>", page))
        elif stored != "none" and not FINGERPRINT_PATTERN.fullmatch(stored):
            findings.append(_finding("critical", "frontmatter", "source_fingerprint must be none or sha256:<hex>", page))
        elif computed is not None and stored != computed:
            findings.append(_finding("warning", "stale_source", "Page source fingerprint is stale.", page))
        if record.get("status") == "placeholder":
            findings.append(_finding("warning", "placeholder", "Page is still a placeholder.", page))
    for stem, pages in stems.items():
        if len(pages) > 1:
            findings.append(_finding("critical", "ambiguous_wikilink", f"Multiple pages share target {stem}.", details={"pages": pages}))
    for page in records:
        text = (repo / page).read_text(encoding="utf-8")
        if page == f"{knowledge_root}/index.md":
            section = ""
            for line in text.splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
                    continue
                for raw in _wikilinks(line):
                    target = _wikilink_target(raw)
                    if target:
                        index_sections.setdefault(target, []).append(section)
        for raw in _wikilinks(text):
            target = _wikilink_target(raw)
            if not target:
                continue
            if target not in stems:
                if (
                    page == f"{knowledge_root}/log.md"
                    and target in allowed_log_targets
                ):
                    continue
                findings.append(_finding("critical", "broken_wikilink", f"Missing target [[{raw}]].", page))
            else:
                inbound[target] += 1
                if page == f"{knowledge_root}/index.md":
                    index_counts[target] += 1
    for page, record in records.items():
        if record.get("type") in ("index", "log"):
            continue
        stem = PurePosixPath(record["relative"]).stem
        if page != f"{knowledge_root}/overview.md" and inbound[stem] == 0:
            findings.append(_finding("warning", "orphan", "Page has no inbound wikilink.", page))
        if index_counts[stem] == 0:
            findings.append(_finding("critical", "index_missing", "Page is missing from wiki/index.md.", page))
        elif index_counts[stem] > 1:
            findings.append(_finding("critical", "index_duplicate", "Page appears more than once in wiki/index.md.", page))
        expected_section = INDEX_SECTIONS.get(str(record.get("type")))
        actual_sections = index_sections.get(stem, [])
        if expected_section and actual_sections and any(
            section != expected_section for section in actual_sections
        ):
            findings.append(
                _finding(
                    "critical",
                    "index_section",
                    f"Page must be indexed under {expected_section}.",
                    page,
                    {"actual": actual_sections},
                )
            )
    if base_snapshot and base_snapshot.get("log"):
        base_files = base_snapshot.get("files", {})
        log_path = f"{knowledge_root}/log.md"
        if log_path in base_files and log_path not in snapshot["files"]:
            findings.append(_finding("critical", "log_deleted", "Append-only log was deleted.", log_path))
        elif log_path in snapshot["files"]:
            _, current_body, _ = parse_frontmatter_text((repo / log_path).read_text(encoding="utf-8"))
            base_length = int(base_snapshot["log"].get("body_length", 0))
            prefix = current_body.encode("utf-8")[:base_length]
            if len(prefix) != base_length or sha256_hex(prefix) != base_snapshot["log"].get("body_hash"):
                findings.append(_finding("critical", "log_rewritten", "Existing append-only log body was rewritten.", log_path))
    counts = Counter(item["severity"] for item in findings)
    return {
        "ok": counts["critical"] == 0,
        "root": knowledge_root,
        "summary": {
            "pages": len(records),
            "critical": counts["critical"],
            "warning": counts["warning"],
            "types": dict(sorted(Counter(str(item.get("type")) for item in records.values()).items())),
            "statuses": dict(sorted(Counter(str(item.get("status")) for item in records.values()).items())),
        },
        "findings": findings,
        "agent_review_required": [
            {"check": "module_coverage", "reason": "Importance and module boundaries require source interpretation."},
            {"check": "semantic_contradictions", "reason": "Cross-page claims require semantic review."},
        ],
        "fingerprint": snapshot["fingerprint"],
    }


def knowledge_status(
    repo: Path, *, root: str = "wiki", snapshot: dict[str, Any] | None = None
) -> dict[str, Any]:
    snapshot = snapshot or knowledge_snapshot(repo, root=root)
    lint = lint_wiki(repo, root=root, snapshot=snapshot)
    pages = snapshot.get("pages", {})
    placeholder = sorted(path for path, item in pages.items() if item.get("status") == "placeholder")
    stale = sorted(
        path
        for path, item in pages.items()
        if item.get("computed_source_fingerprint") is not None
        and item.get("source_fingerprint") != item.get("computed_source_fingerprint")
    )
    unsealed = sorted(path for path, item in pages.items() if not item.get("source_fingerprint") or not item.get("verified_by"))
    return {
        "root": normalize_root(root),
        "health": "critical" if lint["summary"]["critical"] else "warning" if lint["summary"]["warning"] else "healthy",
        "fingerprint": snapshot["fingerprint"],
        "pages": len(pages),
        "placeholder_pages": placeholder[:50],
        "stale_pages": stale[:50],
        "unsealed_pages": unsealed[:50],
        "critical": [item for item in lint["findings"] if item["severity"] == "critical"][:50],
        "warnings": [item for item in lint["findings"] if item["severity"] == "warning"][:50],
    }


def bootstrap_assessment(
    repo: Path, *, root: str = "wiki", snapshot: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return the deterministic readiness of the repository's core Wiki pages."""

    knowledge_root = normalize_root(root)
    snapshot = snapshot or knowledge_snapshot(repo, root=knowledge_root)
    lint = lint_wiki(repo, root=knowledge_root, snapshot=snapshot)
    pages = snapshot.get("pages", {})

    def ready(record: Any) -> bool:
        return bool(
            isinstance(record, dict)
            and record.get("status") == "active"
            and record.get("sources")
            and not record.get("parse_errors")
            and not record.get("source_error")
            and record.get("verified_by")
            and record.get("source_fingerprint") not in (None, "none")
            and record.get("source_fingerprint")
            == record.get("computed_source_fingerprint")
        )

    overview = f"{knowledge_root}/overview.md"
    architecture_pages = sorted(
        path
        for path, record in pages.items()
        if record.get("type") == "architecture" and ready(record)
    )
    module_pages = sorted(
        path
        for path, record in pages.items()
        if record.get("type") == "module" and ready(record)
    )
    reasons: list[str] = []
    if not ready(pages.get(overview)):
        reasons.append("overview_not_ready")
    if not architecture_pages:
        reasons.append("architecture_missing")
    if not module_pages:
        reasons.append("module_missing")
    if lint["summary"]["critical"]:
        reasons.append("critical_lint")
    return {
        "complete": not reasons,
        "recommended": bool(reasons),
        "reasons": reasons,
        "overview": overview if ready(pages.get(overview)) else None,
        "architecture_pages": architecture_pages[:50],
        "module_pages": module_pages[:50],
    }


def seal_pages(
    repo: Path,
    pages: Iterable[str],
    work_id: str,
    *,
    root: str = "wiki",
    today: str | None = None,
    allowed_log_missing_stems: Iterable[str] = (),
) -> list[dict[str, Any]]:
    if not WORK_PATTERN.fullmatch(work_id):
        raise KnowledgeError("invalid_work", "verified_by must be a valid work ID.")
    normalized = sorted({normalize_page(page, root) for page in pages})
    if not normalized:
        raise KnowledgeError("missing_page", "At least one Wiki page is required.")
    catalog = source_catalog(repo, root)
    prepared: list[tuple[Path, str, dict[str, Any]]] = []
    results: list[dict[str, Any]] = []
    for page in normalized:
        path = _inside_repo(repo, page)
        if not path.is_file():
            raise KnowledgeError("missing_page", "Wiki page does not exist.", {"page": page})
        text = path.read_text(encoding="utf-8")
        frontmatter, body, errors = parse_frontmatter_text(text)
        if errors:
            raise KnowledgeError("invalid_frontmatter", "Wiki page frontmatter cannot be sealed.", {"page": page, "errors": errors})
        if frontmatter.get("status") != "active":
            raise KnowledgeError(
                "page_not_ready",
                "Only active Wiki pages may be sealed.",
                {"page": page, "status": frontmatter.get("status")},
            )
        tokens = sorted(set(TEMPLATE_TOKEN_PATTERN.findall(text)))
        if tokens:
            raise KnowledgeError(
                "template_token",
                "Wiki page still contains canonical template tokens.",
                {"page": page, "tokens": tokens},
            )
        sources = normalize_sources(frontmatter.get("sources", []), root)
        fingerprint = source_fingerprint(repo, sources, root=root, catalog=catalog)
        frontmatter["sources"] = sources
        frontmatter["last_updated"] = (
            today or datetime.now(timezone.utc).date().isoformat()
        )
        frontmatter["source_fingerprint"] = fingerprint
        frontmatter["verified_by"] = work_id
        rendered = render_frontmatter(frontmatter, body)
        prepared.append((path, rendered, frontmatter))
        results.append({"page": page, "source_fingerprint": fingerprint, "last_updated": frontmatter["last_updated"], "verified_by": work_id})
    snapshot = knowledge_snapshot(repo, root=root)
    lint = lint_wiki(
        repo,
        root=root,
        snapshot=snapshot,
        allowed_log_missing_stems=allowed_log_missing_stems,
    )
    critical = [
        finding
        for finding in lint.get("findings", [])
        if finding.get("severity") == "critical"
    ]
    if critical:
        raise KnowledgeError(
            "critical_lint",
            "Wiki contains critical lint findings and cannot be sealed.",
            {"findings": critical[:50]},
        )
    for path, rendered, _ in prepared:
        _atomic_write(path, rendered)
    return results


def changed_knowledge_paths(base: dict[str, Any], current: dict[str, Any]) -> list[str]:
    before = base.get("files", {}) if isinstance(base, dict) else {}
    after = current.get("files", {}) if isinstance(current, dict) else {}
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def source_overlaps_path(source: str, changed: str) -> bool:
    source = PurePosixPath(source).as_posix().rstrip("/")
    changed = PurePosixPath(changed).as_posix().rstrip("/")
    return source == "." or changed == source or changed.startswith(source + "/") or source.startswith(changed + "/")


def affected_pages(base: dict[str, Any], changed_paths: Sequence[str]) -> list[str]:
    affected: list[str] = []
    for page, record in (base.get("pages", {}) if isinstance(base, dict) else {}).items():
        sources = record.get("sources", []) if isinstance(record, dict) else []
        if any(source_overlaps_path(source, changed) for source in sources for changed in changed_paths):
            affected.append(page)
    return sorted(affected)


def context_records(
    snapshot: dict[str, Any], pages: Sequence[str]
) -> list[dict[str, Any]]:
    """Project an ordered, serializable observation for each context page."""

    records: list[dict[str, Any]] = []
    snapshot_pages = snapshot.get("pages", {}) if isinstance(snapshot, dict) else {}
    for path in pages:
        record = snapshot_pages.get(path)
        records.append(
            {
                "path": path,
                "present": isinstance(record, dict),
                "status": record.get("status") if isinstance(record, dict) else None,
                "content_hash": record.get("file_hash") if isinstance(record, dict) else None,
                "source_fingerprint": record.get("source_fingerprint")
                if isinstance(record, dict)
                else None,
                "computed_source_fingerprint": record.get(
                    "computed_source_fingerprint"
                )
                if isinstance(record, dict)
                else None,
            }
        )
    return records


def coverage_paths(
    snapshot: dict[str, Any], changed_paths: Sequence[str]
) -> dict[str, list[str]]:
    """Split changed paths by whether an active Wiki page declares overlap."""

    sources: list[str] = []
    for record in (
        snapshot.get("pages", {}).values() if isinstance(snapshot, dict) else []
    ):
        if not isinstance(record, dict):
            continue
        if (
            record.get("status") != "active"
            or record.get("parse_errors")
            or record.get("source_error")
        ):
            continue
        sources.extend(record.get("sources", []))
    normalized = sorted(
        {PurePosixPath(path).as_posix() for path in changed_paths if path}
    )
    covered = [
        path
        for path in normalized
        if any(source_overlaps_path(source, path) for source in sources)
    ]
    return {
        "covered": covered,
        "uncovered": [path for path in normalized if path not in covered],
    }


def validate_promote_log(repo: Path, work_id: str, *, root: str = "wiki", base: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    path = _inside_repo(repo, f"{normalize_root(root)}/log.md")
    if not path.is_file():
        return ["wiki/log.md is required for knowledge promotion"]
    _, body, parse_errors = parse_frontmatter_text(path.read_text(encoding="utf-8"))
    if parse_errors:
        return ["wiki/log.md has invalid frontmatter"]
    if base and base.get("log"):
        prefix_length = int(base["log"].get("body_length", 0))
        encoded = body.encode("utf-8")
        prefix = encoded[:prefix_length]
        if len(prefix) != prefix_length or sha256_hex(prefix) != base["log"].get("body_hash"):
            errors.append("wiki/log.md existing body is not append-only")
        appended = encoded[prefix_length:].decode("utf-8", errors="replace")
    else:
        appended = body
    headings = re.findall(r"^##\s+.*?\bpromote\b.*$", appended, flags=re.MULTILINE | re.IGNORECASE)
    matching = [heading for heading in headings if work_id in heading]
    if len(headings) != 1 or len(matching) != 1:
        errors.append("wiki/log.md must append exactly one promote heading containing the work ID")
    return errors

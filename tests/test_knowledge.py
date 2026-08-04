from __future__ import annotations

import unittest
from pathlib import Path

from devweave_test_support import RepositoryHarness, core


knowledge = core.knowledge


def write_page(
    repo: Path,
    relative: str,
    page_type: str,
    sources: list[str],
    *,
    fingerprint: str | None = None,
    body: str = "\n# Fixture Knowledge\n\nEvidence-backed fixture page.\n",
) -> Path:
    page = repo / "wiki" / relative
    page.parent.mkdir(parents=True, exist_ok=True)
    values: dict[str, object] = {
        "title": Path(relative).stem.replace("-", " ").title(),
        "type": page_type,
        "sources": sources,
        "last_updated": "2099-01-01",
        "tags": [page_type],
        "status": "active",
        "source_fingerprint": fingerprint
        if fingerprint is not None
        else knowledge.source_fingerprint(repo, sources),
        "verified_by": "prior-work",
    }
    page.write_text(knowledge.render_frontmatter(values, body), encoding="utf-8")
    return page


def add_to_index(repo: Path, stem: str, section: str, summary: str = "Fixture page") -> None:
    index = repo / "wiki" / "index.md"
    text = index.read_text(encoding="utf-8")
    marker = f"## {section}\n\n"
    if marker not in text:
        raise AssertionError(f"Missing index section: {section}")
    text = text.replace(marker, marker + f"- [[{stem}]] | {summary}\n", 1)
    index.write_text(text, encoding="utf-8")


def prepare_sourced_feature(
    harness: RepositoryHarness, *, stale_unrelated: bool = False
) -> dict:
    harness.init()
    write_page(harness.repo, "modules/runtime.md", "module", ["src/app.txt"])
    add_to_index(harness.repo, "runtime", "Modules", "Runtime module")
    if stale_unrelated:
        write_page(
            harness.repo,
            "modules/unrelated.md",
            "module",
            ["README.md"],
            fingerprint="sha256:" + "0" * 64,
        )
        add_to_index(harness.repo, "unrelated", "Modules", "Unrelated stale page")
    state = core.create_work(
        harness.repo,
        kind="feature",
        title="Sourced Wiki fixture",
        risk="standard",
        risk_rationale="標準風險 fixture。",
    )
    work_id = state["id"]
    harness.fill_requirements(work_id)
    core.set_scope(harness.repo, work_id, ["src/**"], "限制產品來源範圍。")
    core.approve_gate(harness.repo, work_id, "scope", "Test Approver")
    harness.fill_design(work_id)
    state = core.approve_gate(harness.repo, work_id, "build", "Test Approver")
    harness.implement(work_id, "source behavior changed")
    return core.load_state(harness.repo, work_id)


def promote_runtime(
    harness: RepositoryHarness, work_id: str, *, delete: bool = False
) -> None:
    target = "wiki/modules/runtime.md"
    core.set_knowledge_plan(
        harness.repo,
        work_id,
        [] if delete else [target],
        [target] if delete else [],
        "刷新受本 work item 影響的 runtime knowledge。",
    )
    page = harness.repo / target
    index = harness.repo / "wiki" / "index.md"
    if delete:
        page.unlink()
        index.write_text(
            index.read_text(encoding="utf-8").replace(
                "- [[runtime]] | Runtime module\n", ""
            ),
            encoding="utf-8",
        )
    else:
        page.write_text(
            page.read_text(encoding="utf-8")
            + "\n## Promotion\n\nCurrent source behavior verified.\n",
            encoding="utf-8",
        )
        index.write_text(
            index.read_text(encoding="utf-8").replace(
                "Runtime module", "Runtime module refreshed"
            ),
            encoding="utf-8",
        )
    log = harness.repo / "wiki" / "log.md"
    log.write_text(
        log.read_text(encoding="utf-8")
        + f"\n## [2099-01-01] promote | {work_id}\n\n"
        + (
            "- Deleted the obsolete runtime knowledge target.\n"
            if delete
            else "- Refreshed the [[runtime]] knowledge target.\n"
        ),
        encoding="utf-8",
    )
    seal = ["wiki/index.md", "wiki/log.md"]
    if not delete:
        seal.append(target)
    core.seal_knowledge(harness.repo, work_id, seal)


def knowledge_acceptance(harness: RepositoryHarness, state: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    changed = core.changed_paths_since(harness.repo, state["base_source"])
    core._validate_knowledge_acceptance(
        harness.repo, core.load_state(harness.repo, state["id"]), changed, errors, warnings
    )
    return errors, warnings


class KnowledgeCoreTests(unittest.TestCase):
    def test_frontmatter_renderer_quotes_control_characters(self) -> None:
        rendered = knowledge.render_frontmatter(
            {
                "title": "Runtime\nModule",
                "type": "module",
                "sources": ["src/app.txt"],
                "last_updated": "2026-08-03",
                "tags": ["module"],
                "status": "placeholder",
            },
            "# Runtime Module\n",
        )

        frontmatter, body, errors = knowledge.parse_frontmatter_text(rendered)

        self.assertEqual([], errors)
        self.assertEqual("Runtime\nModule", frontmatter["title"])
        self.assertEqual("# Runtime Module\n", body)

    def test_bootstrap_assessment_requires_sourced_overview_architecture_and_module(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            pending = knowledge.bootstrap_assessment(harness.repo)
            self.assertFalse(pending["complete"])
            self.assertTrue(pending["recommended"])
            self.assertEqual(
                ["overview_not_ready", "architecture_missing", "module_missing"],
                pending["reasons"],
            )

            write_page(harness.repo, "overview.md", "overview", ["README.md"])
            write_page(
                harness.repo,
                "architecture/system.md",
                "architecture",
                ["src/app.txt"],
            )
            add_to_index(harness.repo, "system", "Architecture", "System architecture")
            write_page(
                harness.repo,
                "modules/runtime.md",
                "module",
                ["src/app.txt"],
            )
            add_to_index(harness.repo, "runtime", "Modules", "Runtime module")

            complete = knowledge.bootstrap_assessment(harness.repo)
            self.assertTrue(complete["complete"])
            self.assertFalse(complete["recommended"])
            self.assertEqual([], complete["reasons"])
            self.assertEqual("wiki/overview.md", complete["overview"])
            self.assertEqual(["wiki/architecture/system.md"], complete["architecture_pages"])
            self.assertEqual(["wiki/modules/runtime.md"], complete["module_pages"])

            extras = [
                ("modules/api.md", "module", "api", "Modules"),
                ("entities/work-item.md", "entity", "work-item", "Entities"),
                ("patterns/gates.md", "pattern", "gates", "Patterns"),
            ]
            for relative, page_type, stem, section in extras:
                write_page(harness.repo, relative, page_type, ["src/app.txt"])
                add_to_index(harness.repo, stem, section, f"{page_type} fixture")
            over_five = knowledge.bootstrap_assessment(harness.repo)
            self.assertTrue(over_five["complete"])
            self.assertEqual([], over_five["reasons"])
            self.assertGreater(
                len(knowledge.knowledge_snapshot(harness.repo)["pages"]) - 2,
                5,
            )

    def test_context_records_and_coverage_are_deterministic_and_source_bound(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            write_page(
                harness.repo,
                "modules/runtime.md",
                "module",
                ["src/app.txt"],
            )
            add_to_index(harness.repo, "runtime", "Modules", "Runtime module")
            snapshot = knowledge.knowledge_snapshot(harness.repo)

            records = knowledge.context_records(
                snapshot,
                [
                    "wiki/index.md",
                    "wiki/modules/runtime.md",
                    "wiki/modules/missing.md",
                ],
            )
            self.assertEqual(
                [
                    "wiki/index.md",
                    "wiki/modules/runtime.md",
                    "wiki/modules/missing.md",
                ],
                [record["path"] for record in records],
            )
            self.assertTrue(records[0]["present"])
            self.assertEqual("active", records[1]["status"])
            self.assertEqual(
                snapshot["pages"]["wiki/modules/runtime.md"]["file_hash"],
                records[1]["content_hash"],
            )
            self.assertEqual(
                snapshot["pages"]["wiki/modules/runtime.md"]["source_fingerprint"],
                records[1]["source_fingerprint"],
            )
            self.assertEqual(
                {
                    "path": "wiki/modules/missing.md",
                    "present": False,
                    "status": None,
                    "content_hash": None,
                    "source_fingerprint": None,
                    "computed_source_fingerprint": None,
                },
                records[2],
            )

            coverage = knowledge.coverage_paths(
                snapshot, ["README.md", "src/app.txt", "src/app.txt"]
            )
            self.assertEqual(["src/app.txt"], coverage["covered"])
            self.assertEqual(["README.md"], coverage["uncovered"])

            (harness.repo / "src/app.txt").write_text(
                "source currentness changed\n", encoding="utf-8"
            )
            changed_records = knowledge.context_records(
                knowledge.knowledge_snapshot(harness.repo),
                ["wiki/modules/runtime.md"],
            )
            self.assertEqual(records[1]["content_hash"], changed_records[0]["content_hash"])
            self.assertEqual(
                records[1]["source_fingerprint"],
                changed_records[0]["source_fingerprint"],
            )
            self.assertNotEqual(
                records[1]["computed_source_fingerprint"],
                changed_records[0]["computed_source_fingerprint"],
            )

    def test_scaffold_uses_canonical_template_and_never_overwrites(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            result = knowledge.scaffold_page(
                harness.repo,
                core.skill_root() / "assets",
                page="wiki/modules/runtime.md",
                page_type="module",
                title="Runtime Module",
                sources=["src/app.txt"],
                work_id="fixture-work",
                today="2099-01-02",
            )
            self.assertEqual("wiki/modules/runtime.md", result["page"])
            text = (harness.repo / result["page"]).read_text(encoding="utf-8")
            frontmatter, body, errors = knowledge.parse_frontmatter_text(text)
            self.assertEqual([], errors)
            self.assertEqual("Runtime Module", frontmatter["title"])
            self.assertEqual("module", frontmatter["type"])
            self.assertEqual(["src/app.txt"], frontmatter["sources"])
            self.assertEqual("placeholder", frontmatter["status"])
            self.assertEqual("none", frontmatter["source_fingerprint"])
            self.assertEqual("fixture-work", frontmatter["verified_by"])
            self.assertEqual("2099-01-02", frontmatter["last_updated"])
            self.assertIn("# Runtime Module", body)
            self.assertNotIn("<TITLE>", text)

            original = text
            with self.assertRaises(knowledge.KnowledgeError) as caught:
                knowledge.scaffold_page(
                    harness.repo,
                    core.skill_root() / "assets",
                    page="wiki/modules/runtime.md",
                    page_type="module",
                    title="Replacement",
                    sources=["README.md"],
                    work_id="fixture-work",
                )
            self.assertEqual("page_exists", caught.exception.code)
            self.assertEqual(
                original,
                (harness.repo / "wiki/modules/runtime.md").read_text(
                    encoding="utf-8"
                ),
            )

            invalid_targets = [
                ("../outside.md", ["src/app.txt"]),
                ("wiki/modules/escape.md", ["../outside.txt"]),
                ("wiki/modules/state.md", [".devweave/project.json"]),
                ("wiki/modules/wiki-source.md", ["wiki/index.md"]),
                ("wiki/modules/missing-source.md", ["src/missing.txt"]),
            ]
            for page, sources in invalid_targets:
                with self.subTest(page=page, sources=sources), self.assertRaises(
                    knowledge.KnowledgeError
                ):
                    knowledge.scaffold_page(
                        harness.repo,
                        core.skill_root() / "assets",
                        page=page,
                        page_type="module",
                        title="Invalid",
                        sources=sources,
                        work_id="fixture-work",
                    )
                if page.startswith("wiki/"):
                    self.assertFalse((harness.repo / page).exists())

    def test_seal_rejects_placeholder_and_template_tokens_before_writing(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            knowledge.scaffold_page(
                harness.repo,
                core.skill_root() / "assets",
                page="wiki/modules/runtime.md",
                page_type="module",
                title="Runtime Module",
                sources=["src/app.txt"],
                work_id="fixture-work",
                today="2099-01-02",
            )
            add_to_index(harness.repo, "runtime", "Modules", "Runtime module")
            page = harness.repo / "wiki/modules/runtime.md"
            original = page.read_text(encoding="utf-8")
            with self.assertRaises(knowledge.KnowledgeError) as placeholder:
                knowledge.seal_pages(
                    harness.repo,
                    ["wiki/modules/runtime.md"],
                    "fixture-work",
                )
            self.assertEqual("page_not_ready", placeholder.exception.code)
            self.assertEqual(original, page.read_text(encoding="utf-8"))

            page.write_text(
                original.replace("status: placeholder", "status: active")
                + "\n## Verified behavior\n\n<DETAILS>\n",
                encoding="utf-8",
            )
            with self.assertRaises(knowledge.KnowledgeError) as token:
                knowledge.seal_pages(
                    harness.repo,
                    ["wiki/modules/runtime.md"],
                    "fixture-work",
                )
            self.assertEqual("template_token", token.exception.code)

            page.write_text(
                page.read_text(encoding="utf-8").replace(
                    "<DETAILS>", "Runtime behavior is source-bound."
                ),
                encoding="utf-8",
            )
            sealed = knowledge.seal_pages(
                harness.repo,
                ["wiki/modules/runtime.md"],
                "fixture-work",
                today="2099-01-03",
            )
            self.assertEqual("wiki/modules/runtime.md", sealed[0]["page"])
            frontmatter, _, _ = knowledge.parse_frontmatter_text(
                page.read_text(encoding="utf-8")
            )
            self.assertEqual("active", frontmatter["status"])
            self.assertEqual("2099-01-03", frontmatter["last_updated"])
            self.assertEqual(
                knowledge.source_fingerprint(harness.repo, ["src/app.txt"]),
                frontmatter["source_fingerprint"],
            )

    def test_all_canonical_templates_declare_placeholder_scaffold_tokens(self) -> None:
        templates = core.skill_root() / "assets" / "wiki" / "templates"
        expected = {
            "overview",
            "architecture",
            "module",
            "entity",
            "pattern",
            "dependency",
            "decision",
            "guide",
            "synthesis",
        }
        self.assertEqual(expected, {path.stem for path in templates.glob("*.md")})
        for page_type in sorted(expected):
            with self.subTest(page_type=page_type):
                text = (templates / f"{page_type}.md").read_text(encoding="utf-8")
                frontmatter, body, errors = knowledge.parse_frontmatter_text(text)
                self.assertEqual([], errors)
                self.assertEqual(page_type, frontmatter["type"])
                self.assertEqual("placeholder", frontmatter["status"])
                self.assertEqual("<DATE>", frontmatter["last_updated"])
                self.assertEqual("<WORK_ID>", frontmatter["verified_by"])
                self.assertIn("<TITLE>", body)

    def test_scaffold_supports_all_nine_types_and_conditional_fields(self) -> None:
        cases = [
            ("overview", "wiki/overview.md", {}),
            ("architecture", "wiki/architecture/system.md", {}),
            ("module", "wiki/modules/runtime.md", {}),
            ("entity", "wiki/entities/order.md", {}),
            ("pattern", "wiki/patterns/repository.md", {}),
            (
                "dependency",
                "wiki/dependencies/python.md",
                {"package_name": "python", "version": "3.11+"},
            ),
            (
                "decision",
                "wiki/decisions/wiki.md",
                {
                    "decision_date": "2099-01-02",
                    "decision_status": "accepted",
                },
            ),
            ("guide", "wiki/guides/run.md", {}),
            ("synthesis", "wiki/synthesis/question.md", {}),
        ]
        for page_type, page, extras in cases:
            with self.subTest(page_type=page_type), RepositoryHarness() as harness:
                harness.init()
                if page_type == "overview":
                    (harness.repo / "wiki/overview.md").unlink()
                knowledge.scaffold_page(
                    harness.repo,
                    core.skill_root() / "assets",
                    page=page,
                    page_type=page_type,
                    title=f"{page_type.title()} Knowledge",
                    sources=["src/app.txt"],
                    work_id="fixture-work",
                    today="2099-01-02",
                    **extras,
                )
                frontmatter, _, errors = knowledge.parse_frontmatter_text(
                    (harness.repo / page).read_text(encoding="utf-8")
                )
                self.assertEqual([], errors)
                self.assertEqual(page_type, frontmatter["type"])
                for key, value in extras.items():
                    self.assertEqual(value, frontmatter[key])

        with RepositoryHarness() as harness:
            harness.init()
            assets = core.skill_root() / "assets"
            invalid_cases = [
                {
                    "page": "wiki/dependencies/python.md",
                    "page_type": "dependency",
                },
                {
                    "page": "wiki/decisions/wiki.md",
                    "page_type": "decision",
                    "decision_date": "not-a-date",
                    "decision_status": "accepted",
                },
                {
                    "page": "wiki/modules/runtime.md",
                    "page_type": "module",
                    "package_name": "unexpected",
                },
                {
                    "page": "wiki/entities/wrong.md",
                    "page_type": "module",
                },
            ]
            for case in invalid_cases:
                with self.subTest(case=case), self.assertRaises(
                    knowledge.KnowledgeError
                ):
                    knowledge.scaffold_page(
                        harness.repo,
                        assets,
                        title="Invalid",
                        sources=["src/app.txt"],
                        work_id="fixture-work",
                        **case,
                    )

    def test_frontmatter_parser_and_lint_cover_links_uniqueness_and_index(self) -> None:
        parsed, body, errors = knowledge.parse_frontmatter_text(
            "---\ntitle: Example\nsources:\n  - src/app.txt\ntags: [one, two]\n---\n\nBody\n"
        )
        self.assertEqual([], errors)
        self.assertEqual(["src/app.txt"], parsed["sources"])
        self.assertEqual(["one", "two"], parsed["tags"])
        self.assertIn("Body", body)

        with RepositoryHarness() as harness:
            harness.init()
            write_page(
                harness.repo,
                "modules/shared.md",
                "module",
                [],
                body="\n# Shared Module\n\nSee [[missing-target]].\n",
            )
            write_page(harness.repo, "entities/shared.md", "entity", [])
            add_to_index(harness.repo, "shared", "Entities")
            report = knowledge.lint_wiki(harness.repo)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("ambiguous_wikilink", codes)
            self.assertIn("broken_wikilink", codes)
            self.assertIn("index_section", codes)

    def test_bootstrap_is_idempotent_and_adopts_without_overwrite(self) -> None:
        with RepositoryHarness() as harness:
            first = harness.init()
            before = {
                path.relative_to(harness.repo).as_posix(): path.read_bytes()
                for path in (harness.repo / "wiki").rglob("*")
                if path.is_file()
            }
            second = harness.init()
            after = {
                path.relative_to(harness.repo).as_posix(): path.read_bytes()
                for path in (harness.repo / "wiki").rglob("*")
                if path.is_file()
            }
            self.assertEqual(first["knowledge"], second["knowledge"])
            self.assertEqual(before, after)

        with RepositoryHarness() as harness:
            wiki = harness.repo / "wiki"
            wiki.mkdir()
            custom = "---\ntitle: Custom Index\ntype: index\nsources: []\nlast_updated: 2026-01-01\ntags: [index]\nstatus: active\n---\n\n# User index\n"
            (wiki / "index.md").write_text(custom, encoding="utf-8")
            harness.init()
            self.assertEqual(custom, (wiki / "index.md").read_text(encoding="utf-8"))
            self.assertTrue((wiki / "overview.md").is_file())
            self.assertTrue((wiki / "log.md").is_file())

    def test_bootstrap_conflict_is_reported_without_touching_user_content(self) -> None:
        with RepositoryHarness() as harness:
            wiki = harness.repo / "wiki"
            wiki.mkdir()
            custom = wiki / "notes.md"
            custom.write_text("user-owned\n", encoding="utf-8")
            harness.init()
            self.assertEqual("user-owned\n", custom.read_text(encoding="utf-8"))
            self.assertTrue((wiki / "index.md").is_file())
            self.assertTrue((wiki / "overview.md").is_file())
            self.assertTrue((wiki / "log.md").is_file())
            self.assertTrue((wiki / "modules").is_dir())
            knowledge_check = next(
                item for item in core.doctor(harness.repo)["checks"]
                if item["name"] == "knowledge"
            )
            self.assertTrue(knowledge_check["ok"])

        with RepositoryHarness() as harness:
            wiki = harness.repo / "wiki"
            wiki.mkdir()
            (wiki / "index.md").write_text(
                "---\ntitle: User Index\ntype: index\nsources: []\n"
                "last_updated: 2026-01-01\ntags: [index]\nstatus: active\n---\n",
                encoding="utf-8",
            )
            incompatible = "---\ntitle: User Notes\ntype: guide\nsources: []\n---\n\nKeep me.\n"
            (wiki / "overview.md").write_text(incompatible, encoding="utf-8")
            with self.assertRaises(core.ValidationError) as caught:
                harness.init()
            self.assertEqual("knowledge_conflict", caught.exception.details["code"])
            self.assertEqual(
                incompatible, (wiki / "overview.md").read_text(encoding="utf-8")
            )
            self.assertFalse((harness.repo / ".devweave").exists())

        with RepositoryHarness() as harness:
            wiki = harness.repo / "wiki"
            wiki.mkdir()
            (wiki / "modules").write_text("user-owned directory placeholder\n", encoding="utf-8")
            with self.assertRaises(core.ValidationError) as caught:
                harness.init()
            self.assertEqual("knowledge_conflict", caught.exception.details["code"])
            self.assertEqual(
                "user-owned directory placeholder\n",
                (wiki / "modules").read_text(encoding="utf-8"),
            )
            self.assertFalse((harness.repo / ".devweave").exists())

    def test_project_upgrade_is_read_only_until_init_and_legacy_state_loads(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            project = core.read_json(core.project_path(harness.repo))
            project.pop("knowledge")
            core.atomic_write_json(core.project_path(harness.repo), project)
            self.assertIn("knowledge", core.load_project(harness.repo))
            self.assertNotIn("knowledge", core.read_json(core.project_path(harness.repo)))
            harness.init()
            self.assertIn("knowledge", core.read_json(core.project_path(harness.repo)))

            state = core.create_work(
                harness.repo,
                kind="feature",
                title="Legacy compatibility",
                risk_rationale="fixture",
            )
            for key in (
                "base_knowledge",
                "knowledge_context",
                "knowledge_review_required",
                "knowledge_review",
                "knowledge_updates",
            ):
                state.pop(key)
            core.atomic_write_json(core.state_path(harness.repo, state["id"]), state)
            loaded = core.load_state(harness.repo, state["id"])
            errors: list[str] = []
            core._validate_knowledge_acceptance(
                harness.repo, loaded, [], errors, []
            )
            self.assertEqual([], errors)

    def test_source_fingerprint_tracks_dirty_directory_rename_delete_and_ignores_ignored(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            file_before = knowledge.source_fingerprint(harness.repo, ["src/app.txt"])
            directory_before = knowledge.source_fingerprint(harness.repo, ["src"])
            (harness.repo / "src" / "app.txt").write_text("dirty\n", encoding="utf-8")
            self.assertNotEqual(
                file_before, knowledge.source_fingerprint(harness.repo, ["src/app.txt"])
            )
            dirty_directory = knowledge.source_fingerprint(harness.repo, ["src"])
            self.assertNotEqual(directory_before, dirty_directory)

            untracked = harness.repo / "src" / "new.txt"
            untracked.write_text("non-ignored untracked\n", encoding="utf-8")
            with_untracked = knowledge.source_fingerprint(harness.repo, ["src"])
            self.assertNotEqual(dirty_directory, with_untracked)
            untracked.unlink()

            gitignore = harness.repo / ".gitignore"
            gitignore.write_text(
                gitignore.read_text(encoding="utf-8") + "src/ignored.tmp\n",
                encoding="utf-8",
            )
            before_ignored = knowledge.source_fingerprint(harness.repo, ["src"])
            (harness.repo / "src" / "ignored.tmp").write_text("ignored\n", encoding="utf-8")
            self.assertEqual(
                before_ignored, knowledge.source_fingerprint(harness.repo, ["src"])
            )

            (harness.repo / "src" / "app.txt").rename(
                harness.repo / "src" / "renamed.txt"
            )
            renamed = knowledge.source_fingerprint(harness.repo, ["src"])
            self.assertNotEqual(before_ignored, renamed)
            (harness.repo / "src" / "renamed.txt").unlink()
            deleted = knowledge.source_fingerprint(harness.repo, ["src"])
            self.assertNotEqual(renamed, deleted)
            with self.assertRaises(knowledge.KnowledgeError):
                knowledge.source_fingerprint(harness.repo, ["src/app.txt"])
            with self.assertRaises(knowledge.KnowledgeError):
                knowledge.source_fingerprint(harness.repo, ["../outside.txt"])


class KnowledgeLifecycleTests(unittest.TestCase):
    def test_only_affected_page_blocks_and_unrelated_stale_page_warns(self) -> None:
        with RepositoryHarness() as harness:
            state = prepare_sourced_feature(harness, stale_unrelated=True)
            with self.assertRaises(core.ValidationError) as no_update:
                core.set_knowledge_review(
                    harness.repo,
                    state["id"],
                    "no-update",
                    "Affected page 存在時不得略過 refresh。",
                )
            self.assertIn("not allowed", no_update.exception.message.lower())
            status = core.work_knowledge_status(harness.repo, state)
            self.assertEqual(["wiki/modules/runtime.md"], status["affected_pages"])
            self.assertEqual(["wiki/modules/runtime.md"], status["pending_refresh"])
            errors, warnings = knowledge_acceptance(harness, state)
            self.assertTrue(any("runtime.md" in item and "Affected" in item for item in errors))
            self.assertFalse(any("unrelated.md" in item and "Affected" in item for item in errors))
            self.assertTrue(any("unrelated.md" in item and "stale_source" in item for item in warnings))

    def test_plan_requires_real_changes_and_seal_rejects_unplanned_pages(self) -> None:
        with RepositoryHarness() as harness:
            state = prepare_sourced_feature(harness)
            work_id = state["id"]
            updates = core.set_knowledge_plan(
                harness.repo,
                work_id,
                ["wiki/modules/runtime.md"],
                [],
                "Refresh runtime.",
            )
            self.assertEqual(
                ["wiki/index.md", "wiki/log.md"], updates["coupled"]
            )
            with self.assertRaises(core.ValidationError):
                core.seal_knowledge(
                    harness.repo, work_id, ["wiki/modules/unplanned.md"]
                )
            overview = harness.repo / "wiki" / "overview.md"
            overview.write_text(
                overview.read_text(encoding="utf-8") + "\nUndeclared drift.\n",
                encoding="utf-8",
            )
            errors, _ = knowledge_acceptance(harness, state)
            self.assertTrue(any("no work-item change" in item for item in errors))
            self.assertTrue(any("were not declared" in item for item in errors))

    def test_refresh_promotion_passes_g3_and_wiki_only_change_stales_only_g3(self) -> None:
        with RepositoryHarness() as harness:
            state = prepare_sourced_feature(harness, stale_unrelated=True)
            work_id = state["id"]
            promote_runtime(harness, work_id)
            errors, warnings = knowledge_acceptance(harness, state)
            self.assertEqual([], errors)
            self.assertTrue(any("unrelated.md" in item for item in warnings))

            harness.configure_command()
            first = core.run_verification(
                harness.repo,
                work_id,
                command_id="fixture-tests",
                kind="acceptance",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            second = core.add_evidence(
                harness.repo,
                work_id,
                kind="regression",
                status="passed",
                summary="Knowledge-aware regression passed.",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            core.set_baseline_updates(harness.repo, work_id, [], "基線不需更新。")
            harness.fill_acceptance(work_id, [first["id"], second["id"]])
            report = core.validate_work(
                harness.repo, core.load_state(harness.repo, work_id), "acceptance"
            )
            self.assertTrue(report.ok, report.errors)
            accepted = core.approve_gate(
                harness.repo, work_id, "acceptance", "Test Approver"
            )

            index = harness.repo / "wiki" / "index.md"
            accepted_index = index.read_text(encoding="utf-8")
            index.write_text(accepted_index + "\nWiki-only drift.\n", encoding="utf-8")
            stale = core.sync_state(harness.repo, work_id)
            self.assertEqual("stale", stale["gates"]["acceptance"]["status"])
            self.assertFalse(stale["evidence"][first["id"]]["stale"])
            self.assertIsNotNone(stale["last_verification"])

            index.write_text(accepted_index, encoding="utf-8")
            reapproved = core.approve_gate(
                harness.repo, work_id, "acceptance", "Test Approver"
            )
            self.assertEqual("acceptance_review", reapproved["phase"])
            self.assertEqual("closed", core.close_work(harness.repo, work_id)["status"])

    def test_declared_delete_and_append_only_log_rules(self) -> None:
        with RepositoryHarness() as harness:
            state = prepare_sourced_feature(harness)
            promote_runtime(harness, state["id"], delete=True)
            errors, _ = knowledge_acceptance(harness, state)
            self.assertEqual([], errors)

        with RepositoryHarness() as harness:
            state = prepare_sourced_feature(harness)
            promote_runtime(harness, state["id"])
            log = harness.repo / "wiki" / "log.md"
            log.write_text(
                log.read_text(encoding="utf-8").replace(
                    "Append-only chronological record", "Rewritten historical record"
                ),
                encoding="utf-8",
            )
            errors, _ = knowledge_acceptance(harness, state)
            self.assertTrue(any("log_rewritten" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()

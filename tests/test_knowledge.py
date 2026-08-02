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
            with self.assertRaises(core.ValidationError) as caught:
                harness.init()
            self.assertEqual("knowledge_conflict", caught.exception.details["code"])
            self.assertEqual("user-owned\n", custom.read_text(encoding="utf-8"))
            self.assertFalse((wiki / "index.md").exists())
            knowledge_check = next(
                item for item in core.doctor(harness.repo)["checks"]
                if item["name"] == "knowledge"
            )
            self.assertFalse(knowledge_check["ok"])
            self.assertIn("knowledge_conflict", knowledge_check["detail"])

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
            for key in ("base_knowledge", "knowledge_context", "knowledge_updates"):
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

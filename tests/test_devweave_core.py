from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

from devweave_test_support import RepositoryHarness, core, load_scenarios, run_git


class EndToEndProfileTests(unittest.TestCase):
    def test_all_entry_profiles_reach_closed_with_required_evidence(self) -> None:
        for scenario in load_scenarios():
            with self.subTest(kind=scenario["kind"]), RepositoryHarness() as harness:
                state = harness.prepare_g2(scenario["kind"], scenario["title"])
                work_id = state["id"]
                self.assertEqual(
                    "references/implementation-phase.md",
                    core.instructions(harness.repo, state)["reference"],
                )
                harness.implement(work_id, scenario["kind"])
                if scenario["kind"] == "new":
                    harness.promote_overview(work_id)
                self.assertEqual(
                    "references/verification-phase.md",
                    core.instructions(
                        harness.repo, core.load_state(harness.repo, work_id)
                    )["reference"],
                )
                harness.configure_command()

                evidence_ids: list[str] = []
                first_kind, *remaining = scenario["required_evidence"]
                executed = core.run_verification(
                    harness.repo,
                    work_id,
                    command_id="fixture-tests",
                    kind=first_kind,
                    covers=["AC-001", "AC-002"],
                    tasks=["TASK-001"],
                )
                evidence_ids.append(executed["id"])
                for evidence_kind in remaining:
                    manual = core.add_evidence(
                        harness.repo,
                        work_id,
                        kind=evidence_kind,
                        status="passed",
                        summary=f"{evidence_kind} 驗證通過。",
                        covers=["AC-001", "AC-002"],
                        tasks=["TASK-001"],
                        observed_result="success",
                    )
                    evidence_ids.append(manual["id"])

                baseline_target = scenario["baseline_target"]
                if baseline_target:
                    target = harness.repo / baseline_target
                    target.write_text(
                        "# 架構基線\n\n第一個 vertical slice 已接受。\n",
                        encoding="utf-8",
                    )
                    core.set_baseline_updates(
                        harness.repo,
                        work_id,
                        [baseline_target],
                        "new 入口建立架構 living baseline。",
                    )
                else:
                    core.set_baseline_updates(
                        harness.repo,
                        work_id,
                        [],
                        "本變更未改變產品或架構基線。",
                    )
                harness.fill_acceptance(work_id, evidence_ids)

                report = core.validate_work(
                    harness.repo, core.load_state(harness.repo, work_id), "acceptance"
                )
                self.assertTrue(report.ok, report.errors)
                accepted = core.approve_gate(
                    harness.repo, work_id, "acceptance", "Test Approver"
                )
                self.assertEqual("approved", accepted["gates"]["acceptance"]["status"])
                self.assertEqual("close", core.instructions(harness.repo, accepted)["next_action"])
                closed = core.close_work(harness.repo, work_id)
                self.assertEqual("closed", closed["status"])
                self.assertTrue(all(gate["approved_by"] for gate in closed["gates"].values()))
                with self.assertRaises(core.ValidationError):
                    core.revise_work(
                        harness.repo, work_id, "implementation", "closed item 不可重開。"
                    )
                if scenario["kind"] == "bug":
                    replacement = core.create_work(
                        harness.repo,
                        kind="bug",
                        title=scenario["title"],
                        risk_rationale="後續變更使用新的工作項。",
                    )
                    self.assertNotEqual(work_id, replacement["id"])

    def test_bootstrap_profile_reaches_g3_through_scaffold_and_seal(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            created = core.bootstrap_knowledge_work(harness.repo)
            work_id = created["work"]["id"]
            harness.fill_requirements(work_id)
            core.set_scope(
                harness.repo,
                work_id,
                ["wiki/**"],
                "Bootstrap 僅提升 Wiki，不修改產品 source。",
            )
            core.approve_gate(harness.repo, work_id, "scope", "Test Approver")
            harness.fill_design(work_id)
            core.approve_gate(harness.repo, work_id, "build", "Test Approver")
            core.update_task(harness.repo, work_id, "TASK-001", "start")
            core.update_task(
                harness.repo,
                work_id,
                "TASK-001",
                "complete",
                note="已選定 overview、architecture 與 module 三個核心頁。",
            )
            with self.assertRaises(core.ValidationError) as no_update:
                core.set_knowledge_review(
                    harness.repo,
                    work_id,
                    "no-update",
                    "Bootstrap 不允許略過核心知識提升。",
                )
            self.assertIn("not allowed", no_update.exception.message.lower())
            core.set_knowledge_review(
                harness.repo,
                work_id,
                "promote",
                "Bootstrap 建立可重用的 repository 核心知識。",
            )
            pages = [
                "wiki/overview.md",
                "wiki/architecture/system.md",
                "wiki/modules/runtime.md",
            ]
            core.set_knowledge_plan(
                harness.repo,
                work_id,
                pages,
                [],
                "建立三個 source-bound 核心頁。",
            )
            core.scaffold_knowledge(
                harness.repo,
                work_id,
                page="wiki/architecture/system.md",
                page_type="architecture",
                title="System Architecture",
                sources=["src/app.txt"],
            )
            core.scaffold_knowledge(
                harness.repo,
                work_id,
                page="wiki/modules/runtime.md",
                page_type="module",
                title="Runtime Module",
                sources=["src/app.txt"],
            )

            for page in pages:
                target = harness.repo / page
                frontmatter, _, errors = core.knowledge.parse_frontmatter_text(
                    target.read_text(encoding="utf-8")
                )
                self.assertEqual([], errors)
                frontmatter["sources"] = ["src/app.txt"]
                frontmatter["status"] = "active"
                target.write_text(
                    core.knowledge.render_frontmatter(
                        frontmatter,
                        f"\n# {frontmatter['title']}\n\n"
                        "此頁由目前 fixture source 驗證，描述可重用的核心邊界。\n",
                    ),
                    encoding="utf-8",
                )

            index = harness.repo / "wiki/index.md"
            index_text = index.read_text(encoding="utf-8")
            index_text = index_text.replace(
                "_尚無頁面。_",
                "- [[system]] | Source-bound system architecture",
                1,
            ).replace(
                "_尚無頁面。_",
                "- [[runtime]] | Source-bound runtime module",
                1,
            )
            index.write_text(index_text, encoding="utf-8")
            log = harness.repo / "wiki/log.md"
            log.write_text(
                log.read_text(encoding="utf-8")
                + f"\n## [2099-01-01] promote | {work_id}\n\n"
                + "- Promoted overview, architecture, and module from fixture sources.\n",
                encoding="utf-8",
            )
            core.seal_knowledge(
                harness.repo,
                work_id,
                [*pages, "wiki/index.md", "wiki/log.md"],
            )

            harness.configure_command()
            regression = core.run_verification(
                harness.repo,
                work_id,
                command_id="fixture-tests",
                kind="regression",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            acceptance = core.add_evidence(
                harness.repo,
                work_id,
                kind="acceptance",
                status="passed",
                summary="Bootstrap 核心 Wiki 可由 index 定位並通過 source-bound 驗收。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
                observed_result="success",
            )
            core.set_baseline_updates(
                harness.repo,
                work_id,
                [],
                "Bootstrap 不改變 accepted product 或 architecture baseline。",
            )
            harness.fill_acceptance(work_id, [regression["id"], acceptance["id"]])

            state = core.load_state(harness.repo, work_id)
            report = core.validate_work(harness.repo, state, "acceptance")
            self.assertTrue(report.ok, report.errors)
            approved = core.approve_gate(
                harness.repo, work_id, "acceptance", "Test Approver"
            )
            self.assertEqual("approved", approved["gates"]["acceptance"]["status"])
            self.assertEqual("closed", core.close_work(harness.repo, work_id)["status"])
            self.assertEqual(
                "already_complete",
                core.bootstrap_knowledge_work(harness.repo)["action"],
            )


class StateAndFingerprintTests(unittest.TestCase):
    def test_bootstrap_work_is_created_resumed_or_skipped_when_complete(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            created = core.bootstrap_knowledge_work(harness.repo)
            self.assertEqual("created", created["action"])
            self.assertEqual("feature", created["work"]["kind"])
            self.assertEqual("bootstrap", created["work"]["knowledge_profile"])
            self.assertTrue(created["work"]["knowledge_review_required"])

            resumed = core.bootstrap_knowledge_work(harness.repo)
            self.assertEqual("resume", resumed["action"])
            self.assertEqual(created["work"]["id"], resumed["work"]["id"])
            self.assertEqual(1, len(core.list_work(harness.repo)))

        with RepositoryHarness() as harness:
            harness.init()

            def write_core_page(relative: str, page_type: str) -> None:
                sources = ["src/app.txt"]
                values = {
                    "title": page_type.title(),
                    "type": page_type,
                    "sources": sources,
                    "last_updated": "2099-01-01",
                    "tags": [page_type],
                    "status": "active",
                    "source_fingerprint": core.knowledge.source_fingerprint(
                        harness.repo, sources
                    ),
                    "verified_by": "prior-work",
                }
                target = harness.repo / "wiki" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    core.knowledge.render_frontmatter(
                        values, f"\n# {page_type.title()}\n\nSource-bound.\n"
                    ),
                    encoding="utf-8",
                )

            write_core_page("overview.md", "overview")
            write_core_page("architecture/system.md", "architecture")
            write_core_page("modules/runtime.md", "module")
            index = harness.repo / "wiki/index.md"
            text = index.read_text(encoding="utf-8")
            text = text.replace(
                "## Architecture\n\n", "## Architecture\n\n- [[system]] | System\n"
            )
            text = text.replace(
                "## Modules\n\n", "## Modules\n\n- [[runtime]] | Runtime\n"
            )
            index.write_text(text, encoding="utf-8")

            complete = core.bootstrap_knowledge_work(harness.repo)
            self.assertEqual("already_complete", complete["action"])
            self.assertIsNone(complete["work"])
            self.assertTrue(complete["bootstrap"]["complete"])
            self.assertEqual([], core.list_work(harness.repo))

    def test_bootstrap_acceptance_requires_core_plan_and_zero_product_diff(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            created = core.bootstrap_knowledge_work(harness.repo)
            work_id = created["work"]["id"]
            harness.fill_requirements(work_id)
            core.set_scope(
                harness.repo,
                work_id,
                ["src/**"],
                "Bootstrap 不修改產品程式碼；scope 僅供偵測違規 diff。",
            )
            core.approve_gate(harness.repo, work_id, "scope", "Test Approver")
            harness.fill_design(work_id)
            core.approve_gate(harness.repo, work_id, "build", "Test Approver")
            core.update_task(harness.repo, work_id, "TASK-001", "start")
            core.update_task(
                harness.repo,
                work_id,
                "TASK-001",
                "complete",
                note="Bootstrap knowledge design complete.",
            )
            core.set_knowledge_review(
                harness.repo,
                work_id,
                "promote",
                "建立可長期重用的 repository 核心知識。",
            )
            core.set_knowledge_plan(
                harness.repo,
                work_id,
                ["wiki/overview.md"],
                [],
                "不完整的 bootstrap plan 應在 G3 被拒絕。",
            )

            state = core.load_state(harness.repo, work_id)
            errors: list[str] = []
            core._validate_knowledge_acceptance(
                harness.repo,
                state,
                core.changed_paths_since(harness.repo, state["base_source"]),
                errors,
                [],
            )
            self.assertTrue(any("three to five" in item.lower() for item in errors))
            self.assertTrue(any("architecture" in item.lower() for item in errors))
            self.assertTrue(any("module" in item.lower() for item in errors))

            (harness.repo / "src/app.txt").write_text(
                "baseline\nbootstrap must reject this product diff\n",
                encoding="utf-8",
            )
            core.set_knowledge_review(
                harness.repo,
                work_id,
                "promote",
                "重新檢視變更後仍須 promote，但產品 diff 必須阻擋 G3。",
            )
            core.set_knowledge_plan(
                harness.repo,
                work_id,
                [
                    "wiki/overview.md",
                    "wiki/architecture/system.md",
                    "wiki/modules/runtime.md",
                ],
                [],
                "宣告三個核心頁以隔離產品 diff 規則。",
            )
            state = core.load_state(harness.repo, work_id)
            errors = []
            core._validate_knowledge_acceptance(
                harness.repo,
                state,
                core.changed_paths_since(harness.repo, state["base_source"]),
                errors,
                [],
            )
            self.assertTrue(any("product source" in item.lower() for item in errors))

    def test_new_work_declares_additive_knowledge_review_contract(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            self.assertTrue(state["knowledge_review_required"])
            self.assertNotIn("knowledge_profile", state)
            self.assertEqual([], state["knowledge_context"]["records"])
            self.assertEqual(
                {
                    "disposition": None,
                    "rationale": "",
                    "affected_pages": [],
                    "covered_changed_paths": [],
                    "uncovered_changed_paths": [],
                    "change_fingerprint": None,
                    "recorded_at": None,
                    "invalidated_at": None,
                },
                state["knowledge_review"],
            )
            self.assertIsNone(state["knowledge_updates"]["change_fingerprint"])

            for key in ("knowledge_review_required", "knowledge_review"):
                state.pop(key)
            state["knowledge_context"].pop("records")
            state["knowledge_updates"].pop("change_fingerprint")
            core.atomic_write_json(core.state_path(harness.repo, state["id"]), state)
            legacy = core.load_state(harness.repo, state["id"])
            self.assertNotIn("knowledge_review_required", legacy)
            self.assertNotIn("knowledge_review", legacy)
            self.assertTrue(
                core.work_knowledge_status(harness.repo, legacy)["legacy_work"]
            )

    def test_new_work_rejects_malformed_knowledge_context_record(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            valid_record = {
                "path": "wiki/index.md",
                "present": True,
                "status": "active",
                "content_hash": "abc",
                "source_fingerprint": None,
                "computed_source_fingerprint": None,
            }
            malformed_records = [
                {**valid_record, "content_hash": ["not", "a", "hash"]},
                {
                    key: value
                    for key, value in valid_record.items()
                    if key != "source_fingerprint"
                },
            ]
            for record in malformed_records:
                with self.subTest(record=record):
                    state["knowledge_context"]["records"] = [record]
                    core.atomic_write_json(
                        core.state_path(harness.repo, state["id"]), state
                    )

                    with self.assertRaises(core.ValidationError) as raised:
                        core.load_state(harness.repo, state["id"])

                    self.assertIn(
                        "knowledge_context.records is invalid",
                        raised.exception.details["errors"],
                    )

    def test_new_work_rejects_semantically_incomplete_knowledge_review(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            state["knowledge_review"].update(
                {
                    "disposition": "promote",
                    "rationale": "",
                    "change_fingerprint": "source-fingerprint",
                    "recorded_at": "2026-08-03T01:00:00Z",
                }
            )
            core.atomic_write_json(core.state_path(harness.repo, state["id"]), state)

            with self.assertRaises(core.ValidationError) as raised:
                core.load_state(harness.repo, state["id"])

            self.assertTrue(
                any(
                    "disposition requires rationale" in error
                    for error in raised.exception.details["errors"]
                )
            )

            state = harness.start(title="Missing knowledge base")
            state.pop("base_knowledge")
            core.atomic_write_json(core.state_path(harness.repo, state["id"]), state)
            with self.assertRaises(core.ValidationError) as missing_base:
                core.load_state(harness.repo, state["id"])
            self.assertIn(
                "knowledge_review_required needs a base_knowledge snapshot",
                missing_base.exception.details["errors"],
            )

    def test_context_records_capture_page_state_and_design_drift_invalidates_g1(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            work_id = state["id"]
            harness.fill_requirements(work_id)
            captured = core.load_state(harness.repo, work_id)["knowledge_context"]
            self.assertEqual(
                ["wiki/index.md", "wiki/overview.md"], captured["pages"]
            )
            self.assertEqual(captured["pages"], [item["path"] for item in captured["records"]])
            self.assertTrue(captured["records"][0]["present"])
            self.assertEqual("placeholder", captured["records"][1]["status"])
            self.assertTrue(captured["records"][1]["content_hash"])

            core.set_scope(harness.repo, work_id, ["src/**"], "限制產品來源範圍。")
            core.approve_gate(harness.repo, work_id, "scope", "Test Approver")
            overview = harness.repo / "wiki/overview.md"
            overview.write_text(
                overview.read_text(encoding="utf-8") + "\nExternal knowledge drift.\n",
                encoding="utf-8",
            )
            stale = core.sync_state(harness.repo, work_id)
            self.assertEqual("requirements", stale["phase"])
            self.assertEqual("stale", stale["gates"]["scope"]["status"])

    def test_no_update_review_projects_coverage_and_invalidates_on_source_change(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "knowledge review change", review=False)

            before = core.work_knowledge_status(
                harness.repo, core.load_state(harness.repo, work_id)
            )
            self.assertEqual([], before["covered_changed_paths"])
            self.assertEqual(["src/app.txt"], before["uncovered_changed_paths"])
            self.assertTrue(before["bootstrap"]["recommended"])
            self.assertFalse(before["review"]["current"])

            review = core.set_knowledge_review(
                harness.repo,
                work_id,
                "no-update",
                "此 fixture 只改變測試 marker，沒有可跨 Work Item 重用的知識。",
            )
            self.assertEqual("no-update", review["disposition"])
            self.assertEqual(["src/app.txt"], review["uncovered_changed_paths"])
            current = core.work_knowledge_status(
                harness.repo, core.load_state(harness.repo, work_id)
            )
            self.assertTrue(current["review"]["current"])

            (harness.repo / "src/app.txt").write_text(
                "changed after knowledge review\n", encoding="utf-8"
            )
            invalidated = core.sync_state(harness.repo, work_id)
            self.assertIsNotNone(invalidated["knowledge_review"]["invalidated_at"])
            self.assertIsNone(
                invalidated["knowledge_updates"]["change_fingerprint"]
            )
            status = core.work_knowledge_status(harness.repo, invalidated)
            self.assertFalse(status["review"]["current"])

    def test_promote_review_is_required_for_a_current_five_page_plan(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "promotion candidate", review=False)
            with self.assertRaises(core.ValidationError):
                core.set_knowledge_plan(
                    harness.repo,
                    work_id,
                    ["wiki/modules/one.md"],
                    [],
                    "Plan before review must fail.",
                )

            review = core.set_knowledge_review(
                harness.repo,
                work_id,
                "promote",
                "變更形成可重用的 module knowledge。",
            )
            five = [f"wiki/modules/page-{number}.md" for number in range(1, 6)]
            updates = core.set_knowledge_plan(
                harness.repo,
                work_id,
                five,
                [],
                "建立最多五個 source-bound module pages。",
            )
            self.assertEqual(five, updates["upserts"])
            self.assertEqual(
                review["change_fingerprint"], updates["change_fingerprint"]
            )
            with self.assertRaises(core.ValidationError) as too_many:
                core.set_knowledge_plan(
                    harness.repo,
                    work_id,
                    five + ["wiki/modules/page-6.md"],
                    [],
                    "第六頁應被拒絕。",
                )
            self.assertIn("five", too_many.exception.message.lower())

    def test_acceptance_requires_current_review_and_no_update_has_no_wiki_diff(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "no durable knowledge", review=False)
            current = core.load_state(harness.repo, work_id)
            changed = core.changed_paths_since(harness.repo, current["base_source"])
            errors: list[str] = []
            core._validate_knowledge_acceptance(
                harness.repo, current, changed, errors, []
            )
            self.assertTrue(any("knowledge review" in item.lower() for item in errors))

            with self.assertRaises(core.ValidationError):
                core.set_knowledge_review(
                    harness.repo,
                    work_id,
                    "no-update",
                    "",
                )
            index = harness.repo / "wiki/index.md"
            original_index = index.read_bytes()
            index.write_bytes(original_index + b"\nUndeclared Wiki diff.\n")
            with self.assertRaises(core.ValidationError) as wiki_diff:
                core.set_knowledge_review(
                    harness.repo,
                    work_id,
                    "no-update",
                    "Wiki 已有變更時不得宣告 no-update。",
                )
            self.assertIn("not allowed", wiki_diff.exception.message.lower())
            index.write_bytes(original_index)

            core.set_knowledge_review(
                harness.repo,
                work_id,
                "no-update",
                "沒有跨工作項可重用的知識。",
            )
            current = core.load_state(harness.repo, work_id)
            errors = []
            core._validate_knowledge_acceptance(
                harness.repo, current, changed, errors, []
            )
            self.assertEqual([], errors)

            overview = harness.repo / "wiki/overview.md"
            overview.write_text(
                overview.read_text(encoding="utf-8") + "\nUnexpected Wiki diff.\n",
                encoding="utf-8",
            )
            errors = []
            core._validate_knowledge_acceptance(
                harness.repo,
                core.load_state(harness.repo, work_id),
                changed,
                errors,
                [],
            )
            self.assertTrue(any("no-update" in item.lower() for item in errors))

    def test_requirements_change_invalidates_all_gates(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            path = harness.work_file(work_id, "requirements.md")
            path.write_text(path.read_text(encoding="utf-8") + "\n範圍決策已變更。\n", encoding="utf-8")

            updated = core.sync_state(harness.repo, work_id)

            self.assertEqual("requirements", updated["phase"])
            self.assertEqual("stale", updated["gates"]["scope"]["status"])
            self.assertNotEqual("approved", updated["gates"]["build"]["status"])
            self.assertNotEqual("approved", updated["gates"]["acceptance"]["status"])

    def test_design_or_plan_change_invalidates_g2_and_g3_only(self) -> None:
        for artifact in ("design.md", "plan.md"):
            with self.subTest(artifact=artifact), RepositoryHarness() as harness:
                state = harness.prepare_g2()
                work_id = state["id"]
                path = harness.work_file(work_id, artifact)
                path.write_text(path.read_text(encoding="utf-8") + "\n已調整。\n", encoding="utf-8")

                updated = core.sync_state(harness.repo, work_id)

                self.assertEqual("approved", updated["gates"]["scope"]["status"])
                self.assertEqual("stale", updated["gates"]["build"]["status"])
                self.assertEqual("design", updated["phase"])

    def test_source_change_stales_g3_and_source_bound_evidence(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "first implementation")
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
                summary="回歸通過。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            core.set_baseline_updates(harness.repo, work_id, [], "基線不需更新。")
            harness.fill_acceptance(work_id, [first["id"], second["id"]])
            core.approve_gate(harness.repo, work_id, "acceptance", "Test Approver")

            (harness.repo / "src" / "app.txt").write_text(
                "changed after verification\n", encoding="utf-8"
            )
            updated = core.sync_state(harness.repo, work_id)

            self.assertEqual("verification", updated["phase"])
            self.assertEqual("stale", updated["gates"]["acceptance"]["status"])
            self.assertIsNone(updated["last_verification"])
            self.assertTrue(updated["evidence"][first["id"]]["stale"])
            self.assertTrue(updated["evidence"][second["id"]]["stale"])

    def test_acceptance_artifact_change_invalidates_only_g3(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "accepted implementation")
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
                summary="回歸通過。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            core.set_baseline_updates(harness.repo, work_id, [], "基線不需更新。")
            harness.fill_acceptance(work_id, [first["id"], second["id"]])
            core.approve_gate(harness.repo, work_id, "acceptance", "Test Approver")
            acceptance = harness.work_file(work_id, "acceptance.md")
            acceptance.write_text(
                acceptance.read_text(encoding="utf-8") + "\n驗收決策補充。\n",
                encoding="utf-8",
            )

            updated = core.sync_state(harness.repo, work_id)

            self.assertEqual("approved", updated["gates"]["scope"]["status"])
            self.assertEqual("approved", updated["gates"]["build"]["status"])
            self.assertEqual("stale", updated["gates"]["acceptance"]["status"])

    def test_framework_artifacts_do_not_change_source_fingerprint(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            before = core.git_snapshot(harness.repo)["fingerprint"]
            harness.work_file(state["id"], "brief.md").write_text(
                "framework-only change\n", encoding="utf-8"
            )
            after = core.git_snapshot(harness.repo)["fingerprint"]
            self.assertEqual(before, after)

    def test_changed_paths_excludes_preexisting_dirty_files(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            (harness.repo / "README.md").write_text("preexisting dirty\n", encoding="utf-8")
            base = core.git_snapshot(harness.repo)
            self.assertIn("README.md", base["dirty_paths"])
            self.assertEqual([], core.changed_paths_since(harness.repo, base))
            (harness.repo / "src" / "app.txt").write_text("new change\n", encoding="utf-8")
            self.assertEqual(["src/app.txt"], core.changed_paths_since(harness.repo, base))

    def test_source_fingerprint_is_branch_aware_but_staging_stable(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            (harness.repo / "src" / "app.txt").write_text("working change\n", encoding="utf-8")
            unstaged = core.git_snapshot(harness.repo)
            run_git(harness.repo, "add", "src/app.txt")
            staged = core.git_snapshot(harness.repo)
            self.assertEqual(unstaged["fingerprint"], staged["fingerprint"])
            run_git(harness.repo, "switch", "-c", "alternate-fixture")
            alternate = core.git_snapshot(harness.repo)
            self.assertEqual(staged["head"], alternate["head"])
            self.assertNotEqual(staged["fingerprint"], alternate["fingerprint"])


class ValidationAndPersistenceTests(unittest.TestCase):
    def test_illegal_transitions_are_rejected(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            with self.assertRaises(core.ValidationError):
                core.approve_gate(harness.repo, state["id"], "scope")
            with self.assertRaises(core.ValidationError):
                core.update_task(harness.repo, state["id"], "TASK-001", "start")
            with self.assertRaises(core.ValidationError):
                core.close_work(harness.repo, state["id"])

    def test_gate_approval_must_match_current_phase(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            work_id = state["id"]
            harness.fill_requirements(work_id)
            core.set_scope(harness.repo, work_id, ["src/**"], "限制實作範圍。")
            core.approve_gate(harness.repo, work_id, "scope", "Test Approver")
            with self.assertRaises(core.ValidationError):
                core.approve_gate(harness.repo, work_id, "scope", "Test Approver")
            with self.assertRaises(core.ValidationError):
                core.approve_gate(harness.repo, work_id, "acceptance", "Test Approver")

    def test_completed_task_is_terminal_until_plan_revision(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            core.update_task(harness.repo, work_id, "TASK-001", "start")
            core.update_task(
                harness.repo,
                work_id,
                "TASK-001",
                "complete",
                note="完成。",
            )
            for action in ("start", "complete", "block"):
                with self.subTest(action=action), self.assertRaises(core.ValidationError):
                    core.update_task(
                        harness.repo,
                        work_id,
                        "TASK-001",
                        action,
                        note="不允許的轉移。",
                    )

    def test_risk_downgrade_requires_reason(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start(risk="high")
            with self.assertRaises(core.ValidationError):
                core.set_risk(harness.repo, state["id"], "standard", "風險已降低。")
            updated = core.set_risk(
                harness.repo,
                state["id"],
                "standard",
                "風險已降低。",
                "已移除資料 migration 與公開介面變更。",
            )
            self.assertTrue(updated["risk"]["downgrade_rationale"])

    def test_high_risk_requires_current_review_evidence(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2(risk="high")
            work_id = state["id"]
            harness.implement(work_id, "high-risk implementation")
            harness.configure_command(required_for=("high",))
            evidence = [
                core.run_verification(
                    harness.repo,
                    work_id,
                    command_id="fixture-tests",
                    kind="acceptance",
                    covers=["AC-001", "AC-002"],
                    tasks=["TASK-001"],
                )
            ]
            evidence.append(
                core.add_evidence(
                    harness.repo,
                    work_id,
                    kind="regression",
                    status="passed",
                    summary="高風險回歸通過。",
                    covers=["AC-001", "AC-002"],
                    tasks=["TASK-001"],
                )
            )
            core.set_baseline_updates(harness.repo, work_id, [], "基線不需更新。")
            harness.fill_acceptance(work_id, [item["id"] for item in evidence])
            report = core.validate_work(
                harness.repo, core.load_state(harness.repo, work_id), "acceptance"
            )
            self.assertTrue(any("review" in error for error in report.errors))

            review = core.add_evidence(
                harness.repo,
                work_id,
                kind="review",
                status="passed",
                summary="獨立 reviewer 已確認 migration、rollback、安全、相容與效能分析。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            harness.fill_acceptance(work_id, [item["id"] for item in evidence] + [review["id"]])
            report = core.validate_work(
                harness.repo, core.load_state(harness.repo, work_id), "acceptance"
            )
            self.assertTrue(report.ok, report.errors)

    def test_new_work_requires_architecture_baseline_update(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2(kind="new")
            work_id = state["id"]
            harness.implement(work_id, "vertical slice")
            harness.configure_command()
            evidence = core.run_verification(
                harness.repo,
                work_id,
                command_id="fixture-tests",
                kind="acceptance",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            core.set_baseline_updates(harness.repo, work_id, [], "暫不更新基線。")
            harness.fill_acceptance(work_id, [evidence["id"]])
            report = core.validate_work(
                harness.repo, core.load_state(harness.repo, work_id), "acceptance"
            )
            self.assertTrue(any("architecture.md" in error for error in report.errors))

    def test_task_dependencies_control_start_order(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            work_id = state["id"]
            harness.fill_requirements(work_id)
            core.set_scope(harness.repo, work_id, ["src/**"], "限制實作範圍。")
            core.approve_gate(harness.repo, work_id, "scope", "Test Approver")
            harness.fill_design(work_id)
            plan_path = harness.work_file(work_id, "plan.md")
            plan = plan_path.read_text(encoding="utf-8")
            second_task = """
## TASK-002: 整合第二步驟
- Traces: REQ-001, NFR-001, AC-001, AC-002, DEC-001
- Inputs: TASK-001 的輸出。
- Output: 完成整合。
- Verification: targeted verification。
- Dependencies: TASK-001

"""
            plan_path.write_text(
                plan.replace("## 驗證策略", second_task + "## 驗證策略"),
                encoding="utf-8",
            )
            core.approve_gate(harness.repo, work_id, "build", "Test Approver")
            with self.assertRaises(core.ValidationError):
                core.update_task(harness.repo, work_id, "TASK-002", "start")
            core.update_task(harness.repo, work_id, "TASK-001", "start")
            core.update_task(
                harness.repo,
                work_id,
                "TASK-001",
                "complete",
                note="第一步完成。",
            )
            started = core.update_task(harness.repo, work_id, "TASK-002", "start")
            self.assertEqual("in_progress", started["status"])

    def test_duplicate_and_undefined_trace_ids_fail_validation(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            work_id = state["id"]
            harness.fill_requirements(work_id)
            requirements = harness.work_file(work_id, "requirements.md")
            text = requirements.read_text(encoding="utf-8")
            text = text.replace("Acceptance: AC-001", "Acceptance: AC-999", 1)
            text = text.replace("## AC-002:", "## AC-001:")
            requirements.write_text(text, encoding="utf-8")
            core.set_scope(harness.repo, work_id, ["src/**"], "限制實作範圍。")
            report = core.validate_work(
                harness.repo, core.load_state(harness.repo, work_id), "scope"
            )
            self.assertTrue(any("duplicate IDs" in error for error in report.errors))
            self.assertTrue(any("undefined acceptance" in error for error in report.errors))

    def test_revision_returns_to_earliest_affected_phase(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            design_revision = core.revise_work(
                harness.repo, work_id, "design", "改變介面設計。"
            )
            self.assertEqual("design", design_revision["phase"])
            self.assertEqual("approved", design_revision["gates"]["scope"]["status"])
            self.assertEqual("stale", design_revision["gates"]["build"]["status"])

            requirements_revision = core.revise_work(
                harness.repo, work_id, "requirements", "改變需求範圍。"
            )
            self.assertEqual("requirements", requirements_revision["phase"])
            self.assertEqual("stale", requirements_revision["gates"]["scope"]["status"])

    def test_bug_requires_red_evidence_or_narrow_waiver(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start("bug")
            work_id = state["id"]
            harness.fill_requirements(work_id)
            core.set_scope(harness.repo, work_id, ["src/**"], "限制修正範圍。")
            report = core.validate_work(harness.repo, core.load_state(harness.repo, work_id), "scope")
            self.assertTrue(any("reproduction" in error for error in report.errors))
            core.add_waiver(
                harness.repo,
                work_id,
                kind="unreproducible",
                target="reported-environment",
                reason="原始外部服務已下線，保留現有 failure log 並以鄰近回歸替代。",
                actor="Test Approver",
            )
            report = core.validate_work(harness.repo, core.load_state(harness.repo, work_id), "scope")
            self.assertTrue(report.ok, report.errors)

    def test_missing_command_blocks_until_acceptance_waiver(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "manual-only verification")
            project = core.load_project(harness.repo)
            project["verification_profiles"]["standard"] = ["missing-suite"]
            core.atomic_write_json(core.project_path(harness.repo), project)
            first = core.add_evidence(
                harness.repo,
                work_id,
                kind="acceptance",
                status="passed",
                summary="人工驗收通過。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            second = core.add_evidence(
                harness.repo,
                work_id,
                kind="regression",
                status="passed",
                summary="人工回歸通過。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            core.set_baseline_updates(harness.repo, work_id, [], "基線不需更新。")
            harness.fill_acceptance(work_id, [first["id"], second["id"]])
            report = core.validate_work(harness.repo, core.load_state(harness.repo, work_id), "acceptance")
            self.assertTrue(any("undefined" in error for error in report.errors))
            core.add_waiver(
                harness.repo,
                work_id,
                kind="missing-command",
                target="missing-suite",
                reason="fixture 無該平台 runner；已執行同範圍人工驗證。",
                actor="Test Approver",
            )
            report = core.validate_work(harness.repo, core.load_state(harness.repo, work_id), "acceptance")
            self.assertTrue(report.ok, report.errors)

    def test_out_of_scope_change_is_blocked(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "in scope")
            (harness.repo / "README.md").write_text("out of scope\n", encoding="utf-8")
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
                summary="回歸通過。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            core.set_baseline_updates(harness.repo, work_id, [], "基線不需更新。")
            harness.fill_acceptance(work_id, [first["id"], second["id"]])
            report = core.validate_work(harness.repo, core.load_state(harness.repo, work_id), "acceptance")
            self.assertTrue(any("README.md" in error for error in report.errors))

    def test_undeclared_living_baseline_change_is_blocked(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "baseline-sensitive change")
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
                summary="回歸通過。",
                covers=["AC-001", "AC-002"],
                tasks=["TASK-001"],
            )
            architecture = harness.repo / ".devweave" / "baseline" / "architecture.md"
            architecture.write_text("# 未宣告的基線變更\n", encoding="utf-8")
            core.set_baseline_updates(harness.repo, work_id, [], "宣稱不需更新。")
            harness.fill_acceptance(work_id, [first["id"], second["id"]])
            report = core.validate_work(
                harness.repo, core.load_state(harness.repo, work_id), "acceptance"
            )
            self.assertTrue(
                any("not declared" in error for error in report.errors), report.errors
            )

    def test_work_lock_times_out_and_atomic_write_leaves_no_temp_file(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            with core.WorkLock(harness.repo, "locked"):
                with self.assertRaises(core.ExecutionError):
                    with core.WorkLock(harness.repo, "locked", timeout_seconds=0.05):
                        pass
            target = harness.repo / ".devweave" / "atomic.json"
            core.atomic_write_json(target, {"value": "完整"})
            self.assertEqual("完整", core.read_json(target)["value"])
            self.assertEqual([], list(target.parent.glob(f".{target.name}.*.tmp")))

    def test_malformed_models_return_validation_diagnostics(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            state["phase"] = "invented-phase"
            core.atomic_write_json(core.state_path(harness.repo, state["id"]), state)
            with self.assertRaises(core.ValidationError) as invalid_state:
                core.load_state(harness.repo, state["id"])
            self.assertIn("phase is invalid", invalid_state.exception.details["errors"])

        with RepositoryHarness() as harness:
            harness.init()
            project = core.read_json(core.project_path(harness.repo))
            project["commands"] = [{"id": "bad", "argv": "shell string"}]
            project["knowledge"]["root"] = "docs/wiki"
            core.atomic_write_json(core.project_path(harness.repo), project)
            with self.assertRaises(core.ValidationError) as invalid_project:
                core.load_project(harness.repo)
            self.assertTrue(invalid_project.exception.details["errors"])
            self.assertIn(
                "knowledge.root must be wiki",
                invalid_project.exception.details["errors"],
            )

    def test_multiple_items_require_selection_and_closed_item_cannot_reopen(self) -> None:
        with RepositoryHarness() as harness:
            first = harness.start(title="First")
            second = core.create_work(
                harness.repo,
                kind="feature",
                title="Second",
                risk_rationale="標準風險。",
            )
            with self.assertRaises(core.SelectionError) as ambiguity:
                core.resolve_work(harness.repo, None)
            self.assertEqual(2, len(ambiguity.exception.details["candidates"]))
            self.assertNotEqual(first["id"], second["id"])
            state = core.load_state(harness.repo, first["id"])
            state["status"] = "closed"
            state["phase"] = "closed"
            core.atomic_write_json(core.state_path(harness.repo, first["id"]), state)
            with self.assertRaises(core.ValidationError):
                core.revise_work(harness.repo, first["id"], "requirements", "重新開啟")

    def test_timeout_and_log_truncation_are_recorded(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            work_id = state["id"]
            harness.configure_command(
                "slow",
                argv=[sys.executable, "-c", "import time; time.sleep(2)"],
                timeout_seconds=1,
                required_for=(),
            )
            timed_out = core.run_verification(
                harness.repo, work_id, command_id="slow", kind="diagnostic"
            )
            self.assertEqual("failed", timed_out["status"])
            self.assertTrue(timed_out["timed_out"])

            harness.configure_command(
                "large",
                argv=[sys.executable, "-c", "print('x' * 2000); print('token=secret-value')"],
                required_for=(),
            )
            project = core.load_project(harness.repo)
            project["evidence"]["raw_log_limit_bytes"] = 128
            core.atomic_write_json(core.project_path(harness.repo), project)
            large = core.run_verification(
                harness.repo, work_id, command_id="large", kind="diagnostic"
            )
            self.assertTrue(large["log_truncated"])
            self.assertNotIn("secret-value", large["summary"])
            log = harness.repo / Path(large["raw_log"])
            self.assertLessEqual(log.stat().st_size, 128)

    def test_missing_executable_is_failed_evidence_not_an_internal_crash(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "missing-executable",
                argv=["devweave-command-that-does-not-exist-7f58"],
                required_for=(),
            )
            evidence = core.run_verification(
                harness.repo,
                state["id"],
                command_id="missing-executable",
                kind="diagnostic",
            )
            self.assertEqual("failed", evidence["status"])
            self.assertEqual("failure", evidence["observed_result"])
            self.assertIn("FileNotFoundError", evidence["execution_error"])


if __name__ == "__main__":
    unittest.main()

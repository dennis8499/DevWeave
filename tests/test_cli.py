from __future__ import annotations

import json
import subprocess
import sys
import unittest

from devweave_test_support import REPOSITORY_ROOT, RepositoryHarness, core


CLI = REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "scripts" / "devweave.py"


def invoke(repo, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run(
        [sys.executable, "-B", str(CLI), "--repo", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result, json.loads(result.stdout)


class CliContractTests(unittest.TestCase):
    def test_usage_errors_are_json_with_exit_code_two(self) -> None:
        with RepositoryHarness() as harness:
            result, payload = invoke(harness.repo, "start", "--kind", "feature")
            self.assertEqual(2, result.returncode)
            self.assertEqual("usage_error", payload["error"]["code"])
            self.assertEqual("", result.stderr)

    def test_json_first_status_and_validation_exit_codes(self) -> None:
        with RepositoryHarness() as harness:
            result, payload = invoke(harness.repo, "status", "--all")
            self.assertEqual(0, result.returncode)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["initialized"])

            result, payload = invoke(harness.repo, "init")
            self.assertEqual(0, result.returncode)
            result, payload = invoke(harness.repo, "status")
            self.assertEqual(0, result.returncode)
            self.assertEqual([], payload["work_items"])

            result, payload = invoke(
                harness.repo,
                "start",
                "--kind",
                "feature",
                "--title",
                "CLI fixture",
                "--rationale",
                "標準風險。",
            )
            self.assertEqual(0, result.returncode)
            work_id = payload["work"]["id"]

            result, payload = invoke(
                harness.repo, "validate", "--work", work_id, "--gate", "scope"
            )
            self.assertEqual(2, result.returncode)
            self.assertFalse(payload["ok"])
            self.assertEqual("scope", payload["validation"]["gate"])

    def test_bind_without_hook_confirmation_is_not_reported_as_bound(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            result, payload = invoke(
                harness.repo, "bind", "--work", state["id"]
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("awaiting_hook", payload["binding"]["status"])
            self.assertTrue(payload["guard_confirmation_required"])
            self.assertIsNone(payload["binding"]["session_id"])

    def test_ambiguous_selection_uses_exit_code_three(self) -> None:
        with RepositoryHarness() as harness:
            harness.start(title="First")
            core.create_work(
                harness.repo,
                kind="bug",
                title="Second",
                risk_rationale="標準風險。",
            )
            result, payload = invoke(harness.repo, "status")
            self.assertEqual(3, result.returncode)
            self.assertEqual("selection_required", payload["error"]["code"])
            self.assertEqual(2, len(payload["error"]["details"]["candidates"]))

    def test_work_id_cannot_escape_work_item_directory(self) -> None:
        with RepositoryHarness() as harness:
            harness.start()
            result, payload = invoke(
                harness.repo, "status", "--work", "../../outside"
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("validation_failed", payload["error"]["code"])

    def test_verify_failure_uses_exit_code_four(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "fails",
                argv=[sys.executable, "-c", "raise SystemExit(7)"],
                required_for=(),
            )
            result, payload = invoke(
                harness.repo,
                "verify",
                "--work",
                state["id"],
                "--command",
                "fails",
                "--kind",
                "diagnostic",
            )
            self.assertEqual(4, result.returncode)
            self.assertFalse(payload["ok"])
            self.assertEqual(7, payload["evidence"]["exit_code"])

    def test_verify_records_selection_and_unavailable_usage_metrics(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "metrics-command",
                argv=[sys.executable, "-c", "print('metrics')"],
                required_for=(),
            )
            result, payload = invoke(
                harness.repo,
                "verify",
                "--work",
                state["id"],
                "--command",
                "metrics-command",
                "--kind",
                "diagnostic",
                "--metrics-json",
                json.dumps({"usage": {"status": "unavailable"}}),
            )
            self.assertEqual(0, result.returncode, result)
            metrics = payload["evidence"]["metrics"]
            self.assertEqual("unavailable", metrics["usage"]["status"])
            self.assertIsNone(metrics["usage"]["input_tokens"])
            self.assertEqual(1, metrics["verification"]["selected"])
            self.assertGreaterEqual(metrics["duration_ms"], 0)

    def test_verify_rejects_malformed_metrics_json_as_validation_error(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "metrics-invalid",
                argv=[sys.executable, "-c", "print('never')"],
                required_for=(),
            )
            result, payload = invoke(
                harness.repo,
                "verify",
                "--work",
                state["id"],
                "--command",
                "metrics-invalid",
                "--kind",
                "diagnostic",
                "--metrics-json",
                "{",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("validation_failed", payload["error"]["code"])
            self.assertNotIn("JSONDecodeError", result.stdout)

    def test_verify_profile_batches_independent_commands_and_respects_dependencies(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "profile-first",
                argv=[sys.executable, "-c", "print('first')"],
                required_for=("standard",),
            )
            harness.configure_command(
                "profile-independent",
                argv=[sys.executable, "-c", "print('independent')"],
                required_for=("standard",),
            )
            harness.configure_command(
                "profile-dependent",
                argv=[sys.executable, "-c", "print('dependent')"],
                required_for=("standard",),
                depends_on=("profile-first",),
            )
            result, payload = invoke(
                harness.repo,
                "verify",
                "--work",
                state["id"],
                "--profile",
                "standard",
                "--max-parallel",
                "2",
                "--kind",
                "regression",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(payload["ok"])
            batch = payload["batch"]
            self.assertTrue(batch["id"].startswith("VB-"))
            records = {item["command_id"]: item for item in batch["commands"]}
            self.assertEqual("passed", records["profile-first"]["status"])
            self.assertEqual("passed", records["profile-independent"]["status"])
            self.assertEqual("passed", records["profile-dependent"]["status"])
            self.assertEqual(3, len(core.load_state(harness.repo, state["id"])["evidence"]))
            for record in records.values():
                evidence = record["evidence"]
                self.assertEqual(batch["id"], evidence["verification_batch_id"])

    def test_command_set_rejects_unknown_dependency_without_writing_invalid_project(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            result, payload = invoke(
                harness.repo,
                "command",
                "set",
                "--id",
                "dependent",
                "--depends-on",
                "missing",
                "--required-for",
                "standard",
                "--",
                sys.executable,
                "-c",
                "print('never configured')",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("validation_failed", payload["error"]["code"])
            self.assertEqual([], core.load_project(harness.repo)["commands"])

    def test_command_set_records_and_validates_optional_metadata(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            result, payload = invoke(
                harness.repo,
                "command",
                "set",
                "--id",
                "metadata-command",
                "--required-for",
                "standard",
                "--affected-path",
                "src",
                "--writes",
                "generated",
                "--output",
                "dist",
                "--release-only",
                "--",
                sys.executable,
                "-c",
                "print('metadata')",
            )
            self.assertEqual(0, result.returncode, payload)
            command = payload["command"]
            self.assertEqual(["src"], command["affected_paths"])
            self.assertEqual("generated", command["writes"])
            self.assertEqual(["dist"], command["outputs"])
            self.assertTrue(command["release_only"])

            result, payload = invoke(
                harness.repo,
                "command",
                "set",
                "--id",
                "bad-metadata",
                "--affected-path",
                "../outside",
                "--",
                sys.executable,
                "-c",
                "print('never')",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("validation_failed", payload["error"]["code"])
            self.assertEqual(
                ["metadata-command"],
                [item["id"] for item in core.load_project(harness.repo)["commands"]],
            )

    def test_selective_profile_reports_skips_and_dependency_closure(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "selected",
                argv=[sys.executable, "-c", "print('selected')"],
                required_for=("standard",),
                affected_paths=("src",),
            )
            harness.configure_command(
                "dependency",
                argv=[sys.executable, "-c", "print('dependency')"],
                required_for=(),
                affected_paths=("docs",),
            )
            project = core.load_project(harness.repo)
            selected = next(item for item in project["commands"] if item["id"] == "selected")
            selected["depends_on"] = ["dependency"]
            project["verification_profiles"]["standard"] = ["selected"]
            core.atomic_write_json(core.project_path(harness.repo), project)
            result, payload = invoke(
                harness.repo,
                "verify",
                "--work",
                state["id"],
                "--profile",
                "standard",
                "--path",
                "src/app.txt",
                "--kind",
                "regression",
            )
            self.assertEqual(0, result.returncode, result)
            selection = payload["batch"]["selection"]
            self.assertEqual("affected-paths", selection["mode"])
            self.assertEqual(["dependency"], selection["dependency_closure_added"])
            self.assertEqual(["dependency", "selected"], selection["selected"])
            self.assertEqual([], selection["skipped"])

    def test_non_high_profile_does_not_resurrect_release_only_dependency(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "release-package",
                argv=[sys.executable, "-c", "print('package')"],
                required_for=("standard",),
                affected_paths=("src",),
                release_only=True,
            )
            harness.configure_command(
                "release-smoke",
                argv=[sys.executable, "-c", "print('smoke')"],
                required_for=("standard",),
                depends_on=("release-package",),
                affected_paths=("src",),
            )
            result, payload = invoke(
                harness.repo,
                "verify",
                "--work",
                state["id"],
                "--profile",
                "standard",
                "--path",
                "src/app.txt",
                "--kind",
                "regression",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            selection = payload["batch"]["selection"]
            self.assertEqual([], selection["selected"])
            self.assertEqual(
                {"release-package", "release-smoke"},
                {item["command_id"] for item in selection["skipped"]},
            )
            self.assertIn(
                "release-only-dependency:release-package",
                {item["reason"] for item in selection["skipped"]},
            )

    def test_high_profile_ignores_path_filter_and_legacy_commands_are_explicitly_skipped(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            harness.configure_command(
                "legacy-high",
                argv=[sys.executable, "-c", "print('legacy')"],
                required_for=("high",),
            )
            result, payload = invoke(
                harness.repo,
                "verify",
                "--work",
                state["id"],
                "--profile",
                "high",
                "--path",
                "unrelated.txt",
                "--kind",
                "regression",
            )
            self.assertEqual(0, result.returncode, result)
            self.assertTrue(payload["batch"]["selection"]["high_profile_full_set"])
            self.assertEqual([], payload["batch"]["selection"]["skipped"])

    def test_machine_only_review_record_cli_writes_review_evidence(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2(risk="high")
            work_id = state["id"]
            harness.implement(work_id, "CLI review change")
            incoming = harness.repo / ".devweave" / "cache" / "incoming" / work_id
            incoming.mkdir(parents=True, exist_ok=True)
            report = incoming / "review.json"
            report.write_text(
                json.dumps(
                    {
                        "result": "passed",
                        "severity": "none",
                        "summary": "CLI independent review passed.",
                        "source_fingerprint": core.git_snapshot(harness.repo)["fingerprint"],
                        "covers": ["AC-001", "AC-002"],
                        "tasks": ["TASK-001"],
                        "findings": [],
                    }
                ),
                encoding="utf-8",
            )
            result, payload = invoke(
                harness.repo,
                "review",
                "record",
                "--work",
                work_id,
                "--reviewer-id",
                "opaque-cli-reviewer",
                "--report-file",
                report.relative_to(harness.repo).as_posix(),
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertTrue(payload["ok"])
            self.assertEqual("review", payload["evidence"]["kind"])
            self.assertEqual("passed", payload["evidence"]["review"]["result"])

    def test_command_set_preserves_argv_array(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            result, payload = invoke(
                harness.repo,
                "command",
                "set",
                "--id",
                "unit",
                "--cwd",
                ".",
                "--timeout",
                "20",
                "--required-for",
                "standard",
                "--",
                sys.executable,
                "-c",
                "print('ok')",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual([sys.executable, "-c", "print('ok')"], payload["command"]["argv"])
            self.assertIn("unit", payload["profiles"]["standard"])

    def test_command_set_rejects_invalid_timeout(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            result, payload = invoke(
                harness.repo,
                "command",
                "set",
                "--id",
                "invalid",
                "--timeout",
                "0",
                "--",
                sys.executable,
                "-c",
                "print('never configured')",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("validation_failed", payload["error"]["code"])

    def test_knowledge_machine_cli_reports_and_replaces_g1_context(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            work_id = state["id"]
            result, payload = invoke(
                harness.repo, "knowledge", "status", "--work", work_id
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("warning", payload["knowledge"]["health"])
            self.assertIn("wiki/overview.md", payload["knowledge"]["placeholder_pages"])

            result, payload = invoke(
                harness.repo,
                "knowledge",
                "context",
                "--work",
                work_id,
                "--page",
                "wiki/index.md",
                "--page",
                "wiki/overview.md",
                "--gap",
                "overview placeholder required raw-source fallback",
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual(
                ["wiki/index.md", "wiki/overview.md"],
                payload["knowledge_context"]["pages"],
            )
            result, payload = invoke(
                harness.repo,
                "knowledge",
                "context",
                "--work",
                work_id,
                "--page",
                "wiki/index.md",
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual(["wiki/index.md"], payload["knowledge_context"]["pages"])

    def test_knowledge_bootstrap_cli_creates_then_resumes_one_work_item(self) -> None:
        with RepositoryHarness() as harness:
            result, payload = invoke(harness.repo, "knowledge", "bootstrap")
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual("created", payload["action"])
            self.assertEqual("bootstrap", payload["work"]["knowledge_profile"])
            work_id = payload["work"]["id"]

            result, payload = invoke(harness.repo, "knowledge", "bootstrap")
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual("resume", payload["action"])
            self.assertEqual(work_id, payload["work"]["id"])

            result, payload = invoke(
                harness.repo, "knowledge", "bootstrap", "--scope", "src"
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("usage_error", payload["error"]["code"])

    def test_knowledge_review_and_scaffold_cli_are_phase_and_plan_bound(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "durable module behavior", review=False)

            result, payload = invoke(
                harness.repo, "instructions", "--work", work_id
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual(
                "record_knowledge_review", payload["instructions"]["next_action"]
            )

            result, payload = invoke(
                harness.repo,
                "knowledge",
                "review",
                "--work",
                work_id,
                "--disposition",
                "promote",
                "--rationale",
                "此變更形成可跨工作項重用的 module knowledge。",
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual("promote", payload["knowledge_review"]["disposition"])
            result, payload = invoke(
                harness.repo, "instructions", "--work", work_id
            )
            self.assertEqual("plan_knowledge_updates", payload["instructions"]["next_action"])

            page = "wiki/modules/runtime.md"
            result, payload = invoke(
                harness.repo,
                "knowledge",
                "scaffold",
                "--work",
                work_id,
                "--page",
                page,
                "--type",
                "module",
                "--title",
                "Runtime Module",
                "--source",
                "src/app.txt",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("validation_failed", payload["error"]["code"])

            result, payload = invoke(
                harness.repo,
                "knowledge",
                "plan",
                "--work",
                work_id,
                "--upsert",
                page,
                "--rationale",
                "建立新的 runtime module 頁。",
            )
            self.assertEqual(0, result.returncode, payload)
            result, payload = invoke(
                harness.repo,
                "knowledge",
                "scaffold",
                "--work",
                work_id,
                "--page",
                page,
                "--type",
                "module",
                "--title",
                "Runtime Module",
                "--source",
                "src/app.txt",
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual("placeholder", payload["scaffold"]["status"])
            self.assertTrue((harness.repo / page).is_file())
            result, payload = invoke(
                harness.repo, "instructions", "--work", work_id
            )
            self.assertEqual(
                "promote_and_seal_knowledge", payload["instructions"]["next_action"]
            )

            result, payload = invoke(
                harness.repo,
                "knowledge",
                "scaffold",
                "--work",
                work_id,
                "--page",
                page,
                "--type",
                "module",
                "--title",
                "Runtime Module",
                "--source",
                "src/app.txt",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("validation_failed", payload["error"]["code"])

            result, payload = invoke(
                harness.repo,
                "knowledge",
                "seal",
                "--work",
                work_id,
                "--page",
                page,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("active", payload["error"]["message"].lower())

    def test_knowledge_no_update_review_cli_records_rationale_without_plan(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "local-only behavior", review=False)
            result, payload = invoke(
                harness.repo,
                "knowledge",
                "review",
                "--work",
                work_id,
                "--disposition",
                "no-update",
                "--rationale",
                "沒有可跨工作項重用的 durable knowledge。",
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual("no-update", payload["knowledge_review"]["disposition"])
            self.assertEqual([], payload["knowledge"]["planned"]["upserts"])
            self.assertTrue(payload["knowledge"]["review"]["current"])

    def test_knowledge_plan_and_seal_cli_use_coupled_targets(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            work_id = state["id"]
            harness.implement(work_id, "verification", review=False)
            result, payload = invoke(
                harness.repo,
                "knowledge",
                "review",
                "--work",
                work_id,
                "--disposition",
                "promote",
                "--rationale",
                "CLI fixture 將 overview 提升為 durable knowledge。",
            )
            self.assertEqual(0, result.returncode, payload)
            result, payload = invoke(
                harness.repo,
                "knowledge",
                "plan",
                "--work",
                work_id,
                "--upsert",
                "wiki/overview.md",
                "--rationale",
                "CLI promotion fixture",
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual(
                ["wiki/index.md", "wiki/log.md"],
                payload["knowledge_updates"]["coupled"],
            )
            overview = harness.repo / "wiki/overview.md"
            frontmatter, _, errors = core.knowledge.parse_frontmatter_text(
                overview.read_text(encoding="utf-8")
            )
            self.assertEqual([], errors)
            frontmatter["sources"] = ["src/app.txt"]
            frontmatter["status"] = "active"
            overview.write_text(
                core.knowledge.render_frontmatter(
                    frontmatter,
                    "\n# Fixture Overview\n\nCurrent source-backed behavior.\n",
                ),
                encoding="utf-8",
            )
            result, payload = invoke(
                harness.repo,
                "knowledge",
                "seal",
                "--work",
                work_id,
                "--page",
                "wiki/overview.md",
                "--page",
                "wiki/index.md",
                "--page",
                "wiki/log.md",
            )
            self.assertEqual(0, result.returncode, payload)
            self.assertEqual(3, len(payload["pages"]))


if __name__ == "__main__":
    unittest.main()

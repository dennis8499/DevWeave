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

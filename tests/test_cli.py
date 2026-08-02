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


if __name__ == "__main__":
    unittest.main()

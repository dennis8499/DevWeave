from __future__ import annotations

import json
import time
import unittest
from pathlib import Path

from test_app_server_e2e import (
    LIVE_CLEANUP_TIMEOUT_SECONDS,
    LIVE_OPERATION_BUDGET_SECONDS,
    operation_timeout,
    protocol_diagnostic,
)


ROOT = Path(__file__).resolve().parents[1]


class LiveE2EContractTests(unittest.TestCase):
    def test_global_budget_leaves_executor_cleanup_headroom(self) -> None:
        project = json.loads((ROOT / ".devweave/project.json").read_text(encoding="utf-8"))
        command = next(
            item
            for item in project["verification_plan"]["commands"]
            if item["command_id"] == "app-server-e2e"
        )
        self.assertLess(
            LIVE_OPERATION_BUDGET_SECONDS + LIVE_CLEANUP_TIMEOUT_SECONDS,
            command["timeout_seconds"],
        )

    def test_operation_timeout_is_capped_and_expiry_fails_closed(self) -> None:
        self.assertLessEqual(operation_timeout(time.monotonic() + 1, 30), 1)
        with self.assertRaises(TimeoutError):
            operation_timeout(time.monotonic() - 1, 30)

    def test_protocol_diagnostic_is_bounded_and_redacts_secrets(self) -> None:
        secret = "sk-exampletoken123456789"
        diagnostic = protocol_diagnostic(
            [
                {
                    "method": "error",
                    "params": {
                        "error": {
                            "code": "transport",
                            "message": f"authorization={secret}",
                        },
                        "willRetry": True,
                        "prompt": "must not be copied",
                    },
                },
                {
                    "method": "item/completed",
                    "params": {
                        "item": {
                            "type": "agentMessage",
                            "text": f"authorization={secret}",
                        },
                    },
                },
            ]
        )
        self.assertLessEqual(len(diagnostic), 4_096)
        self.assertNotIn(secret, diagnostic)
        self.assertNotIn("must not be copied", diagnostic)
        parsed = json.loads(diagnostic)
        self.assertEqual("transport", parsed["errors"][0]["error_code"])
        self.assertTrue(parsed["errors"][0]["willRetry"])
        self.assertEqual("authorization=<redacted>", parsed["agent_messages"][0])


if __name__ == "__main__":
    unittest.main()

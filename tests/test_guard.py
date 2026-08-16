from __future__ import annotations

import sys
import subprocess
import unittest

from devweave_test_support import RepositoryHarness, SCRIPT_ROOT, core

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
import guard


def denied(result: dict | None) -> bool:
    if not result:
        return False
    output = result.get("hookSpecificOutput", {})
    return output.get("permissionDecision") == "deny"


def patch_payload(repo, session: str, path: str, tool_name: str = "apply_patch") -> dict:
    return {
        "cwd": str(repo),
        "session_id": session,
        "tool_name": tool_name,
        "tool_input": {
            "command": f"*** Begin Patch\n*** Update File: {path}\n@@\n-old\n+new\n*** End Patch"
        },
    }


def bash_payload(repo, session: str, command: str) -> dict:
    return {
        "cwd": str(repo),
        "session_id": session,
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


class GuardTests(unittest.TestCase):
    def test_read_only_bash_short_circuits_before_repository_loading(self) -> None:
        payload = {
            "cwd": "Z:\\missing\\repository",
            "session_id": "",
            "tool_name": "Bash",
            "tool_input": {"command": "git status --short"},
        }
        self.assertIsNone(guard.handle_hook(payload))

    def test_uninitialized_repository_does_not_activate(self) -> None:
        with RepositoryHarness() as harness:
            payload = patch_payload(harness.repo, "s-unmanaged", "src/app.txt")
            self.assertIsNone(guard.handle_hook(payload, harness.repo))

    def test_managed_repository_blocks_unbound_writes(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            result = guard.handle_hook(
                patch_payload(harness.repo, "s-unbound", "src/app.txt"), harness.repo
            )
            self.assertTrue(denied(result))

    def test_devweave_name_inside_arbitrary_command_is_not_a_guard_bypass(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            payload = bash_payload(
                harness.repo,
                "s-bypass",
                "python -c devweave.py",
            )
            self.assertTrue(denied(guard.handle_hook(payload, harness.repo)))

    def test_bound_session_can_edit_artifacts_but_not_product_before_g2(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            session = "s-artifacts"
            core.bind_session(harness.repo, session, state["id"])
            artifact = harness.work_file(state["id"], "brief.md")
            artifact_result = guard.handle_hook(
                patch_payload(harness.repo, session, str(artifact)), harness.repo
            )
            product_result = guard.handle_hook(
                patch_payload(harness.repo, session, "src/app.txt"), harness.repo
            )
            wiki_result = guard.handle_hook(
                patch_payload(harness.repo, session, "wiki/overview.md"), harness.repo
            )
            self.assertIsNone(artifact_result)
            self.assertTrue(denied(product_result))
            self.assertTrue(denied(wiki_result))

    def test_g2_allows_product_write_and_stale_design_reblocks_it(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            session = "s-implementation"
            core.bind_session(harness.repo, session, state["id"])
            payload = patch_payload(harness.repo, session, "src/app.txt")
            self.assertIsNone(guard.handle_hook(payload, harness.repo))
            design = harness.work_file(state["id"], "design.md")
            design.write_text(design.read_text(encoding="utf-8") + "\n變更設計。\n", encoding="utf-8")
            self.assertTrue(denied(guard.handle_hook(payload, harness.repo)))

    def test_g2_still_blocks_known_out_of_scope_patch(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            session = "s-scope"
            core.bind_session(harness.repo, session, state["id"])
            result = guard.handle_hook(
                patch_payload(harness.repo, session, "README.md"), harness.repo
            )
            self.assertTrue(denied(result))
            outside = guard.handle_hook(
                patch_payload(harness.repo, session, "../outside.txt"), harness.repo
            )
            self.assertTrue(denied(outside))

    def test_patch_move_destination_is_also_scope_checked(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            session = "s-move"
            core.bind_session(harness.repo, session, state["id"])
            payload = {
                "cwd": str(harness.repo),
                "session_id": session,
                "tool_name": "apply_patch",
                "tool_input": {
                    "command": "*** Begin Patch\n*** Update File: src/app.txt\n*** Move to: README.md\n@@\n-old\n+new\n*** End Patch"
                },
            }
            self.assertTrue(denied(guard.handle_hook(payload, harness.repo)))

    def test_baseline_write_is_limited_to_verification(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            session = "s-baseline"
            core.bind_session(harness.repo, session, state["id"])
            payload = patch_payload(
                harness.repo, session, ".devweave/baseline/architecture.md"
            )
            self.assertTrue(denied(guard.handle_hook(payload, harness.repo)))
            harness.implement(state["id"], "done")
            self.assertIsNone(guard.handle_hook(payload, harness.repo))

    def test_read_only_is_unbound_but_configured_command_requires_binding(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            command = harness.configure_command(required_for=())
            command_text = subprocess.list2cmdline(command["argv"])
            self.assertIsNone(
                guard.handle_hook(bash_payload(harness.repo, "", "git status"), harness.repo)
            )
            self.assertTrue(
                denied(
                    guard.handle_hook(
                        bash_payload(harness.repo, "", command_text), harness.repo
                    )
                )
            )
            core.bind_session(harness.repo, "s-command", state["id"])
            self.assertTrue(
                denied(
                guard.handle_hook(
                    bash_payload(harness.repo, "s-command", command_text), harness.repo
                )
                )
            )

    def test_read_only_prefix_bypass_payloads_fail_closed_after_g2(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            session = "s-adversarial"
            core.bind_session(harness.repo, session, state["id"])
            payloads = (
                "git status & echo SHOULD_NOT_RUN",
                "git status $(echo SHOULD_NOT_RUN)",
                "git status `echo SHOULD_NOT_RUN`",
                "git diff --output=.devweave/cache/guard-probe.txt",
                "git status --unknown-helper",
                "Get-Content . & Write-Output SHOULD_NOT_RUN",
                "Get-Content . $(Write-Output SHOULD_NOT_RUN)",
                "Get-ChildItem . | Out-File .devweave/cache/probe.txt",
            )
            for command in payloads:
                with self.subTest(command=command):
                    self.assertTrue(
                        denied(
                            guard.handle_hook(
                                bash_payload(harness.repo, session, command), harness.repo
                            )
                        )
                    )

    def test_configured_command_direct_bash_is_denied_after_g2(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            command = harness.configure_command(
                "configured-writer",
                required_for=(),
                writes="generated",
                outputs=("dist",),
            )
            session = "s-configured-direct"
            core.bind_session(harness.repo, session, state["id"])
            command_text = subprocess.list2cmdline(command["argv"])
            result = guard.handle_hook(
                bash_payload(harness.repo, session, command_text), harness.repo
            )
            self.assertTrue(denied(result))

    def test_arbitrary_bash_is_denied_after_g2(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            session = "s-arbitrary"
            core.bind_session(harness.repo, session, state["id"])
            result = guard.handle_hook(
                bash_payload(harness.repo, session, "python -c print('side effect')"),
                harness.repo,
            )
            self.assertTrue(denied(result))

    def test_cli_bind_command_binds_hook_session(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.start()
            command = (
                "python .agents/skills/devweave/scripts/devweave.py --repo . "
                f"bind --work {state['id']}"
            )
            result = guard.handle_hook(
                bash_payload(harness.repo, "s-cli-bind", command), harness.repo
            )
            self.assertFalse(denied(result))
            binding = core.load_session_binding(harness.repo, "s-cli-bind")
            self.assertEqual(state["id"], binding["work"])

    def test_wiki_write_requires_verification_and_exact_knowledge_plan(self) -> None:
        with RepositoryHarness() as harness:
            state = harness.prepare_g2()
            session = "s-wiki"
            core.bind_session(harness.repo, session, state["id"])
            planned = patch_payload(
                harness.repo, session, "wiki/modules/runtime.md"
            )
            self.assertTrue(denied(guard.handle_hook(planned, harness.repo)))
            self.assertTrue(
                denied(
                    guard.handle_hook(
                        bash_payload(
                            harness.repo,
                            session,
                            "Set-Content wiki/modules/runtime.md changed",
                        ),
                        harness.repo,
                    )
                )
            )

            harness.implement(state["id"], "verification", review=False)
            self.assertTrue(denied(guard.handle_hook(planned, harness.repo)))
            core.set_knowledge_review(
                harness.repo,
                state["id"],
                "promote",
                "Guard fixture promotes a planned module page.",
            )
            core.set_knowledge_plan(
                harness.repo,
                state["id"],
                ["wiki/modules/runtime.md"],
                [],
                "Guard fixture promotion.",
            )
            self.assertIsNone(guard.handle_hook(planned, harness.repo))
            self.assertIsNone(
                guard.handle_hook(
                    patch_payload(harness.repo, session, "wiki/index.md"), harness.repo
                )
            )
            self.assertIsNone(
                guard.handle_hook(
                    patch_payload(harness.repo, session, "wiki/log.md"), harness.repo
                )
            )
            self.assertTrue(
                denied(
                    guard.handle_hook(
                        patch_payload(harness.repo, session, "wiki/modules/other.md"),
                        harness.repo,
                    )
                )
            )
            (harness.repo / "src/app.txt").write_text(
                "baseline\nsource changed after knowledge plan\n", encoding="utf-8"
            )
            self.assertTrue(denied(guard.handle_hook(planned, harness.repo)))


if __name__ == "__main__":
    unittest.main()

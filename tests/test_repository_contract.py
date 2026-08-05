from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from devweave_test_support import REPOSITORY_ROOT, RepositoryHarness, SCRIPT_ROOT, core


COMPANION_SKILLS = {
    "codebase-design",
    "diagnosing-bugs",
    "grill-me",
    "grilling",
    "tdd",
}
MAINTENANCE_ONLY_SKILLS = {"writing-great-skills"}
EXPECTED_REPOSITORY_SKILLS = COMPANION_SKILLS | {"devweave"}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class RepositoryContractTests(unittest.TestCase):
    def test_devweave_is_the_only_router_with_expected_companions(self) -> None:
        discovered = {
            path.parent.name
            for path in (REPOSITORY_ROOT / ".agents" / "skills").glob("*/SKILL.md")
        }
        skills = discovered - MAINTENANCE_ONLY_SKILLS
        self.assertEqual(EXPECTED_REPOSITORY_SKILLS, skills)

        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("DevWeave remains the sole SDLC router.", agents)

        for name in sorted(skills):
            source = (
                REPOSITORY_ROOT / ".agents" / "skills" / name / "SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertTrue(source.startswith("---\n"), name)
            frontmatter = source.split("---", 2)[1]
            self.assertRegex(frontmatter, rf"(?m)^name:\s*{re.escape(name)}\s*$")

    def test_maintenance_only_skill_is_excluded_from_governed_sets_and_bundle(
        self,
    ) -> None:
        discovered = {
            path.parent.name
            for path in (REPOSITORY_ROOT / ".agents" / "skills").glob("*/SKILL.md")
        }
        self.assertIn("writing-great-skills", discovered)
        self.assertNotIn("writing-great-skills", COMPANION_SKILLS)

        lock = json.loads(
            (REPOSITORY_ROOT / "skills-lock.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("writing-great-skills", lock["skills"])

        bundle = (REPOSITORY_ROOT / "vscode-extension" / "esbuild.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'const companionSkills = ["codebase-design", "diagnosing-bugs", "grill-me", "grilling", "tdd"]',
            bundle,
        )
        self.assertNotIn("writing-great-skills", bundle)

    def test_skill_frontmatter_metadata_and_invocation_policy_are_explicit(
        self,
    ) -> None:
        for name in sorted(EXPECTED_REPOSITORY_SKILLS):
            skill_root = REPOSITORY_ROOT / ".agents" / "skills" / name
            source = (skill_root / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(source.startswith("---\n"), name)
            frontmatter = source.split("---", 2)[1]
            self.assertRegex(frontmatter, r"(?m)^description:\s*\S.+$")

            metadata = skill_root / "agents" / "openai.yaml"
            self.assertTrue(metadata.exists(), name)
            metadata_source = metadata.read_text(encoding="utf-8")
            self.assertRegex(metadata_source, r'(?m)^\s*display_name:\s*"[^"]+"$')
            self.assertRegex(
                metadata_source, r'(?m)^\s*short_description:\s*"[^"]+"$'
            )

        grill_me = (
            REPOSITORY_ROOT / ".agents" / "skills" / "grill-me" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", grill_me)
        grill_me_metadata = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "grill-me"
            / "agents"
            / "openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", grill_me_metadata)

        devweave_metadata = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "agents"
            / "openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: true", devweave_metadata)

    def test_companion_skill_provenance_and_relative_links_are_complete(self) -> None:
        lock = json.loads(
            (REPOSITORY_ROOT / "skills-lock.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, lock["version"])
        self.assertEqual(COMPANION_SKILLS, set(lock["skills"]))

        for name in sorted(COMPANION_SKILLS):
            record = lock["skills"][name]
            self.assertEqual("mattpocock/skills", record["source"])
            self.assertEqual("github", record["sourceType"])
            self.assertRegex(record["computedHash"], r"^[0-9a-f]{64}$")

            skill_root = REPOSITORY_ROOT / ".agents" / "skills" / name
            for markdown in skill_root.rglob("*.md"):
                source = markdown.read_text(encoding="utf-8")
                for raw_target in MARKDOWN_LINK_PATTERN.findall(source):
                    target = raw_target.strip().strip("<>").split("#", 1)[0]
                    if not target or target.startswith(
                        ("https://", "http://", "mailto:")
                    ):
                        continue
                    resolved = (markdown.parent / target).resolve()
                    self.assertTrue(
                        resolved.is_relative_to(skill_root.resolve()),
                        f"{markdown}: relative link escapes skill root: {raw_target}",
                    )
                    self.assertTrue(
                        resolved.exists(),
                        f"{markdown}: missing relative link target: {raw_target}",
                    )

    def test_companion_skill_precedence_policy_covers_side_effect_boundaries(
        self,
    ) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        required_fragments = (
            "DevWeave remains the sole SDLC router.",
            "`grill-me`/`grilling` during requirements",
            "`codebase-design` during G2 design",
            "`diagnosing-bugs` for bug discovery",
            "`tdd` only during implementation with a current G2 approval",
            "Do not independently create or update `CONTEXT.md`, ADRs, `docs/agents/`",
            "Before G2, do not modify tracked product source or tests.",
            "Keep Wiki read-only until verification.",
            "Do not create issues, branches, worktrees, commits, pushes, pull requests",
            "Never edit DevWeave JSON/JSONL ledgers directly.",
            "run `$devweave revise` from the earliest affected phase",
            "Do not update them automatically",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, agents)

    def test_interactive_decision_policy_is_explicit(self) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        router = (
            REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "SKILL.md"
        ).read_text(encoding="utf-8")
        requirements = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "references"
            / "requirements-phase.md"
        ).read_text(encoding="utf-8")
        design = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "references"
            / "design-phase.md"
        ).read_text(encoding="utf-8")
        verification = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "references"
            / "verification-phase.md"
        ).read_text(encoding="utf-8")
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        manual = (
            REPOSITORY_ROOT / "docs" / "使用手冊.md"
        ).read_text(encoding="utf-8")

        for fragment in (
            "Interactive decision contract:",
            "Facts that can be discovered from Wiki, source, tests, or approved artifacts",
            "native-question-contract.md",
            "request_user_input",
            "Plan-first is mandatory",
            "two or three mutually exclusive options",
            "structured numbered fallback",
            "Each question is asked one at a time with a recommendation and trade-off",
            "never permits the agent to invent a decision or approve a Gate",
            "New requirements, design, scope, or task decisions use `$devweave revise`",
        ):
            self.assertIn(fragment, agents)

        for fragment in (
            "## Interactive decision protocol",
            "During G1, use `grill-me`/`grilling`; during G2, use `codebase-design`.",
            "Follow [native-question-contract.md](references/native-question-contract.md)",
            "Plan Mode is the formal native-question entry",
            "request_user_input",
            "structured numbered fallback",
            "Ask one material decision at a time.",
            "Do not silently choose an unresolved material decision",
            "Before G1 approval, present the answered material decisions",
            "Before G2 approval, present the answered design decisions",
            "Gate summaries are Double Checks against the current artifacts",
        ):
            self.assertIn(fragment, router)

        for fragment in (
            "grill-me`/`grilling` for material requirements decisions and follow",
            "follow [native-question-contract.md](native-question-contract.md)",
            "Plan Mode as the formal native-question entry",
            "request_user_input",
            "structured numbered fallback",
            "Wait for the user's answer before recording the next decision",
            "Stop at the Gate if approval is absent",
        ):
            self.assertIn(fragment, requirements)

        for fragment in (
            "using `codebase-design` vocabulary",
            "For each material design choice, follow",
            "native-question-contract.md",
            "Plan Mode",
            "Stop before product-code or tracked-test changes",
        ):
            self.assertIn(fragment, design)

        for fragment in (
            "Treat G3 as a conformance check against the approved",
            "request_user_input",
            "Do not silently resolve a newly discovered product or design decision",
            "silence or an inferred acceptance is not approval",
        ):
            self.assertIn(fragment, verification)

        for fragment in (
            "G1 的逐題決策流程是",
            "G1/G2/Gate 的正式入口是",
            "request_user_input",
            "structured numbered fallback",
            "G2 使用 `codebase-design` 在 Plan Mode 逐題確認",
            "Plan Mode",
            "每道 Gate 都是 validation 後的 Double Check",
            "若 Gate 發現新需求或設計決策，必須使用 `revise`",
        ):
            self.assertIn(fragment, readme)

        for fragment in (
            "使用 `grill-me`／`grilling` 逐題確認 material requirements",
            "G1/G2/Gate 的正式入口是 Plan Mode",
            "request_user_input",
            "structured numbered fallback",
            "在 Plan Mode 使用 `codebase-design` 逐題確認 material design trade-off",
            "G1/G2 Gate 是對目前 artifacts 的 Double Check",
            "必須使用 `revise` 回到最早受影響 phase",
        ):
            self.assertIn(fragment, manual)

    def test_native_question_contract_is_shared_without_host_or_engine_adapters(
        self,
    ) -> None:
        contract = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "references"
            / "native-question-contract.md"
        ).read_text(encoding="utf-8")
        for fragment in (
            "canonical host tool name is `request_user_input`",
            "questions` contains exactly one item",
            "options` contains two or three mutually exclusive choices",
            "(Recommended)",
            "host-provided `Other`",
            "Before current G2",
            "return to Plan Mode",
            "structured numbered fallback",
            "existing validation and CLI `approve`/`revise` contract",
            "Tool visibility is a host capability",
        ):
            self.assertIn(fragment, contract)
        self.assertNotIn("requestUserInput(", contract)

        for name in sorted(COMPANION_SKILLS):
            source = (
                REPOSITORY_ROOT / ".agents" / "skills" / name / "SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertIn("native question contract", source, name)
            self.assertIn("Plan Mode", source, name)
        router = (
            REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("native-question-contract.md", router)
        self.assertIn("request_user_input", router)

        extension_sources = list(
            (REPOSITORY_ROOT / "vscode-extension" / "src").rglob("*.ts")
        ) + list((REPOSITORY_ROOT / "vscode-extension" / "webview").rglob("*.ts"))
        for path in extension_sources:
            self.assertNotIn("request_user_input", path.read_text(encoding="utf-8"), path)
            self.assertNotIn("requestUserInput", path.read_text(encoding="utf-8"), path)

    def test_runtime_has_no_openspec_or_third_party_imports(self) -> None:
        for path in SCRIPT_ROOT.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("openspec", source.lower(), path.name)
            tree = ast.parse(source, filename=str(path))
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".", 1)[0])
            non_standard = imported - set(sys.stdlib_module_names) - {
                "devweave_core",
                "knowledge_core",
            }
            self.assertEqual(set(), non_standard, f"{path.name}: {sorted(non_standard)}")

    def test_hook_contract_is_json_and_resolves_from_git_root(self) -> None:
        hook_path = REPOSITORY_ROOT / ".codex" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))
        group = hook["hooks"]["PreToolUse"][0]
        self.assertIn("Bash", group["matcher"])
        self.assertIn("apply_patch", group["matcher"])
        command = group["hooks"][0]
        self.assertIn("powershell -NoProfile -Command", command["command"])
        self.assertIn("git rev-parse --show-toplevel", command["command"])
        self.assertNotIn("commandWindows", command)

    def test_hook_launcher_runs_through_windows_cmd_and_preserves_deny_json(self) -> None:
        hook_path = REPOSITORY_ROOT / ".codex" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))
        command = hook["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        payload = {
            "cwd": str(REPOSITORY_ROOT),
            "session_id": "",
            "tool_name": "Write",
            "tool_input": {
                "command": "*** Update File: src/app.txt\n@@\n-old\n+new"
            },
        }
        # Use COMSPEC with the same raw command-string quoting as Codex's
        # Windows hook runner; passing the command as a subprocess argv item
        # changes cmd.exe's handling of the nested PowerShell quotes.
        result = subprocess.run(
            f'cmd.exe /d /s /c "{command}"',
            cwd=REPOSITORY_ROOT,
            input=json.dumps(payload, ensure_ascii=True),
            text=True,
            capture_output=True,
            shell=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        specific = output["hookSpecificOutput"]
        self.assertEqual("PreToolUse", specific["hookEventName"])
        self.assertEqual("deny", specific["permissionDecision"])
        self.assertIn("active work item", specific["permissionDecisionReason"])

    def test_doctor_passes_for_an_initialized_fixture_with_hook(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            target = harness.repo / ".codex" / "hooks.json"
            target.parent.mkdir()
            shutil.copyfile(REPOSITORY_ROOT / ".codex" / "hooks.json", target)
            report = core.doctor(harness.repo)
            self.assertTrue(report["ok"], report["checks"])

    def test_codebase_wiki_closed_loop_is_documented_on_the_single_router(self) -> None:
        documents = {
            ".agents/skills/devweave/SKILL.md": (
                "$devweave wiki bootstrap",
                "knowledge review",
                "knowledge scaffold",
                "at most five related pages",
                "read-only Wiki preflight",
                "custom-only",
            ),
            ".agents/skills/devweave/references/requirements-phase.md": (
                "bootstrap",
                "source fallback",
                "content hash",
            ),
            ".agents/skills/devweave/references/verification-phase.md": (
                "promote|no-update",
                "one to five content",
                "placeholder",
            ),
            ".agents/skills/devweave/references/contracts.md": (
                "knowledge_profile",
                "knowledge_review_required",
                "knowledge bootstrap",
                "knowledge scaffold",
                "reserved-starter preflight",
            ),
            "AGENTS.md": (
                "$devweave wiki bootstrap",
                "Knowledge Review",
                "no-update",
                "Initialization preflight",
            ),
            "README.md": (
                "$devweave wiki bootstrap",
                "Codebase LLM Wiki",
                "Knowledge Review",
                "read-only preflight",
                "半套 `.devweave/`",
            ),
            "docs/使用手冊.md": (
                "knowledge bootstrap",
                "knowledge review",
                "knowledge scaffold",
                "exclusive-create",
                "partial control bundle",
            ),
            "vscode-extension/README.md": (
                "DevWeave: Bootstrap Codebase Wiki",
                "$devweave wiki bootstrap",
                "九個公開",
                "semantic contract",
                "adopted",
            ),
            "vscode-extension/assets/bootstrap/AGENTS.md": (
                "Initialization order",
                "partial control bundle",
            ),
        }
        for relative, fragments in documents.items():
            source = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
            for fragment in fragments:
                self.assertIn(fragment, source, f"{relative}: {fragment}")
            self.assertNotIn("八個公開", source, relative)

    def test_high_risk_review_stays_on_the_single_router_and_read_only_extension(self) -> None:
        router = (REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "SKILL.md").read_text(encoding="utf-8")
        verification = (REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "references" / "verification-phase.md").read_text(encoding="utf-8")
        contracts = (REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "references" / "contracts.md").read_text(encoding="utf-8")
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for source in (router, verification, contracts, agents):
            self.assertIn("isolated", source)
            self.assertIn("read-only", source)
            self.assertIn("review record", source)
            self.assertIn("human", source.lower())
        self.assertIn("There is no public `$devweave review` chat verb.", router)
        self.assertIn("Python engine does not spawn", verification)
        self.assertIn("VS Code Extension does not invoke", verification)
        self.assertIn("review-critical", contracts)
        self.assertIn("G2 `Design It Twice`", agents)

        core_source = (SCRIPT_ROOT / "devweave_core.py").read_text(encoding="utf-8")
        extension_source = (REPOSITORY_ROOT / "vscode-extension" / "src" / "presentation.ts").read_text(encoding="utf-8")
        self.assertIn('"kind": "review"', core_source)
        self.assertIn("independent-review", extension_source)
        self.assertNotIn("multi_agent", core_source)


if __name__ == "__main__":
    unittest.main()

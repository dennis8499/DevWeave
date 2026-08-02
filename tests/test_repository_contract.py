from __future__ import annotations

import ast
import json
import re
import shutil
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
EXPECTED_REPOSITORY_SKILLS = COMPANION_SKILLS | {"devweave"}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class RepositoryContractTests(unittest.TestCase):
    def test_devweave_is_the_only_router_with_expected_companions(self) -> None:
        skills = {
            path.parent.name
            for path in (REPOSITORY_ROOT / ".agents" / "skills").glob("*/SKILL.md")
        }
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
        self.assertIn("git rev-parse --show-toplevel", command["command"])
        self.assertIn("git rev-parse --show-toplevel", command["commandWindows"])

    def test_doctor_passes_for_an_initialized_fixture_with_hook(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            target = harness.repo / ".codex" / "hooks.json"
            target.parent.mkdir()
            shutil.copyfile(REPOSITORY_ROOT / ".codex" / "hooks.json", target)
            report = core.doctor(harness.repo)
            self.assertTrue(report["ok"], report["checks"])


if __name__ == "__main__":
    unittest.main()

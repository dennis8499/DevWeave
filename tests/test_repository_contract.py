from __future__ import annotations

import ast
import json
import shutil
import sys
import unittest
from pathlib import Path

from devweave_test_support import REPOSITORY_ROOT, RepositoryHarness, SCRIPT_ROOT, core


class RepositoryContractTests(unittest.TestCase):
    def test_devweave_is_the_only_repository_skill(self) -> None:
        skills = sorted(
            path.parent.name
            for path in (REPOSITORY_ROOT / ".agents" / "skills").glob("*/SKILL.md")
        )
        self.assertEqual(["devweave"], skills)

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
            non_standard = imported - set(sys.stdlib_module_names) - {"devweave_core"}
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

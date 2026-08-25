from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.architecture_check import ArchitectureChecker


class ArchitectureCheckerTests(unittest.TestCase):
    def test_repository_knowledge_and_architecture_contract_passes(self) -> None:
        report = ArchitectureChecker(ROOT).report()
        self.assertEqual(report["issues"], [], report)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["limits"]["navigation_hops"], 2)

    def test_each_violation_fixture_reports_its_stable_code_and_path(self) -> None:
        cases = json.loads((ROOT / "fixtures" / "devweave_v2" / "architecture-violations.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["name"]), tempfile.TemporaryDirectory(prefix="devweave-architecture-") as temporary:
                fixture = Path(temporary)
                self._copy_baseline(fixture)
                target = fixture / case["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                content = case["content"] * int(case.get("count", 1))
                if case["mode"] == "append":
                    target.write_text(target.read_text(encoding="utf-8") + content, encoding="utf-8")
                else:
                    target.write_text(content, encoding="utf-8")
                report = ArchitectureChecker(fixture).report()
                expected_path = case.get("expected_path", case["path"])
                matches = [item for item in report["issues"] if item["code"] == case["expected_code"] and item["path"] == expected_path]
                self.assertTrue(matches, report)

    def test_exact_owned_unexpired_exception_waives_only_its_code_and_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="devweave-architecture-") as temporary:
            fixture = Path(temporary)
            self._copy_baseline(fixture)
            index = fixture / "docs" / "index.md"
            index.write_text(index.read_text(encoding="utf-8") + "\n[Missing](missing.md)\n", encoding="utf-8")
            exceptions = {
                "schema_version": 2,
                "exceptions": [{
                    "code": "BROKEN_DOC_LINK",
                    "path": "docs/index.md",
                    "owner": "quality-owner",
                    "reason": "Fixture proves exact waiver matching.",
                    "expires": "2099-01-01",
                }],
            }
            (fixture / "docs" / "architecture-exceptions.json").write_text(json.dumps(exceptions), encoding="utf-8")
            report = ArchitectureChecker(fixture).report()
            self.assertEqual(report["status"], "passed", report)
            self.assertEqual(report["waived"][0]["code"], "BROKEN_DOC_LINK")
            exceptions["exceptions"][0]["expires"] = "2000-01-01"
            (fixture / "docs" / "architecture-exceptions.json").write_text(json.dumps(exceptions), encoding="utf-8")
            expired = ArchitectureChecker(fixture).report()
            self.assertIn("EXPIRED_EXCEPTION", {item["code"] for item in expired["issues"]})
            self.assertIn("BROKEN_DOC_LINK", {item["code"] for item in expired["issues"]})

    def _copy_baseline(self, target: Path) -> None:
        for relative in ("AGENTS.md", "ARCHITECTURE.md", "README.md"):
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        shutil.copytree(ROOT / "docs", target / "docs")
        skill_target = target / ".agents" / "skills" / "devweave"
        (skill_target / "references").mkdir(parents=True)
        shutil.copy2(ROOT / ".agents" / "skills" / "devweave" / "SKILL.md", skill_target / "SKILL.md")
        for source in (ROOT / ".agents" / "skills" / "devweave" / "references").glob("*.md"):
            shutil.copy2(source, skill_target / "references" / source.name)
        contracts_target = target / "vscode-extension" / "src" / "v2"
        contracts_target.mkdir(parents=True)
        shutil.copy2(ROOT / "vscode-extension" / "src" / "v2" / "contracts.ts", contracts_target / "contracts.ts")


if __name__ == "__main__":
    unittest.main()

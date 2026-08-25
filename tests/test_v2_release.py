from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2.cutover import (  # noqa: E402
    CutoverFinalizer,
    _git_files,
    _is_legacy,
    generate_manifest,
    write_manifest,
)
from devweave_v2.errors import DevWeaveError, ErrorCode  # noqa: E402
from devweave_v2.project_config import ProjectConfig  # noqa: E402


class CutoverFinalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="devweave-cutover-")
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        self._write_fixture()
        self._git("init", "-q")
        self._git("config", "user.email", "devweave@example.invalid")
        self._git("config", "user.name", "DevWeave Test")
        self._git("add", "-A")
        self._git("commit", "-qm", "legacy fixture")
        self.base_ref = self._git("rev-parse", "HEAD").strip()
        self.manifest_path = self.repository / "docs" / "generated" / "v2-cutover-manifest.json"
        write_manifest(self.manifest_path, generate_manifest(self.repository, base_ref=self.base_ref))

    def test_fresh_apply_and_retry_converge_without_legacy_paths(self) -> None:
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        self.assertEqual("ready", finalizer.check()["status"])
        with self.assertRaisesRegex(RuntimeError, "Injected cutover failure"):
            finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256, fail_after=2)

        retried = finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual("applied", retried["status"])
        self.assertEqual("already_applied", finalizer.check()["status"])
        self.assertEqual(
            "final agents\n",
            (self.repository / "AGENTS.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "final skill\n",
            (self.repository / ".agents/skills/devweave/SKILL.md").read_text(encoding="utf-8"),
        )
        installed = json.loads((self.repository / ".devweave/project.json").read_text(encoding="utf-8"))
        self.assertEqual(2, installed["schema_version"])
        for relative in _git_files(self.repository):
            if _is_legacy(relative):
                self.assertFalse((self.repository / relative).exists(), relative)

        again = finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual({"status": "already_applied", "manifest_sha256": finalizer.manifest_sha256, "mutations": 0}, again)

    def test_hash_drift_fails_before_any_mutation(self) -> None:
        old_agents = (self.repository / "AGENTS.md").read_bytes()
        (self.repository / "wiki/index.md").write_text("drift\n", encoding="utf-8")
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.apply(approved_manifest_sha256=finalizer.manifest_sha256)
        self.assertEqual(ErrorCode.CONFLICT, caught.exception.code)
        self.assertEqual(old_agents, (self.repository / "AGENTS.md").read_bytes())
        self.assertTrue((self.repository / ".agents/skills/grill-me/SKILL.md").exists())

    def test_manifest_hash_and_explicit_approval_are_both_required(self) -> None:
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.apply(approved_manifest_sha256="0" * 64)
        self.assertEqual(ErrorCode.FORBIDDEN, caught.exception.code)
        self.assertEqual("old agents\n", (self.repository / "AGENTS.md").read_text(encoding="utf-8"))

        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        raw["base_ref"] = "f" * 40
        self.manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(DevWeaveError) as tampered:
            CutoverFinalizer(self.repository, self.manifest_path)
        self.assertEqual(ErrorCode.CONFLICT, tampered.exception.code)

    def test_new_legacy_path_after_manifest_is_rejected(self) -> None:
        added = self.repository / "wiki" / "late.md"
        added.write_text("late legacy truth\n", encoding="utf-8")
        self._git("add", "wiki/late.md")
        finalizer = CutoverFinalizer(self.repository, self.manifest_path)
        with self.assertRaises(DevWeaveError) as caught:
            finalizer.check()
        self.assertEqual(ErrorCode.CONFLICT, caught.exception.code)
        self.assertTrue(added.exists())

    def _write_fixture(self) -> None:
        files = {
            "AGENTS.md": "old agents\n",
            ".devweave/project.json": '{"schema_version":1}\n',
            ".devweave/baseline/product.md": "old baseline\n",
            ".devweave/work-items/old/state.json": "{}\n",
            "wiki/index.md": "old wiki\n",
            ".agents/skills/devweave/SKILL.md": "old skill\n",
            ".agents/skills/devweave/references/contracts.md": "old reference\n",
            ".agents/skills/devweave/scripts/devweave.py": "# old launcher\n",
            ".agents/skills/devweave/assets/v2-cutover/AGENTS.md": "final agents\n",
            ".agents/skills/devweave/assets/v2-cutover/project.json": '{"schema_version":2}\n',
            ".agents/skills/devweave/assets/v2-skill/SKILL.md": "final skill\n",
            ".agents/skills/devweave/assets/v2-skill/references/planning.md": "planning\n",
            ".agents/skills/devweave/assets/v2-skill/references/implementation.md": "implementation\n",
            ".agents/skills/devweave/assets/v2-skill/references/verification.md": "verification\n",
            ".agents/skills/grill-me/SKILL.md": "legacy companion\n",
            "skills-lock.json": "{}\n",
            "tests/devweave_test_support.py": "# old support\n",
            "tests/test_cli.py": "# old test\n",
            "tests/test_v2_contracts.py": "# v2 test\n",
            "vscode-extension/src/clipboard.ts": "export const old = true;\n",
            "vscode-extension/src/extension.ts": "export const current = true;\n",
            "vscode-extension/test/unit/wiki-search.test.ts": "// old test\n",
            "vscode-extension/test/unit/security.test.ts": "// v2 test\n",
            "vscode-extension/devweave-control-center-0.2.3.vsix": "legacy binary\x00",
        }
        for relative, content in files.items():
            path = self.repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.repository, check=True, capture_output=True,
            text=True, encoding="utf-8", shell=False,
        )
        return result.stdout


class RepositoryReleaseContractTests(unittest.TestCase):
    def test_staged_project_is_strict_schema_v2_with_release_dag(self) -> None:
        path = REPOSITORY_ROOT / ".agents/skills/devweave/assets/v2-cutover/project.json"
        config = ProjectConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
        command_ids = {command.command_id for command in config.verification_plan.commands}
        self.assertEqual(
            {
                "repository-check", "python-v2", "extension-typecheck", "extension-tests",
                "extension-build", "extension-package", "extension-smoke", "app-server-e2e",
            },
            command_ids,
        )
        self.assertTrue(next(item for item in config.verification_plan.commands if item.command_id == "extension-package").release_only)
        self.assertTrue(next(item for item in config.verification_plan.commands if item.command_id == "app-server-e2e").release_only)

    def test_repository_manifest_is_hash_bound_and_ready(self) -> None:
        manifest_path = REPOSITORY_ROOT / "docs/generated/v2-cutover-manifest.json"
        finalizer = CutoverFinalizer(REPOSITORY_ROOT, manifest_path)
        report = finalizer.check()
        self.assertEqual("ready", report["status"])
        self.assertEqual(6, report["pending_replacements"])
        self.assertGreater(report["pending_deletions"], 600)


if __name__ == "__main__":
    unittest.main()

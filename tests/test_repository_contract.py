from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

try:
    from devweave_test_support import REPOSITORY_ROOT, RepositoryHarness, SCRIPT_ROOT, core
except ModuleNotFoundError as error:
    if error.name != "devweave_test_support":
        raise
    from tests.devweave_test_support import REPOSITORY_ROOT, RepositoryHarness, SCRIPT_ROOT, core


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
WINDOWS_HOOK_RUNNERS = ("cmd", "powershell", "pwsh")


def run_windows_hook(
    command: str,
    cwd: Path,
    payload: bytes,
    runner: str,
) -> subprocess.CompletedProcess[bytes]:
    if runner == "cmd":
        return subprocess.run(
            f'cmd.exe /d /s /c "{command}"',
            cwd=cwd,
            input=payload,
            capture_output=True,
            shell=True,
            check=False,
        )
    executable = "powershell.exe" if runner == "powershell" else "pwsh"
    return subprocess.run(
        [
            executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ],
        cwd=cwd,
        input=payload,
        capture_output=True,
        shell=False,
        check=False,
    )


class RepositoryContractTests(unittest.TestCase):
    def test_devweave_is_the_only_router_during_the_legacy_cutover(self) -> None:
        discovered = {
            path.parent.name
            for path in (REPOSITORY_ROOT / ".agents" / "skills").glob("*/SKILL.md")
        }
        skills = discovered - MAINTENANCE_ONLY_SKILLS
        self.assertEqual(EXPECTED_REPOSITORY_SKILLS, skills)

        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Use the [DevWeave skill]", agents)
        self.assertIn("One-time cutover note", agents)
        for legacy_name in sorted(COMPANION_SKILLS):
            self.assertNotIn(legacy_name, agents)

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
        for name in sorted(COMPANION_SKILLS):
            self.assertNotIn(name, bundle)
        self.assertNotIn("bootstrap", bundle.lower())
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

    def test_root_map_covers_v2_authority_and_side_effect_boundaries(
        self,
    ) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        required_fragments = (
            "documentation index",
            "ARCHITECTURE.md",
            "Sources of truth",
            "Agent-facing MCP exposes exactly eight workflow tools",
            "Start/resume, human decisions, Gates, and cancel remain host-only",
            "shell=False",
            "undeclared writes",
            "symlink escape",
            "Never persist raw reasoning",
            "Do not push, open a pull request, merge, reset, or switch branches",
            "Do not edit canonical run JSON by hand",
            "exact code/path plus owner, reason, and unexpired date",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, agents)

        self.assertLessEqual(len(agents.splitlines()), 100)
        self.assertLessEqual(len(agents.encode("utf-8")), 8_000)
        for legacy_name in sorted(COMPANION_SKILLS):
            self.assertNotIn(legacy_name, agents)

    def test_interactive_decision_policy_is_explicit(self) -> None:
        product = (REPOSITORY_ROOT / "docs" / "product.md").read_text(
            encoding="utf-8"
        )
        design = (REPOSITORY_ROOT / "docs" / "design.md").read_text(
            encoding="utf-8"
        )
        planning = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "assets"
            / "v2-skill"
            / "references"
            / "planning.md"
        ).read_text(encoding="utf-8")
        router = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "assets"
            / "v2-skill"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        for fragment in (
            "typed `PendingDecision` records",
            "two or three options",
            "recommendation",
            "optional custom answer",
            "Only the host can answer them",
        ):
            self.assertIn(fragment, design)

        for fragment in (
            "material product choice",
            "two or three mutually exclusive options",
            "recommendation",
            "optional custom-answer policy",
            "Stop the affected task until the host resolves it",
            "Do not call a Gate operation",
            "interpret silence as approval",
        ):
            self.assertIn(fragment, planning)

        self.assertIn("Pending decision round-trip", product)
        self.assertIn("malformed/stale input leaves the task pending", product)
        self.assertIn("decisions, Gates, and cancellation", router)
        self.assertIn("Agent/reviewer output is evidence, never approval", router)

    def test_pending_decisions_are_host_only_without_agent_passthrough(
        self,
    ) -> None:
        router = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "assets"
            / "v2-skill"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        product = (REPOSITORY_ROOT / "docs" / "product.md").read_text(
            encoding="utf-8"
        )
        security = (REPOSITORY_ROOT / "docs" / "security.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("decision_request", router)
        self.assertIn("decision_resolve", product)
        self.assertIn("Host/agent capability isolation", product)
        self.assertIn("MCP cannot discover or forward", security)
        self.assertIn("decision resolution", security)

        extension_sources = list(
            (REPOSITORY_ROOT / "vscode-extension" / "src").rglob("*.ts")
        ) + list((REPOSITORY_ROOT / "vscode-extension" / "webview").rglob("*.ts"))
        for path in extension_sources:
            self.assertNotIn("request_user_input", path.read_text(encoding="utf-8"), path)
            self.assertNotIn("requestUserInput", path.read_text(encoding="utf-8"), path)

    def test_codex_preflight_and_control_center_ownership_are_documented(
        self,
    ) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        product = (REPOSITORY_ROOT / "docs" / "product.md").read_text(
            encoding="utf-8"
        )
        design = (REPOSITORY_ROOT / "docs" / "design.md").read_text(
            encoding="utf-8"
        )
        security = (REPOSITORY_ROOT / "docs" / "security.md").read_text(
            encoding="utf-8"
        )
        extension = (
            REPOSITORY_ROOT / "vscode-extension" / "src" / "extension.ts"
        ).read_text(encoding="utf-8")

        self.assertIn("Missing Codex is a hard, machine-readable blocker", product)
        self.assertIn("locally installed Codex CLI", readme)
        self.assertIn("never downloads Codex", readme)
        self.assertIn("Control Center", design)
        self.assertIn("host facade contains five lifecycle mutations", design)
        self.assertIn("Codex is resolved locally and never downloaded", security)
        self.assertIn("codexPath", extension)
        self.assertIn("devweave_v2_host.py", extension)
        self.assertIn("startRun", extension)
        self.assertNotIn("clipboard.writeText", extension)

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
                "devweave_v2",
                "command_policy",
                "knowledge_core",
            }
            self.assertEqual(set(), non_standard, f"{path.name}: {sorted(non_standard)}")

    def test_hook_contract_is_json_and_resolves_from_git_root(self) -> None:
        hook_path = REPOSITORY_ROOT / ".codex" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))
        group = hook["hooks"]["PreToolUse"][0]
        self.assertEqual("^(Bash|apply_patch|Edit|Write)$", group["matcher"])
        self.assertEqual(1, len(hook["hooks"]["PreToolUse"]))
        command = group["hooks"][0]
        self.assertEqual("command", command["type"])
        self.assertEqual(30, command["timeout"])
        self.assertEqual("Checking DevWeave gates", command["statusMessage"])
        self.assertIn("python3 -X utf8 -B", command["command"])
        self.assertIn("$(git rev-parse --show-toplevel)", command["command"])
        self.assertNotIn("$repo", command["command"])
        self.assertIn("commandWindows", command)
        self.assertIn(
            "powershell.exe -NoLogo -NoProfile -NonInteractive -Command",
            command["commandWindows"],
        )
        self.assertIn("py -3 -X utf8 -B", command["commandWindows"])
        self.assertIn(
            "Join-Path (git rev-parse --show-toplevel)",
            command["commandWindows"],
        )
        self.assertIn("[Console]::InputEncoding = [System.Text.UTF8Encoding]::new(0)", command["commandWindows"])
        self.assertIn("[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(0)", command["commandWindows"])
        self.assertNotIn("$repo", command["commandWindows"])

    def test_hook_launcher_matrix_preserves_utf8_deny_json(self) -> None:
        hook_path = REPOSITORY_ROOT / ".codex" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))
        command = hook["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"]
        for runner in WINDOWS_HOOK_RUNNERS:
            for cwd in (REPOSITORY_ROOT, REPOSITORY_ROOT / "vscode-extension"):
                payload = {
                    "cwd": str(cwd),
                    "session_id": "",
                    "tool_name": "Write",
                    "tool_input": {
                        "command": "*** 更新檔案：src/應用程式.txt\n@@\n-舊\n+新"
                    },
                }
                result = run_windows_hook(
                    command,
                    cwd,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    runner,
                )
                self.assertEqual(
                    0,
                    result.returncode,
                    f"{runner} at {cwd}: {result.stderr.decode('utf-8', errors='replace')}",
                )
                output = json.loads(result.stdout.decode("utf-8"))
                specific = output["hookSpecificOutput"]
                self.assertEqual("PreToolUse", specific["hookEventName"])
                self.assertEqual("deny", specific["permissionDecision"])
                self.assertIn("active work item", specific["permissionDecisionReason"])

    def test_hook_launcher_matrix_returns_valid_deny_json_for_malformed_utf8_json(self) -> None:
        hook_path = REPOSITORY_ROOT / ".codex" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))
        command = hook["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"]
        for runner in WINDOWS_HOOK_RUNNERS:
            for cwd in (REPOSITORY_ROOT, REPOSITORY_ROOT / "vscode-extension"):
                result = run_windows_hook(command, cwd, b'{"cwd":', runner)
                self.assertEqual(
                    0,
                    result.returncode,
                    f"{runner} at {cwd}: {result.stderr.decode('utf-8', errors='replace')}",
                )
                output = json.loads(result.stdout.decode("utf-8"))
                specific = output["hookSpecificOutput"]
                self.assertEqual("deny", specific["permissionDecision"])
                self.assertIn("無法解析 hook input", specific["permissionDecisionReason"])

    def test_hook_launcher_matrix_keeps_read_only_bash_silent(self) -> None:
        hook_path = REPOSITORY_ROOT / ".codex" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))
        command = hook["hooks"]["PreToolUse"][0]["hooks"][0]["commandWindows"]
        for runner in WINDOWS_HOOK_RUNNERS:
            for cwd in (REPOSITORY_ROOT, REPOSITORY_ROOT / "vscode-extension"):
                payload = {
                    "cwd": str(cwd),
                    "session_id": "",
                    "tool_name": "Bash",
                    "tool_input": {"command": "git status --short"},
                }
                result = run_windows_hook(
                    command,
                    cwd,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    runner,
                )
                self.assertEqual(
                    0,
                    result.returncode,
                    f"{runner} at {cwd}: {result.stderr.decode('utf-8', errors='replace')}",
                )
                self.assertEqual(b"", result.stdout)

    def test_doctor_passes_for_an_initialized_fixture_with_hook(self) -> None:
        with RepositoryHarness() as harness:
            harness.init()
            target = harness.repo / ".codex" / "hooks.json"
            target.parent.mkdir()
            shutil.copyfile(REPOSITORY_ROOT / ".codex" / "hooks.json", target)
            guard_target = harness.repo / ".agents" / "skills" / "devweave" / "scripts" / "guard.py"
            guard_target.parent.mkdir(parents=True)
            for script_name in ("guard.py", "devweave_core.py", "command_policy.py", "knowledge_core.py"):
                shutil.copyfile(
                    REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "scripts" / script_name,
                    guard_target.parent / script_name,
                )
            report = core.doctor(harness.repo)
            checks = {item["name"]: item for item in report["checks"]}
            for name in ("py-3", "cmd", "powershell", "pwsh", "hook-schema", "launcher-probe"):
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
            self.assertTrue(report["ok"], report["checks"])

    def test_v2_knowledge_tree_and_release_contract_are_documented(self) -> None:
        required = (
            "ARCHITECTURE.md",
            "docs/index.md",
            "docs/product.md",
            "docs/design.md",
            "docs/reliability.md",
            "docs/security.md",
            "docs/quality.md",
            "docs/generated/README.md",
            "docs/exec-plans/active/README.md",
            "docs/exec-plans/completed/README.md",
            "docs/exec-plans/tech-debt.md",
        )
        for relative in required:
            self.assertTrue((REPOSITORY_ROOT / relative).is_file(), relative)

        index = (REPOSITORY_ROOT / "docs" / "index.md").read_text(
            encoding="utf-8"
        )
        for label in (
            "Architecture",
            "Product",
            "Design",
            "Reliability",
            "Security",
            "Quality",
            "Active ExecPlans",
            "Completed ExecPlans",
            "Tech debt",
            "Generated references",
        ):
            self.assertIn(label, index)

        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("# DevWeave 2.0.0", readme)
        self.assertIn("exactly eight allowlisted MCP tools", readme)
        self.assertIn("six verbs", readme)
        self.assertIn("clean cutover", readme)
        self.assertIn("never downloads Codex", readme)
        self.assertIn("falls back to a clipboard workflow", readme)

        canonical_surfaces = [
            REPOSITORY_ROOT / "AGENTS.md",
            REPOSITORY_ROOT / "ARCHITECTURE.md",
            *(REPOSITORY_ROOT / "docs" / name for name in (
                "index.md",
                "product.md",
                "design.md",
                "reliability.md",
                "security.md",
                "quality.md",
            )),
        ]
        for path in canonical_surfaces:
            source = path.read_text(encoding="utf-8")
            for legacy_name in sorted(COMPANION_SKILLS):
                self.assertNotIn(legacy_name, source, path)

    def test_high_risk_review_is_bounded_detached_and_human_accepted(self) -> None:
        skill_root = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "assets"
            / "v2-skill"
        )
        router = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        verification = (skill_root / "references" / "verification.md").read_text(
            encoding="utf-8"
        )
        product = (REPOSITORY_ROOT / "docs" / "product.md").read_text(
            encoding="utf-8"
        )
        design = (REPOSITORY_ROOT / "docs" / "design.md").read_text(
            encoding="utf-8"
        )
        coordinator = (
            REPOSITORY_ROOT
            / "vscode-extension"
            / "src"
            / "controller"
            / "review-coordinator.ts"
        ).read_text(encoding="utf-8")

        self.assertIn("high risk permits at most three detached", router)
        self.assertIn("Human acceptance remains mandatory", router)
        self.assertIn("reviewer output is evidence, never approval", router)
        self.assertIn("stops after three rounds", verification)
        self.assertIn("Unresolved critical findings", verification)
        self.assertIn("human Gate", verification)
        self.assertIn("AC-014: Bounded independent review", product)
        self.assertIn("A reviewer cannot reuse the implementation thread identity", design)
        self.assertIn("raw reviewer reasoning is not persisted", design)
        self.assertIn("maxRounds", coordinator)
        self.assertIn("detached", coordinator)


if __name__ == "__main__":
    unittest.main()

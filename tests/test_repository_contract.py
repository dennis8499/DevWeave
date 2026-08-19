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
NON_WINDOWS_DOCTOR_SKIP = "Windows-only prerequisite probe skipped on this non-Windows host."


def workflow_job_block(source: str, job_id: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job_id)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        source,
    )
    if match is None:
        raise AssertionError(f"workflow job is missing: {job_id}")
    return match.group("body")


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
    def test_public_ci_workflow_is_cross_platform_and_least_privilege(self) -> None:
        workflow_path = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow_path.is_file(), workflow_path)
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertIn(
            "on:\n  pull_request:\n  push:\n    branches:\n      - master\n",
            workflow,
        )
        self.assertEqual(1, workflow.count("permissions:"))
        self.assertIn("permissions:\n  contents: read\n", workflow)
        self.assertNotIn("continue-on-error", workflow)
        self.assertNotIn("${{ secrets.", workflow)

        checkout = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"
        setup_python = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0"
        setup_node = "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0"
        self.assertEqual(3, workflow.count(checkout))
        self.assertEqual(3, workflow.count("persist-credentials: false"))
        self.assertEqual(1, workflow.count(setup_python))
        self.assertEqual(1, workflow.count(setup_node))
        self.assertNotRegex(workflow, r"actions/(?:checkout|setup-python|setup-node)@v\d")

        python_job = workflow_job_block(workflow, "python")
        self.assertIn("name: Python ${{ matrix.python-version }} / ${{ matrix.os }}", python_job)
        self.assertIn("runs-on: ${{ matrix.os }}", python_job)
        self.assertIn("fail-fast: false", python_job)
        self.assertIn(
            "os: [ubuntu-latest, windows-latest, macos-latest]",
            python_job,
        )
        self.assertIn(
            'python-version: ["3.11", "3.12", "3.13", "3.14"]',
            python_job,
        )
        self.assertIn(setup_python, python_job)
        self.assertIn("python-version: ${{ matrix.python-version }}", python_job)
        self.assertIn("python -B -m unittest discover -s tests -v", python_job)

        node_job = workflow_job_block(workflow, "node")
        self.assertIn("name: Node ${{ matrix.node-version }} / ${{ matrix.os }}", node_job)
        self.assertIn("runs-on: ${{ matrix.os }}", node_job)
        self.assertIn("fail-fast: false", node_job)
        self.assertIn("os: [ubuntu-latest, windows-latest]", node_job)
        self.assertIn('node-version: ["20", "22"]', node_job)
        self.assertIn(setup_node, node_job)
        self.assertIn("node-version: ${{ matrix.node-version }}", node_job)
        self.assertIn("working-directory: vscode-extension", node_job)
        node_commands = (
            "npm ci",
            "npm run typecheck",
            "npm test",
            "npm run build",
        )
        positions = [node_job.index(command) for command in node_commands]
        self.assertEqual(sorted(positions), positions)

        hygiene_job = workflow_job_block(workflow, "hygiene")
        self.assertIn("name: Repository hygiene", hygiene_job)
        self.assertIn("runs-on: ubuntu-latest", hygiene_job)
        self.assertIn("git diff --check", hygiene_job)

    def test_public_ci_badge_and_local_equivalent_commands_are_documented(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        badge = (
            "[![CI](https://github.com/dennis8499/DevWeave/actions/workflows/"
            "ci.yml/badge.svg?branch=master)](https://github.com/dennis8499/"
            "DevWeave/actions/workflows/ci.yml)"
        )
        self.assertIn(badge, readme)
        self.assertIn("### PowerShell 本機等價命令", readme)
        self.assertIn("### POSIX 本機等價命令", readme)
        self.assertIn("### VS Code Extension 本機等價命令", readme)
        for command in (
            "py -3 -X utf8 -B -m unittest discover -s tests -v",
            "python3 -X utf8 -B -m unittest discover -s tests -v",
            "git diff --check",
            "npm ci",
            "npm run typecheck",
            "npm test",
            "npm run build",
        ):
            self.assertIn(command, readme)
        self.assertIn("CI 開發矩陣不等於正式 release certification", readme)

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

    def test_initial_plan_mode_preflight_and_control_center_handoff_are_documented(
        self,
    ) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        router = (REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "SKILL.md").read_text(encoding="utf-8")
        contract = (
            REPOSITORY_ROOT
            / ".agents"
            / "skills"
            / "devweave"
            / "references"
            / "native-question-contract.md"
        ).read_text(encoding="utf-8")
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        manual = (REPOSITORY_ROOT / "docs" / "使用手冊.md").read_text(encoding="utf-8")
        extension_readme = (REPOSITORY_ROOT / "vscode-extension" / "README.md").read_text(encoding="utf-8")
        bootstrap_agents = (
            REPOSITORY_ROOT / "vscode-extension" / "assets" / "bootstrap" / "AGENTS.md"
        ).read_text(encoding="utf-8")

        for source in (agents, router, contract):
            self.assertIn("request_user_input", source)
            self.assertIn("explicitly chooses compatibility", source)
            self.assertIn("start", source)
            self.assertIn("bind", source)

        self.assertIn("Initial Plan Mode preflight", router)
        self.assertIn("## Initial mutation preflight", contract)
        self.assertIn("Plan Mode preflight", agents)
        self.assertIn("Plan Mode preflight", readme)
        self.assertIn("Plan Mode preflight", manual)
        self.assertIn("Plan Mode preflight", bootstrap_agents)
        self.assertIn("先切換 Plan Mode，再貼到 Codex Chat", extension_readme)
        self.assertIn("不會嘗試切換 host mode", extension_readme)

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
            windows_checks = (
                "py-3",
                "cmd",
                "powershell",
                "pwsh",
                "hook-schema",
                "launcher-probe",
            )
            for name in windows_checks:
                self.assertIn(name, checks)
                self.assertTrue(checks[name]["ok"], checks[name])
                if sys.platform == "win32":
                    self.assertNotEqual(NON_WINDOWS_DOCTOR_SKIP, checks[name]["detail"])
                else:
                    self.assertEqual(NON_WINDOWS_DOCTOR_SKIP, checks[name]["detail"])
            self.assertTrue(report["ok"], report["checks"])

    def test_codebase_wiki_and_current_release_contracts_are_documented(self) -> None:
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

        release_surfaces = (
            "README.md",
            "docs/使用手冊.md",
            "vscode-extension/README.md",
            "vscode-extension/webview/help-content.ts",
        )
        release_contract = (
            "本次提供 0.2.3 VSIX",
            "本次認證環境",
            "Windows x64 build 10.0.26200／25H2",
            "VS Code 1.131.0",
            "Python 3.14.6",
            "Git 2.51.0.windows.1",
            "目前 Codex host",
            "技術門檻",
            "Python full suite 111 項",
            "Extension unit tests 88 項",
            "symlink 權限",
            "停止散布",
            "不會自動刪除 `.devweave`、Wiki 或 workspace 資料",
            "PreToolUse",
            "commandWindows",
            "py -3 -X utf8 -B",
            "CMD",
            "PowerShell 7",
            "VS Code terminal",
            "launcher failure",
        )
        for relative in release_surfaces:
            source = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
            for fragment in release_contract:
                self.assertIn(fragment, source, f"{relative}: {fragment}")
            self.assertNotIn("本次提供 0.2.2 VSIX", source, relative)
            self.assertNotIn("停用或解除安裝 0.2.2", source, relative)
            self.assertNotRegex(source, r"\b0\.(?:1\.0|2\.0)\b", relative)

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

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPOSITORY_ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import devweave_core as core


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class RepositoryHarness:
    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="devweave-test-")
        self.repo = Path(self._temporary.name).resolve()
        run_git(self.repo, "init")
        run_git(self.repo, "config", "user.name", "DevWeave Test")
        run_git(self.repo, "config", "user.email", "devweave@example.test")
        (self.repo / "src").mkdir()
        (self.repo / "README.md").write_text("# Fixture\n", encoding="utf-8")
        (self.repo / "src" / "app.txt").write_text("baseline\n", encoding="utf-8")
        run_git(self.repo, "add", "README.md", "src/app.txt")
        run_git(self.repo, "commit", "-m", "fixture baseline")

    def __enter__(self) -> "RepositoryHarness":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._temporary.cleanup()

    def init(self) -> dict[str, Any]:
        return core.init_project(self.repo)

    def start(
        self,
        kind: str = "feature",
        title: str = "Fixture change",
        risk: str = "standard",
    ) -> dict[str, Any]:
        self.init()
        return core.create_work(
            self.repo,
            kind=kind,
            title=title,
            risk=risk,
            risk_rationale="影響範圍已知，使用標準驗證與人工關卡。",
        )

    def work_file(self, work_id: str, name: str) -> Path:
        return core.work_root(self.repo, work_id) / name

    def fill_requirements(self, work_id: str) -> None:
        self.work_file(work_id, "brief.md").write_text(
            """# 工作摘要

## 問題與目標
提供一個可由使用者觀察、可驗收的成果。

## 現況證據
已檢查 README、Git 基線與 src/app.txt。

## 範圍
僅修改 src 下的垂直切片與對應驗證。

## 非目標
不部署、不推送、不變更遠端服務。

## 風險
標準風險；相容性由回歸證據確認。

## Profile 補充
入口所需的現況、契約或重現資訊已記錄。
""",
            encoding="utf-8",
        )
        self.work_file(work_id, "requirements.md").write_text(
            """# 需求與驗收條件

## 假設與限制
本機 Git 與 Python 可使用；不操作遠端。

## 需求與驗收條件

## REQ-001: 提供可觀察的成果
- Priority: must
- Acceptance: AC-001
- Description: 使用者可以觀察到本工作項的新結果。

## NFR-001: 維持相容性
- Priority: must
- Acceptance: AC-002
- Description: 既有行為與驗證不得退步。

## AC-001: 新成果可使用
- Requirement: REQ-001
- Scenario: Given 已完成實作，When 執行驗證，Then 新成果通過。

## AC-002: 既有行為維持
- Requirement: NFR-001
- Scenario: Given 既有基線，When 執行回歸，Then 結果通過。
""",
            encoding="utf-8",
        )
        core.set_knowledge_context(
            self.repo,
            work_id,
            ["wiki/index.md", "wiki/overview.md"],
            ["wiki/overview.md 尚為 placeholder；探索已回溯 fixture raw source。"],
        )

    def fill_design(self, work_id: str, high_risk: bool = False) -> None:
        risk_analysis = (
            "Migration：採向後相容步驟；Rollback：可還原單一切片；"
            "Security：無新增信任邊界；Compatibility：回歸覆蓋；Performance：維持基準。"
            if high_risk
            else "本工作不含資料 migration；可直接還原檔案，安全與效能風險由既有邊界控制。"
        )
        self.work_file(work_id, "design.md").write_text(
            f"""# 系統設計

## 設計摘要
在既有邊界內加入最小可驗證切片，保持單向資料流。

## 選項比較
比較直接擴充與新增抽象層；選擇直接擴充以降低不必要複雜度。

## 介面與資料流
輸入經既有入口轉換為結果，不改變公開相容契約。

## 失敗模式與回復
驗證失敗即停止驗收；修改可由單一檔案回復。

## 高風險分析
{risk_analysis}

## 設計決策

## DEC-001: 採用最小垂直切片
- Requirements: REQ-001, NFR-001
- Decision: 在既有邊界內完成變更。
- Rationale: 可獨立驗證且容易回復。
- Consequences: 需同時執行新行為與回歸驗證。
""",
            encoding="utf-8",
        )
        self.work_file(work_id, "plan.md").write_text(
            """# 執行計畫

## 工作分解

## TASK-001: 完成可驗證的垂直切片
- Traces: REQ-001, NFR-001, AC-001, AC-002, DEC-001
- Inputs: 已核准的需求與設計。
- Output: src/app.txt 的可觀察變更。
- Verification: targeted、acceptance 與 regression。
- Dependencies: none

## 驗證策略
執行語言中立的設定命令，並保留 acceptance 與 regression 證據。

## 基線更新計畫
new 入口更新 architecture baseline；其餘入口記錄不需更新理由。
""",
            encoding="utf-8",
        )

    def fill_acceptance(self, work_id: str, evidence_ids: list[str]) -> None:
        evidence = ", ".join(evidence_ids)
        self.work_file(work_id, "acceptance.md").write_text(
            f"""# 功能驗收

## 驗證矩陣
AC-001、AC-002 對應 TASK-001，證據為 {evidence}，且綁定目前 source fingerprint。

## Profile 證據
入口要求的 acceptance、regression、equivalence 或 red-before/green-after 已保存。

## 基線更新
已更新指定 living baseline，或已記錄不需更新的理由。

## Wiki 知識提升
已完成必要的 affected-page promotion；沒有目標時 Wiki 維持不變。

## 殘餘風險
無未處理的殘餘風險。

## 驗收結論
所有驗收條件、任務與必要證據均已完成，可提交 G3 核准。
""",
            encoding="utf-8",
        )

    def promote_overview(self, work_id: str) -> None:
        core.set_knowledge_plan(
            self.repo,
            work_id,
            ["wiki/overview.md"],
            [],
            "new work 將 overview 提升為具來源的 active 知識。",
        )
        overview = self.repo / "wiki" / "overview.md"
        frontmatter, _, errors = core.knowledge.parse_frontmatter_text(
            overview.read_text(encoding="utf-8")
        )
        if errors:
            raise AssertionError(errors)
        frontmatter["sources"] = ["src/app.txt"]
        frontmatter["status"] = "active"
        body = """
# Fixture Overview

## Scope

此 fixture 以 `src/app.txt` 提供可驗收的垂直切片。

## Architecture

單一 source file 代表最小產品邊界。

## Key Modules

- `src/app.txt`

## Gaps

- 無。
"""
        overview.write_text(
            core.knowledge.render_frontmatter(frontmatter, body), encoding="utf-8"
        )
        index = self.repo / "wiki" / "index.md"
        index.write_text(
            index.read_text(encoding="utf-8").replace(
                "專案概觀 placeholder", "Fixture 的 active、source-bound 專案概觀"
            ),
            encoding="utf-8",
        )
        log = self.repo / "wiki" / "log.md"
        log.write_text(
            log.read_text(encoding="utf-8")
            + f"\n## [2099-01-01] promote | {work_id}\n\n"
            + "- Promoted [[overview]] from current fixture source behavior.\n",
            encoding="utf-8",
        )
        core.seal_knowledge(
            self.repo,
            work_id,
            ["wiki/overview.md", "wiki/index.md", "wiki/log.md"],
        )

    def configure_command(
        self,
        command_id: str = "fixture-tests",
        *,
        argv: list[str] | None = None,
        timeout_seconds: int = 30,
        required_for: tuple[str, ...] = ("standard",),
    ) -> dict[str, Any]:
        project = core.load_project(self.repo)
        command = {
            "id": command_id,
            "argv": argv or [sys.executable, "-c", "print('fixture verification passed')"],
            "cwd": ".",
            "timeout_seconds": timeout_seconds,
            "required_for": list(required_for),
        }
        project["commands"] = [
            item for item in project.get("commands", []) if item.get("id") != command_id
        ] + [command]
        for level in core.RISK_LEVELS:
            profile = project.setdefault("verification_profiles", {}).setdefault(level, [])
            if level in required_for and command_id not in profile:
                profile.append(command_id)
            if level not in required_for and command_id in profile:
                profile.remove(command_id)
        core.atomic_write_json(core.project_path(self.repo), project)
        return command

    def prepare_g2(
        self,
        kind: str = "feature",
        title: str = "Fixture change",
        risk: str = "standard",
    ) -> dict[str, Any]:
        state = self.start(kind, title, risk)
        work_id = state["id"]
        self.fill_requirements(work_id)
        core.set_scope(self.repo, work_id, ["src/**"], "限制在實作切片路徑。")
        if kind == "bug":
            core.add_evidence(
                self.repo,
                work_id,
                kind="reproduction",
                status="passed",
                summary="修正前可穩定觀察到錯誤。",
                covers=["AC-001"],
                observed_result="failure",
                binds_current_source=False,
            )
        if kind == "refactor":
            core.add_evidence(
                self.repo,
                work_id,
                kind="baseline",
                status="passed",
                summary="重構前行為基線已保存。",
                covers=["AC-002"],
                observed_result="success",
                binds_current_source=False,
            )
        core.approve_gate(self.repo, work_id, "scope", "Test Approver")
        self.fill_design(work_id, high_risk=risk == "high")
        return core.approve_gate(self.repo, work_id, "build", "Test Approver")

    def implement(self, work_id: str, marker: str, *, review: bool = True) -> None:
        core.update_task(self.repo, work_id, "TASK-001", "start")
        (self.repo / "src" / "app.txt").write_text(
            f"baseline\n{marker}\n", encoding="utf-8"
        )
        core.update_task(
            self.repo,
            work_id,
            "TASK-001",
            "complete",
            note="切片已完成，驗證將於 verification phase 執行。",
        )
        state = core.load_state(self.repo, work_id)
        if review and state.get("knowledge_review_required"):
            status = core.work_knowledge_status(self.repo, state)
            disposition = (
                "promote"
                if state.get("kind") == "new"
                or state.get("knowledge_profile") == "bootstrap"
                or status.get("affected_pages")
                else "no-update"
            )
            core.set_knowledge_review(
                self.repo,
                work_id,
                disposition,
                "Fixture 依 affected pages 與 durable knowledge 邊界完成 review。",
            )


def load_scenarios() -> list[dict[str, Any]]:
    fixture_root = REPOSITORY_ROOT / "fixtures" / "devweave"
    return [
        json.loads((fixture_root / f"{kind}.json").read_text(encoding="utf-8"))
        for kind in core.KINDS
    ]

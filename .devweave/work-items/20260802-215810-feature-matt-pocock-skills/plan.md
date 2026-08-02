# 執行計畫：導入 Matt Pocock 核心工程 Skills 作為階段內方法

<!-- DEVWEAVE:artifact=plan version=1 work=20260802-215810-feature-matt-pocock-skills -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 安裝精確的 project-local companion Skills
- Traces: REQ-001, REQ-005, NFR-001, AC-001, AC-006, DEC-002, DEC-005
- Inputs: Current G2 approval、Node.js／npx、上游 `mattpocock/skills`、approved allowlist。
- Output: `.agents/skills/` 下新增五個完整且未修改的 companion directories；保留 installer 實際產生的 lock/provenance metadata，不出現額外 Skill。
- Verification: 列舉 `*/SKILL.md`、核對 folder/frontmatter names 與相對參考檔，執行 `npx skills list -a codex`；檢查 Git diff 只含 allowlist 與可能的 `skills-lock.json`。
- Dependencies: none

## TASK-002: 建立 DevWeave precedence 與使用文件
- Traces: REQ-002, REQ-003, REQ-004, REQ-005, NFR-002, AC-002, AC-003, AC-005, AC-006, DEC-001, DEC-003, DEC-005
- Inputs: TASK-001 的實際安裝結果、approved design、既有 `AGENTS.md` 與 README contract。
- Output: `AGENTS.md` 明定唯一 router 與 phase/write/knowledge/Git/tracker/revise 邊界；README 記錄安裝、階段 mapping、呼叫範例、驗證、rollback 與人工更新流程。
- Verification: Targeted text inspection 確認所有禁止副作用與五個 phase mappings；確認公開 verbs、CLI/schema/hook 說明未改變。
- Dependencies: TASK-001

## TASK-003: 更新 repository contract regression coverage
- Traces: REQ-001, REQ-002, REQ-004, NFR-001, NFR-002, AC-001, AC-002, AC-004, AC-005, DEC-001, DEC-004
- Inputs: TASK-001 Skill tree、TASK-002 precedence policy、既有 `tests/test_repository_contract.py`。
- Output: Contract tests 驗證精確 Skill allowlist、唯一 router、frontmatter folder identity、companion relative-link integrity 與 policy 必要邊界。
- Verification: `python -B -m unittest tests.test_repository_contract -v` 通過，且對額外／遺漏 Skill 或缺少 precedence token 的 fixture-level mutation會失敗。
- Dependencies: TASK-001, TASK-002

## 驗證策略

- Targeted：`python -B -m unittest tests.test_repository_contract -v`。
- Skill discovery：`npx skills list -a codex` 與 filesystem allowlist／relative-link 檢查。
- Regression：project configured command `python -B -m unittest discover -s tests -v`。
- Static hygiene：`git diff --check`；確認無 `CONTEXT.md`、ADR、`docs/agents/`、額外 Skill 或未規劃 Wiki diff。
- Manual acceptance：在新 Codex session 確認五個 companion Skills 可被發現；抽查 README 的 feature/design/implementation/bug 呼叫流程，且沒有第二套 lifecycle。
- Traceability：將 targeted、完整 regression 與 discovery 結果以 current source-bound evidence 對應所有 AC/TASK；G3 前重新 reconcile scope、baseline 與 knowledge status。

## 基線更新計畫

- `.devweave/baseline/product.md`：將「不提供第二套 skill」精確化為「不提供第二套 router／orchestrator」，並記錄受治理的五個 companion Skills 能力。
- `.devweave/baseline/architecture.md`：記錄唯一 router、root precedence policy、project-local Skill discovery 與 artifact/evidence 回流邊界。
- `.devweave/baseline/quality.md`：記錄 exact allowlist、relative-link、policy contract、完整 unit tests 與手動新 session discovery 驗證。
- Verification 階段執行 `knowledge status`；只有被判定 affected 或本工作明確需要提升的 Wiki page 才建立 knowledge plan，不為 placeholder warning 製造無更新理由。

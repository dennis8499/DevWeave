# 執行計畫：建立 G1/G2 互動式決策流程

<!-- DEVWEAVE:artifact=plan version=1 work=20260804-085630-feature-g1-g2 -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 強化 DevWeave router 與 G1/G2/G3 phase guidance

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, NFR-001, AC-001, AC-002, AC-003, AC-004, DEC-001, DEC-002, DEC-003, DEC-004
- Inputs: approved `brief.md`、`requirements.md`、現有 `.agents/skills/devweave/SKILL.md` 與 phase references。
- Output: router 明確啟用 G1 `grill-me`/`grilling`、G2 `codebase-design`；requirements/design/verification guidance 定義事實與決策分界、逐題等待、artifact 回流、validate 後 approval 與 `revise` 回退。
- Verification: targeted inspection、artifact/phase wording review、repository contract assertions。
- Dependencies: none

## TASK-002: 同步 repository policy 與使用文件

- Traces: REQ-003, REQ-004, REQ-005, NFR-001, AC-004, AC-005, AC-006, DEC-001, DEC-003, DEC-004
- Inputs: TASK-001 的 router/phase contract、既有 `AGENTS.md`、`README.md` 與 `docs/使用手冊.md`。
- Output: 文件一致描述 single router、companion phase mapping、G1/G2 問答、Gate Double Check、明確 approval、G2 前寫入限制與 `revise`；不變更 CLI/schema/ledger/Skill provenance。
- Verification: cross-document wording review、relative-link validation、repository contract tests。
- Dependencies: TASK-001

## TASK-003: 增加 repository contract policy tests

- Traces: REQ-004, REQ-005, NFR-001, NFR-002, AC-005, AC-006, DEC-001, DEC-002, DEC-004, DEC-005
- Inputs: TASK-001/002 的正式 wording、既有 `tests/test_repository_contract.py`。
- Output: contract tests 檢查 phase-to-Skill mapping、逐題等待與不得自行補決策、validate 後明確 approval、G2 write boundary、`revise` 與 single-router/companion precedence；測試不新增聊天 API 模擬或 engine schema。
- Verification: targeted repository contract test、完整 Python unittest。
- Dependencies: TASK-001, TASK-002

## TASK-004: 執行 standard regression 與互動式手動驗收

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, NFR-001, NFR-002, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005
- Inputs: TASK-001 至 TASK-003 完成的 policy/document/test diff、current G2 approval、既有 project verification profiles。
- Output: current passing evidence、scope/diff review、G3-ready acceptance notes；確認 no product runtime、Wiki、baseline、skills-lock 或 machine schema change。
- Verification: `extension-package`、`extension-smoke`、`extension-tests`、`extension-typecheck`、`unit-tests`、`git diff --check`，以及 G1/G2/G3 對話情境手動驗收。
- Dependencies: TASK-001, TASK-002, TASK-003

## 驗證策略

- Targeted：檢查 router、三個 phase references、AGENTS/README/使用手冊與 contract test 的互動規則一致。
- Regression：執行既有 Python unittest，包含 repository contract、CLI、guard、knowledge 與 legacy compatibility tests。
- Standard profile：透過 DevWeave CLI 執行 `extension-package`、`extension-smoke`、`extension-tests`、`extension-typecheck` 與 `unit-tests`；雖無 product runtime diff，仍遵守目前 work 的 standard profile。
- Manual：驗證 G1 material question 一次一題且等待；facts 直接查證；未核准不推進；G2 使用 `codebase-design` 並禁止提前寫入；新決策走 `revise`；G3 不靜默補需求。
- Scope/safety：`git diff --check`、完整 diff review、確認不改 `skills-lock.json`、Wiki、baseline、Python engine、schema、ledger 或 VS Code runtime。

## 基線更新計畫

不更新 `.devweave/baseline/architecture.md`、`product.md` 或 `quality.md`。本 work 改善既有治理文件與 agent interaction guidance，不改變已接受的 machine lifecycle、runtime boundary、產品目標或驗證命令；於 `acceptance.md` 記錄 no-update rationale。

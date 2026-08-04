# 需求與驗收條件：建立 G1/G2 互動式決策流程

<!-- DEVWEAVE:artifact=requirements version=1 work=20260804-085630-feature-g1-g2 -->
## 假設與限制

本需求採「關鍵決策逐題」模式：只詢問會影響使用者價值、範圍、介面、風險、相容性、驗收或回復的決策；低風險命名、檔案位置與等價 implementation detail 由 agent 選擇並在 Gate summary 列為假設。可從 Wiki、source 或已核准 artifacts 得到的 facts 不列為使用者問題。使用者可見內容與 artifacts 使用繁體中文，machine keys、CLI 與 state protocol 維持英文。

## 需求與驗收條件

## REQ-001: G1 以關鍵決策問答建立需求共識

- Priority: must
- Acceptance: AC-001, AC-002
- Description: G1 必須先完成 Wiki-first/source discovery，再使用 `grill-me`／`grilling` 逐題詢問未決的 material requirements。每題必須說明現況、agent 建議與主要取捨，等待使用者回答；回答必須回流 `brief.md` 或 `requirements.md`。已可由 repository 查證的 fact 不得轉成使用者問題。

## REQ-002: G2 以設計問答固定可實作方案

- Priority: must
- Acceptance: AC-003, AC-004
- Description: G2 必須重讀 approved G1 artifacts，使用 `codebase-design` 比較合理 design options，逐題確認會影響 interface、seam、data flow、failure mode、rollback、compatibility、observability 或 verification 的設計決策；回答必須回流 `design.md` 與 `plan.md`。G2 approval 前不得修改 product source 或 tracked tests。

## REQ-003: Gate 只接受明確的人類核准

- Priority: must
- Acceptance: AC-002, AC-004, AC-005
- Description: G1/G2 必須在對應 `validate` 通過後展示完整 Double Check summary，並等待清楚且針對目前 Gate 的 human approval。沉默、模糊同意、agent 自己的判斷或未完成的問答不得觸發 `approve`；Gate 中出現新需求或設計決策時，必須以 `revise` 回到最早受影響階段。

## REQ-004: Companion Skills 維持階段內方法與既有邊界

- Priority: must
- Acceptance: AC-003, AC-005
- Description: DevWeave 維持唯一 router；`diagnosing-bugs` 只用於 bug discovery，`tdd` 只在 current G2 approval 後對 approved task 執行。Companion Skill 的輸出只能回流既有 artifacts/evidence，不得建立第二 lifecycle、直接操作 machine ledger 或繞過 Gate。

## REQ-005: 政策與使用文件保持一致

- Priority: must
- Acceptance: AC-005
- Description: `.agents/skills/devweave/` guidance、`AGENTS.md`、`README.md`、`docs/使用手冊.md` 必須以一致的繁體中文描述事實查證、逐題問答、artifact 回流、Gate Double Check、approval 與 `revise` 行為。

## NFR-001: 維持 machine contract 與相容性

- Priority: must
- Acceptance: AC-006
- Description: 不新增 CLI、JSON/JSONL schema、ledger 欄位、pending-question state、public API、VS Code UI 或新的 lifecycle；既有 `devweave.py` gate/status/validate/approve/revise contract、Wiki policy、companion files 與 `skills-lock.json` 保持相容。

## NFR-002: 政策變更可被 repository contract 驗證

- Priority: must
- Acceptance: AC-005, AC-006
- Description: Contract tests 必須檢查唯一 router、正確 phase-to-Skill mapping、逐題等待規則、不得自行補決策、validate 後明確 approval、G2 前寫入限制與 `revise` 邊界；完整 Python suite 與 `git diff --check` 必須通過。

## AC-001: G1 只詢問未決的 material decision

- Requirement: REQ-001
- Scenario: Given G1 已完成 Wiki/source discovery，When 存在會影響目標、範圍、驗收或風險的未決選擇，Then agent 一次提出一題、附推薦與取捨並等待回答；When fact 可由 repository 查證，Then agent 直接查證而不詢問使用者。

## AC-002: G1 回答回流並在 Gate 等待核准

- Requirement: REQ-001, REQ-003
- Scenario: Given 使用者回答 G1 問題，When agent 更新 `brief.md`／`requirements.md` 並通過 `validate --gate scope`，Then agent 展示問題、範圍、非目標、驗收、假設與 waivers，且在收到明確 G1 approval 前不執行 `approve` 或進入 G2。

## AC-003: G2 使用 codebase-design 並禁止提前實作

- Requirement: REQ-002, REQ-004
- Scenario: Given current G1 approval，When G2 遇到多個合理設計方案，Then agent 使用 `codebase-design` 說明 interface/seam、選項與取捨並逐題等待回答；When G2 尚未明確核准，Then 不得修改 product source 或 tracked tests，也不得啟用 TDD implementation loop。

## AC-004: G2 Double Check 與變更回退

- Requirement: REQ-002, REQ-003
- Scenario: Given G2 artifacts 已完成且 `validate --gate build` 通過，When agent 展示選定/淘汰方案、介面、資料流、失敗處理、rollback、verification 與 residual risk，Then 等待明確 G2 approval；When 使用者或 Gate 發現新 requirement/design/scope/task，Then 使用 `revise` 回到最早受影響 phase，不得靜默改寫 approved decision。

## AC-005: 文件與 contract policy 一致

- Requirement: REQ-003, REQ-004, REQ-005, NFR-002
- Scenario: Given 修改後的 router、phase references、root policy、README、使用手冊與 contract test，When 檢查 repository contract，Then 所有文件都保留 DevWeave single-router、phase mapping、逐題等待、Gate approval、G2 write boundary 與 revise 規則，且測試能偵測缺漏。

## AC-006: 不改變既有 machine/runtime contract

- Requirement: NFR-001, NFR-002
- Scenario: Given 本 work 的 scope 只包含政策文件與 contract test，When 執行完整 Python unittest 與 `git diff --check`，Then 測試通過、沒有新增 CLI/schema/ledger/UI/runtime 行為，且既有 companion provenance 與 `skills-lock.json` 未被修改。

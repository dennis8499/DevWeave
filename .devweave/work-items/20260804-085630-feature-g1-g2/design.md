# 系統設計：建立 G1/G2 互動式決策流程

<!-- DEVWEAVE:artifact=design version=1 work=20260804-085630-feature-g1-g2 -->

## 設計摘要

選定「聊天層 policy composition」方案：由 DevWeave router 與 phase references 定義事實查證、關鍵決策問答、artifact 回流與 Gate Double Check；Python engine 仍只負責既有 lifecycle、fingerprint、validation 與 approval state。核心不變量如下：

- DevWeave 是唯一 router；companion Skills 只提供階段內方法。
- 可由 repository 查證的 fact 不詢問使用者；material decision 一次只問一題並等待回答。
- 使用者回答只回流既有 `brief.md`、`requirements.md`、`design.md` 與 `plan.md`，不新增 conversation ledger。
- G1/G2 必須在 validate 後等待明確 human approval；未核准不得推進或修改 product/test scope。
- 新需求或設計決策透過 `revise` 回到最早受影響 phase。

## 選項比較

### Option A：phase-specific policy guidance（選定）

在 router 建立共通原則，再由 requirements/design/verification references 定義各階段問題邊界與 Gate summary。沿用既有 Skills、CLI、artifacts 與 gate fingerprints；可由 contract tests 驗證文件契約。

### Option B：新增 engine pending-question state

將問題、答案與等待狀態加入 Python engine、state schema 與 CLI。此方案能提供 machine enforcement，但會新增 schema、ledger、migration、session binding 與 approval protocol，超出本 work 的政策＋測試 scope，也無法保存完整自然語言對話而不擴大資料模型。

### Option C：修改 Companion Skill 或 Extension UI

修改 `grilling` upstream copy 或增加 VS Code pending-question UI。此方案會改變 companion provenance 或 Extension public surface，且無法取代 Codex Chat 的真正問答；既有 `grilling` 已提供一次一題與等待回覆方法，因此不採用。

## 介面與資料流

### Module、interface 與 seam

本 work 的 module 是 DevWeave phase router；其 interface 是目前 work item 的 phase、approved artifacts、user response 與 Gate approval 的聊天協定。phase references 是外部 seam，`brief/requirements/design/plan` 是 durable output；`devweave.py` engine 是既有 approval adapter，不新增 public API。

### 主要資料流

1. Router 讀取 `status`／`instructions`，依 phase 載入唯一 reference。
2. G1 先完成 Wiki-first/source fact discovery，再由 `grill-me`／`grilling` 逐題確認 material requirements，答案回流 brief/requirements。
3. G1 執行 `validate --gate scope`，展示問題、範圍、非目標、AC、假設與 waivers，等待明確 approval。
4. G2 重讀 approved G1 artifacts，使用 `codebase-design` 比較設計取捨，答案回流 design/plan。
5. G2 執行 `validate --gate build`，展示選定/淘汰方案、介面、資料流、failure/rollback、verification 與 residual risk，等待明確 approval。
6. G3 只驗證實作與 approved artifacts 的一致性；新決策轉成 `revise`，不在 G3 靜默補決策。

公共 `$devweave` intents、CLI JSON envelope、state schema、gate names、companion hashes 與既有 artifact paths 不變。低風險 implementation detail 可由 agent 決定，但必須在 Gate summary 列為 assumption。

## 失敗模式與回復

- 未決 material question 或使用者尚未回答：停止當前 phase，不產生推定答案，不執行後續 Gate/implementation。
- 使用者回答含糊或與既有 requirement 衝突：以一題窄化問題澄清，必要時更新 artifact 並重新 validate。
- 使用者改變已記錄的決策：使用 `revise` 使受影響 Gate/evidence stale，從 requirements/design/implementation 的最早 phase 重走。
- `validate` 失敗、Wiki/source fingerprint stale 或 hook 未確認：回報具體 blocker，保留現有 artifacts，不宣稱 Gate 或 guard 已生效。
- 既有 CLI/schema/runtime 行為不變；rollback 是 revert 本 work 的 policy/document/test diff，不需要 migration 或 state conversion。

觀測依賴既有 artifact fingerprints、gate events、contract test results、manual acceptance notes 與 G3 diff reconciliation；不新增 production instrumentation。

## 高風險分析

本 work risk 為 standard，不涉及資料 migration、runtime security boundary、production performance 或 product API compatibility。仍保留 policy rollback、existing schema compatibility、G2 write guard、Wiki read-only 與完整 standard verification；若 implementation 發現需要 engine/schema/UI 變更，必須先 revise scope/design，而非擴張本 work。

## 設計決策

## DEC-001: 以 phase guidance 作為互動問答的 seam

- Requirements: REQ-001, REQ-002, REQ-003, NFR-001
- Decision: 在 `devweave/SKILL.md` 與 G1/G2/G3 references 定義問答與 Gate policy；不新增 engine pending-question state、CLI 或 Extension UI。
- Rationale: 問題是 agent 的 conversational behavior contract；既有 engine 已能驗證 Gate currentness 與 G2 write boundary，新增 state 不會可靠地記錄自然語言問答，且會擴大相容性成本。
- Consequences: 保留既有 machine contract 與低風險 rollback；問答遵守度需以 policy contract tests 與手動情境驗收，不能完全由 engine 強制。

## DEC-002: 關鍵決策逐題確認，低風險細節由 agent 處理

- Requirements: REQ-001, REQ-002, REQ-004
- Decision: 只詢問影響目標、範圍、介面、風險、相容性、驗收或回復的 decision；每次一題，附推薦與取捨並等待回答。
- Rationale: 保留使用者對真正產品/設計決策的控制，同時避免把可由 source 查證的 facts 或等價 implementation detail 變成冗長問卷。
- Consequences: 低風險選擇需在 artifact/Gate summary 列為假設；若後續發現它其實影響 approved decision，透過 `revise` 回退。

## DEC-003: 使用既有 artifacts 作為答案與 Gate 的唯一 durable output

- Requirements: REQ-001, REQ-002, REQ-003, REQ-005
- Decision: G1 答案寫入 `brief.md`/`requirements.md`，G2 答案寫入 `design.md`/`plan.md`；不建立 `CONTEXT.md`、question ledger 或第二份 spec。
- Rationale: 符合 repository policy 的 artifact ownership、fingerprint 與 gate validation；對話本身不需要新增 machine schema。
- Consequences: G1/G2 summary 必須列出已回答決策、假設、未決 gap 與對應 artifact；文件內容變更會自然使相關 Gate stale。

## DEC-004: Gate Double Check 是核准邊界，不是重新發明需求的階段

- Requirements: REQ-003, REQ-004, NFR-002
- Decision: 只有在 validate 通過後展示完整摘要並取得明確 human approval 才呼叫 `approve`；Gate 發現新 decision 時 `revise`，不自行選擇。
- Rationale: 將探索/決策、正式核准與實作驗證分責，避免「Gate 已通過」掩蓋未確認的假設。
- Consequences: 沉默、模糊回覆或未完成問答會停住流程；G3 只比對 current source-bound evidence 與 approved intent。

## DEC-005: 以文件契約測試與手動情境驗收互動規則

- Requirements: REQ-004, REQ-005, NFR-001, NFR-002
- Decision: 在既有 `test_repository_contract.py` 增加 policy fragment/phase mapping checks，並以 G1/G2/G3 對話情境做人工 acceptance；不改 engine 實作測試以模擬不存在的聊天 API。
- Rationale: 靜態測試能防止政策回退，手動情境才能觀察 agent 是否真的逐題等待與拒絕自動 approval。
- Consequences: 完整 Python/standard verification 保持 regression coverage；G3 acceptance 必須明確記錄 manual limitations。

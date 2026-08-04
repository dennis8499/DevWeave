# 需求與驗收條件：高風險 G3 獨立 Review Agent

<!-- DEVWEAVE:artifact=requirements version=1 work=20260804-122803-feature-g3-review-agent -->

## 假設與限制

本 Work Item 已確認的 material decisions：

- 只在 high-risk G3 啟動一個 reviewer。
- reviewer 使用 isolated context，不帶入主 Agent 推理與結論，且只能唯讀。
- reviewer unavailable、timeout 或 malformed output 形成 warning，不直接阻擋 G3。
- advisory finding 形成 warning；critical security、data-loss、不可回復性或 scope finding 阻擋 G3，僅允許明確窄幅 `review-critical` waiver。
- evidence 保存摘要、AC/TASK coverage、opaque reviewer provenance、source fingerprint、report hash 與 cache raw report。
- source fingerprint 改變會使 review stale，必須重新執行；不使用 stale review。
- Python engine 不 spawn Agent；Codex/router orchestration layer 負責一次呼叫，engine 負責 record/validate。
- Extension 只投影 review readiness，不執行 Agent、engine、shell、Git、network 或 workspace mutation。

## 需求與驗收條件

## REQ-001: High-risk G3 自動觸發獨立 reviewer
- Priority: must
- Acceptance: AC-001, AC-002
- Description: 當 Work Item risk 為 `high` 且進入 G3 verification/acceptance_review 的 final review sequence 時，唯一 DevWeave router 必須啟動恰好一個 isolated、read-only Review Agent；standard/low-risk Work Item 不得啟動此 reviewer。

## REQ-002: Reviewer context 與安全邊界
- Priority: must
- Acceptance: AC-003, AC-004
- Description: Reviewer 必須在不繼承主 Agent 推理與結論的 context 中運作，只能讀取核准 brief/requirements/design/plan、完整 diff、risk analysis、scope、baseline、Wiki 與 current evidence；不得修改 source、Wiki、ledger，不得 approve/revise/close。

## REQ-003: Review result 與可追溯 evidence
- Priority: must
- Acceptance: AC-005, AC-006
- Description: Reviewer 必須回傳可解析的 `passed`、`unavailable` 或 `critical` result、findings、AC/TASK coverage、source fingerprint 與建議；machine-only `review record` 必須由 engine 產生 `kind: review` evidence，保存摘要、opaque reviewer provenance、report hash 與 bounded raw report cache。

## REQ-004: Warning 與 critical finding gate 行為
- Priority: must
- Acceptance: AC-007, AC-008
- Description: unavailable、timeout、malformed output 與 advisory findings 必須呈現 G3 warning 且不阻擋人工核准；critical security、data-loss、不可回復性或 scope finding 必須阻擋 G3，只有明確、具名、窄幅的 `review-critical` waiver 可解除 blocker。

## REQ-005: Source-bound freshness
- Priority: must
- Acceptance: AC-009
- Description: Review evidence 必須綁定目前 product source fingerprint；產品 source 改變後 review 必須標記 stale、使 acceptance review 失效並要求重新審查，不能以 stale review 滿足 current review 狀態。

## REQ-006: G3 artifact 與文件契約同步
- Priority: must
- Acceptance: AC-010
- Description: `acceptance.md`、SKILL、phase reference、contracts、AGENTS、README、使用手冊與 accepted baseline 必須一致描述 high-risk reviewer、result/warning/critical policy、human G3 approval、G2 Design It Twice 差異與 single-router boundary。

## REQ-007: Control Center readiness projection
- Priority: must
- Acceptance: AC-011, AC-012
- Description: VS Code Control Center 必須在 high-risk acceptance gate 顯示 Independent Review check；missing/unavailable/advisory 為 attention，critical finding 為 not-ready，且 Extension 只能提供非權威 snapshot guidance。

## NFR-001: Legacy 與介面相容性
- Priority: must
- Acceptance: AC-013
- Description: 既有 evidence、legacy work item、既有公開 `$devweave` chat surface 與既有 G2 `Design It Twice` 行為保持相容；不新增第二套 lifecycle 或公開 chat verb。

## NFR-002: Report handling safety
- Priority: must
- Acceptance: AC-014
- Description: Review raw report 必須 bounded、repo-relative、具 report hash、secret redaction 與 cache path containment；Agent 不得直接寫入 engine-owned JSON/JSONL ledger。

## NFR-003: Deterministic validation
- Priority: must
- Acceptance: AC-015
- Description: 相同 work state、source fingerprint 與 review record 應產生 deterministic engine validation；Agent orchestration 不得被 Python runtime、Extension runtime 或 verification command 隱式重複執行。

## AC-001: High-risk 工作只啟動一次 reviewer
- Requirement: REQ-001
- Scenario: Given high-risk Work Item 已完成 final source/Wiki/baseline/evidence preparation When router 進入 G3 Review Then exactly one isolated reviewer is requested before the G3 summary。

## AC-002: 一般風險不啟動 reviewer
- Requirement: REQ-001
- Scenario: Given standard 或 low-risk Work Item When 進入 G3 Then workflow 不建立 reviewer attempt，也不增加 review requirement。

## AC-003: Reviewer 不繼承主 Agent 結論
- Requirement: REQ-002
- Scenario: Given 主 Agent 已整理 implementation 結論 When reviewer 啟動 Then reviewer context 不包含主 Agent reasoning，且 prompt 僅提供核准 artifacts、scope、diff 與 output contract。

## AC-004: Reviewer 維持唯讀邊界
- Requirement: REQ-002
- Scenario: Given reviewer 執行期間 When 檢查 workspace、Wiki、ledger 與 public gate commands Then reviewer 不產生 source/Wiki/ledger mutation，也不執行 approve、revise 或 close。

## AC-005: Review result 可解析
- Requirement: REQ-003
- Scenario: Given reviewer 回覆 passed、unavailable 或 critical envelope When router record review Then engine 接受合法 result、findings、coverage、fingerprint 與建議並回傳 JSON evidence。

## AC-006: Raw report 與 provenance 可追溯
- Requirement: REQ-003
- Scenario: Given review record 已寫入 When maintainer 查看 evidence Then 可看到摘要、opaque reviewer ID、context mode、report hash、source fingerprint 與 repo-relative raw report path。

## AC-007: Unavailable/advisory 只形成 warning
- Requirement: REQ-004
- Scenario: Given reviewer timeout、spawn failure、malformed output 或只回報 advisory finding When validate G3 Then validation `ok` 保持 true 並列出 warning，G3 仍等待人類明確 approval。

## AC-008: Critical finding 阻擋 G3
- Requirement: REQ-004
- Scenario: Given current review record 包含 critical security、data-loss、不可回復性或 scope finding When validate acceptance Then validation errors 包含 blocker；只有具名窄幅 `review-critical` waiver 可使其轉為 warning。

## AC-009: Source change invalidates review
- Requirement: REQ-005
- Scenario: Given current review evidence 已記錄 When product source fingerprint 改變 Then evidence/gate 被標記 stale、current review 不成立，必須重新 record reviewer result。

## AC-010: 文件與 G3 artifact 一致
- Requirement: REQ-006
- Scenario: Given repository contract tests 與 G3 acceptance When 檢查 high-risk reviewer policy Then phase reference、CLI contract、acceptance matrix、baseline 與 user-facing docs 對 trigger、result、warning、critical、human approval 與 single-router boundary 一致。

## AC-011: Control Center 顯示 reviewer readiness
- Requirement: REQ-007
- Scenario: Given high-risk acceptance snapshot When reviewer missing/unavailable/advisory/critical Then readiness 分別呈現 attention 或 not-ready，並提供回 Codex Chat 的下一步說明。

## AC-012: Extension 不執行 workflow mutation
- Requirement: REQ-007
- Scenario: Given Control Center 顯示 Independent Review When 使用者互動 Then Extension 只讀取與投影 evidence，不呼叫 Agent、engine、shell、Git、network 或 workspace write seam。

## AC-013: Existing behavior remains compatible
- Requirement: NFR-001
- Scenario: Given legacy evidence/work item、既有 public chat commands 或 G2 Design It Twice When 執行既有 tests Then 不要求 retrospective migration、不新增 chat verb，且原有行為保持通過。

## AC-014: Raw report safety checks
- Requirement: NFR-002
- Scenario: Given oversized、repo-outside、secret-bearing 或 malformed report When record review Then engine bounded/redacts/rejects safely，且不直接覆寫 JSON/JSONL ledger。

## AC-015: Validation is deterministic
- Requirement: NFR-003
- Scenario: Given identical state、source fingerprint、evidence 與 review record When repeated validate/status Then errors、warnings、trace 與 projected review result deterministic，且不重複啟動 reviewer。

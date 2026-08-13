# 需求與驗收條件：強化 DevWeave VS Code Extension 治理、驗證與效率

<!-- DEVWEAVE:artifact=requirements version=1 work=20260813-142228-feature-devweave-vs-code-extension -->
## 假設與限制

本工作以 Windows/VS Code Extension 0.2.3、目前 source-derived bootstrap bundle 與 accepted DevWeave lifecycle 為相容基線。Extension 不取得 Codex host session usage，因此 exact token/cost 欄位為 optional；若不可用，必須回報 unavailable。Wiki 於 G1/G2/implementation read-only，只有 G3 declared knowledge plan 可以更新。

## 需求與驗收條件

## REQ-001: Bootstrap path kind 必須可辨識
- Priority: must
- Acceptance: AC-001
- Description: Bootstrap completeness 必須區分 missing、file、directory、other；預期目錄被同名檔案或不相容 path 取代時，不得回報 complete，並提供可操作 conflict reason。

## REQ-002: Extension readiness 必須區分 projection 與 engine
- Priority: must
- Acceptance: AC-002
- Description: WorkspaceSnapshot 與 UI 必須明確標示 filesystem projection 非 authoritative；只有存在明確 engine observation 時才可顯示 engine Gate 狀態，snapshot 預檢不得被呈現為 Gate 通過。

## REQ-003: Work Item snapshot 必須以 summary-first 讀取
- Priority: should
- Acceptance: AC-003
- Description: Dashboard 初次刷新只讀 Work Item metadata；tasks、evidence、events、raw logs 在選取 Work Item 或明確請求 detail 時才讀取，且有單項與總量上限。

## REQ-004: Wiki projection 必須可追溯且對錯誤格式有診斷
- Priority: must
- Acceptance: AC-004
- Description: Wiki search/result 必須保留 source path、content hash、source fingerprint、stale reason 與 truncation/parse diagnostic；unsupported frontmatter 不得靜默當成正確資料。

## REQ-005: Build/package 必須具備來源 provenance
- Priority: must
- Acceptance: AC-005
- Description: generated bootstrap manifest 與 VSIX verification 必須確認 package version、source revision、manifest hash、bootstrap file count、VSIX entry count 一致；package 必須先寫入 candidate artifact，只有 verifier 成功後才原子替換 current VSIX，任何 provenance/verification failure 都不得覆寫既有 current 或 retained artifact，舊 generated output 不得被誤當成目前 build。

## REQ-006: Smoke 必須固定 runtime 且無靜默 fallback
- Priority: must
- Acceptance: AC-006
- Description: canonical smoke gate 必須固定 accepted VS Code 1.131.0；缺少 runtime/cache 時明確失敗，不能自動改測其它版本或依賴網路 fallback。

## REQ-007: Verification 必須依 scope/impact 選擇
- Priority: must
- Acceptance: AC-007
- Description: DevWeave engine/CLI 與 project command schema 必須能描述 affected paths、writes、outputs、dependencies 與 releaseOnly，並依 scope/impact 選擇 verification；low/standard 不得無條件封裝 VSIX，high/release 仍執行完整驗證。

## REQ-008: Metrics 必須透過既有 evidence 管線紀錄
- Priority: should
- Acceptance: AC-008
- Description: DevWeave engine/CLI verification/evidence contract 必須能記錄 context bytes/chars/pages、tool call counts、verification count/latency/cache 與可用時的 token/cost usage；不可用欄位必須標示 unavailable，不得偽造精確值。

## REQ-009: 初始化後必須清楚表達 operational readiness
- Priority: should
- Acceptance: AC-009
- Description: 若 fresh bootstrap 的 verification commands 為空，Dashboard 必須顯示結構完成但尚未具備可驗證流程，並提供只讀 setup handoff，不直接執行或寫入 command。

## REQ-010: 高風險 review 必須保持單一 reviewer 與雙軸輸出
- Priority: must
- Acceptance: AC-010
- Description: high-risk G3 仍只能有一個隔離 read-only reviewer；其報告分開呈現 specification/scope 與 engineering/standards findings，critical finding 仍依既有 waiver 規則阻擋。

## NFR-001: 安全與治理邊界
- Priority: must
- Acceptance: AC-011
- Description: Extension runtime 不新增 process、network、Git、Codex API、外部寫入或第二套 lifecycle；bootstrap 仍只寫入缺失項目並可 rollback。

## NFR-002: 正確性與可重現性
- Priority: must
- Acceptance: AC-012
- Description: clean build/package、pinned smoke、source fingerprint、baseline、README、evidence 與 Wiki promotion 結果必須可互相追溯，且不產生 false-positive readiness。

## NFR-003: 效率目標
- Priority: should
- Acceptance: AC-013
- Description: 以目前測量值建立 baseline；目標是 low-risk 平均驗證時間降低至少 30%、重複 context bytes 降低至少 25%、snapshot refresh latency 降低至少 30%，high-risk coverage 不降低。

## AC-001: Path kind regression
- Requirement: REQ-001
- Scenario: Given manifest 期待 directory，When workspace 放置同名 regular file，Then completeness 為 incomplete/conflict 並指出 kind mismatch；file、directory、missing 與 symlink adapter case 均有測試。

## AC-002: Authority-safe readiness
- Requirement: REQ-002
- Scenario: Given snapshot source=filesystem 且 authoritative=false，When Dashboard 顯示 readiness，Then UI 使用 projection/precheck 語意，不顯示 engine Gate passed；只有明確 engine observation 才能顯示 engine 狀態。

## AC-003: Summary-first snapshot
- Requirement: REQ-003
- Scenario: Given 多個 closed Work Items 與大型 evidence，When Dashboard 初次 refresh，Then 只讀 bounded metadata；When 使用者選取一個 Work Item，Then 才讀取其 bounded detail，且結果可正確刷新。

## AC-004: Wiki traceability
- Requirement: REQ-004
- Scenario: Given stale page、invalid frontmatter 或 truncated text，When Wiki search/index projection 執行，Then 回傳 path/hash/stale 或 parse diagnostic，不把不完整資料當成無錯結果。

## AC-005: Reproducible package
- Requirement: REQ-005
- Scenario: Given stale dist，When clean build/package/verify 執行，Then dist 先被重建，manifest/package/source revision/VSIX counts 一致，candidate VSIX 通過 verifier 後才原子替換 current artifact；version/provenance drift 或 verifier failure 產生明確失敗訊息並保留既有 current/retained VSIX。

## AC-006: Pinned smoke
- Requirement: REQ-006
- Scenario: Given canonical runtime cache 缺失，When smoke gate 執行，Then command 失敗並指出需安裝/快取 1.131.0，不下載或 fallback 到 1.133.0。

## AC-007: Impact-based verification
- Requirement: REQ-007
- Scenario: Given 只修改 Wiki 或單一不涉及 package 的 Extension unit seam，When low/standard profile 選擇 commands，Then 不執行無關 package；high profile 仍包含完整 package、smoke、Python suites。

## AC-008: Metrics availability
- Requirement: REQ-008
- Scenario: Given 一次 workflow/verification，When evidence 產生，Then 可查到 context/tool/verification metrics；host usage 未提供時欄位為 unavailable 且 proxy 與 exact usage 分開。

## AC-009: Bootstrap readiness
- Requirement: REQ-009
- Scenario: Given fresh initialization 的 commands 為空，When Dashboard refresh，Then 顯示 setup required 並提供可複製 handoff，不能由 Extension 自動執行 command set。

## AC-010: Single reviewer dual axis
- Requirement: REQ-010
- Scenario: Given high-risk G3，When final review 啟動，Then 只有一個 isolated read-only reviewer，結果含 spec/standards 分區，critical finding 依既有 acceptance/waiver 規則處理。

## AC-011: Security boundary regression
- Requirement: NFR-001
- Scenario: Given 正常 refresh、preview、copy、initialize、open file 與 error paths，When Extension tests 執行，Then 沒有新增 process/network/Codex API/direct arbitrary write，bootstrap rollback/security tests 維持通過。

## AC-012: Evidence reconciliation
- Requirement: NFR-002
- Scenario: Given clean source and generated output，When full high verification completes，Then docs/baseline/evidence/Wiki review 的 version、test count、source fingerprint、scope diff 可互相追溯且 G3 validate 通過。

## AC-013: Efficiency benchmark
- Requirement: NFR-003
- Scenario: Given 固定代表性 feature/bug/refactor/bootstrap tasks，When baseline 與改版使用同一套 commands/evals，Then metrics 顯示上述改善目標或以 evidence 記錄未達成原因，不犧牲 correctness/security。

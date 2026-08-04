# 需求與驗收條件：改善 DevWeave Control Center UX 與使用者導引

<!-- DEVWEAVE:artifact=requirements version=1 work=20260803-215202-feature-devweave-control-center-ux -->

## 假設與限制

- 使用者同時包含新手、日常開發者與 reviewer；預設以新手可理解為先，詳細治理資訊可展開。
- Extension 仍是 filesystem projection；engine 與 Codex Chat 是 authoritative workflow surface。
- `PublicCommandIntent`、`parsePublicCommandIntent`、`PromptBundle.chatText`、既有 nine public commands、BootstrapInstaller 與 security boundary 必須相容。
- 本 work 的所有 tracked product/test/doc changes 限於 `vscode-extension/**`；既有 dirty VSIX 不得被覆寫。

## 需求與驗收條件

## REQ-001: 總覽優先的資訊架構
- Priority: must
- Acceptance: AC-001
- Description: Dashboard 預設必須先顯示 workspace state、snapshot provenance、目前 work 或無 active work 的 onboarding、snapshot guidance、blocker 與主要 CTA；完整 artifacts、Wiki、verification 與 audit 不得全部在首次畫面展開。

## REQ-002: 四個可理解的內容區域
- Priority: must
- Acceptance: AC-002
- Description: Extension 必須提供 `總覽`、`工作項目`、`知識`、`驗證與稽核` 四個區域；每個區域都要有繁體中文標題與簡短說明，進階術語保留在次要內容。

## REQ-003: 任務導向 command presentation
- Priority: must
- Acceptance: AC-003
- Description: 命令選擇必須以開始工作、查看進度、審查決策、建立知識分組，並提供任務語言 label、用途 helper 與對應 public command；原有 public intent 與 prompt text 不變。

## REQ-004: Active work 與 closed history 分離
- Priority: must
- Acceptance: AC-004
- Description: Work selector/sidebar 必須將 active work 與 closed history 分組；零 active work 時顯示開始新工作 CTA，closed work 只能作為歷史瀏覽，不得被誤呈現為目前工作。

## REQ-005: 誠實的 snapshot provenance
- Priority: must
- Acceptance: AC-005
- Description: UI 必須清楚標示 filesystem snapshot 非 engine authoritative state；不得以 snapshot capture time 與 work `updated_at` 的單純比較產生無 source-drift 證據的 freshness warning。

## REQ-006: Snapshot guidance 與 authoritative next handoff
- Priority: must
- Acceptance: AC-006
- Description: UI 的本地下一步必須標示為 snapshot guidance，並提供 `$devweave next [work-id]` 的 preview/copy handoff；不得宣稱 Extension 自行判定 engine current next action。

## REQ-007: Bootstrap 與 prompt handoff 差異
- Priority: must
- Acceptance: AC-007
- Description: 初始化 UI 必須清楚說明它是使用者確認後的 direct bootstrap write；其他 command 必須清楚說明只會複製 prompt 到 Codex Chat。Bootstrap 成功或失敗後必須提供下一個可行動步驟。

## REQ-008: Reviewer readiness summary
- Priority: must
- Acceptance: AC-008
- Description: Work detail 必須摘要目前 gate、可審查狀態、blocker、failed/stale evidence、未完成 task、Wiki pending refresh、baseline targets 與 approve/revise 效果；不要求 reviewer 先讀 raw event log。

## REQ-009: Actionable tasks、evidence 與 Knowledge
- Priority: must
- Acceptance: AC-009
- Description: Task/evidence/Knowledge projection 必須顯示人可理解的狀態、原因、受影響路徑與下一步；不能只提供 raw status 或 aggregate count。

## REQ-010: 可讀 diagnostics 與 audit timeline
- Priority: should
- Acceptance: AC-010
- Description: Diagnostics 必須先提供繁體中文問題與修復建議，technical code/path 放進可展開細節；audit 必須以 timestamp/事件/結果的 timeline 呈現並保留 raw event text。

## REQ-011: Prompt preview handoff 說明
- Priority: must
- Acceptance: AC-011
- Description: Preview 必須顯示操作會做什麼、不會做什麼、目前 work/gate context、copy 後要貼到 Codex Chat 送出，以及送出後要 Refresh；approve/revise 必須顯示其治理影響。

## REQ-012: Onboarding 與 verification setup guidance
- Priority: must
- Acceptance: AC-012
- Description: 未初始化、初始化完成、managed workspace 無 verification command、無 active work 等狀態都必須有下一步導引，且不得宣稱 workflow 已完全可驗證而實際 profile 為空。

## REQ-013: UI accessibility 與穩定互動
- Priority: must
- Acceptance: AC-013
- Description: UI 必須支援 keyboard focus、ARIA labels/live status、high contrast、reduced motion、窄視窗；loading/error/duplicate action 不得造成不可見失敗或重複 copy/write。

## REQ-014: 進階顯示偏好與 multi-root clarity
- Priority: could
- Acceptance: AC-014
- Description: 使用者可切換簡潔/進階顯示；偏好只存於 Extension context。Multi-root workspace 選擇器必須顯示 folder、managed 狀態與目前選取 repository。

## REQ-015: Wiki browsing scalability
- Priority: could
- Acceptance: AC-015
- Description: Knowledge area 必須提供頁面分類、搜尋或顯示全部頁面的入口，不得只截斷前 12 頁而沒有發現其餘頁面的方式。

## NFR-001: Public contract compatibility
- Priority: must
- Acceptance: AC-016
- Description: `PublicCommandIntent`、parser、prompt composer 的九個 public command output、sanitization、warning 與 mutation/read-only semantics 維持相容；不加入 machine CLI、任意 JSON intent、gate 參數或 engine write。

## NFR-002: Security and write boundary
- Priority: must
- Acceptance: AC-017
- Description: Extension runtime 不得新增 process、shell、Git、network、Codex API 或一般 workspace write path；BootstrapInstaller 的固定 manifest、confirmation、no-overwrite、conflict、rollback、CSP 與 path safety 維持通過。

## NFR-003: Presentation seam testability
- Priority: must
- Acceptance: AC-018
- Description: 新增的 command presentation、snapshot guidance、review readiness、diagnostic mapping 與 UI state rendering 必須可透過 extension-local public seam 以 deterministic unit tests 驗證，不測私有 DOM 細節。

## NFR-004: Repository compatibility and performance
- Priority: should
- Acceptance: AC-019
- Description: 既有 managed/uninitialized/legacy/malformed/closed/multi-work projection 行為維持；UI 分區與 lazy detail rendering 不得引入外部 runtime dependency 或不受界限的 repository scan。

## AC-001: 使用者先看懂 workspace 狀態
- Requirement: REQ-001
- Scenario: Given managed workspace When 開啟 Control Center Then 首屏顯示 repository state、snapshot provenance、active/empty work state、guidance 與主要 CTA，且不需要先閱讀完整 governance sections。

## AC-002: 使用者可依任務理解詳細內容
- Requirement: REQ-002
- Scenario: Given 任一 workspace When 使用者切換四個區域 Then 每區顯示對應資訊與繁體中文說明，進階內容不污染總覽。

## AC-003: 使用者以自然任務選擇 command
- Requirement: REQ-003
- Scenario: Given command composer When 使用者想新增功能、回報 bug、查看狀態或核准 gate Then 可從任務分組找到對應 command，preview 的 public prompt 與既有 contract 完全一致。

## AC-004: 無 active work 不被歷史阻塞
- Requirement: REQ-004
- Scenario: Given repository 只有 closed work When 開啟 Dashboard Then active section 顯示空狀態與開始工作 CTA，closed history 可展開瀏覽但不會被自動選為 current work。

## AC-005: Snapshot 不產生假 freshness 警告
- Requirement: REQ-005
- Scenario: Given work state 的 `updated_at` 早於當前 filesystem capture 且沒有 source drift metadata When refresh Then UI 顯示 snapshot provenance，不顯示「snapshot may be newer」類誤導警告。

## AC-006: 下一步清楚區分推導與權威
- Requirement: REQ-006
- Scenario: Given active work When 查看 guidance Then UI 標示 snapshot-based suggestion，並可 preview/copy `$devweave next <work-id>` 讓 Codex/engine 回傳權威下一步。

## AC-007: 初始化與 prompt handoff 可辨識
- Requirement: REQ-007, REQ-012
- Scenario: Given uninitialized workspace When 使用者查看或完成 initialization Then UI 清楚說明 direct write、created/adopted/conflict，並提供 setup verification/建立第一個 work 的下一步；managed workspace 的 command 則清楚標示 copy-only handoff。

## AC-008: Reviewer 不需讀 raw log 即可判斷 readiness
- Requirement: REQ-008
- Scenario: Given work item 有 pending/stale/failed evidence 或 gate When reviewer 開啟 Work/Verification area Then 可看到目前 gate、缺項、blocker 與 approve/revise effect，raw event 只作進階展開。

## AC-009: 狀態與下一步可行動
- Requirement: REQ-009
- Scenario: Given pending task、failed/stale evidence、affected Wiki page 或 pending refresh When 使用者查看 detail Then 每項顯示人話狀態、原因、相關路徑與可採取的下一步或 handoff。

## AC-010: Diagnostics 與 audit 易讀
- Requirement: REQ-010
- Scenario: Given critical/warning diagnostic and event history When 使用者查看相關區域 Then 先看到繁中摘要與修復方向，並可展開 technical code/path/raw event。

## AC-011: Prompt preview 交接完整
- Requirement: REQ-011
- Scenario: Given 任一 mutation/public command When 使用者 preview/copy Then 能看懂 will do、will not do、work/gate context、Codex Chat handoff 與 Refresh instruction；approve/revise 顯示 governance warning。

## AC-012: 空 verification profile 不被誤稱 ready
- Requirement: REQ-012
- Scenario: Given managed project commands/profiles 為空 When 使用者開啟 Control Center Then 顯示 verification setup required，並說明 G3 可能受阻，而不是只顯示 ready/healthy。

## AC-013: 鍵盤與窄視窗可用
- Requirement: REQ-013
- Scenario: Given keyboard-only、high-contrast、reduced-motion 或窄 Webview When 使用者切換區域、輸入 command、preview/copy、refresh Then focus、live status、對比與 layout 保持可用。

## AC-014: 偏好與 multi-root 清楚
- Requirement: REQ-014
- Scenario: Given user toggles concise/advanced mode or opens multi-root workspace When Extension refreshes/reopens Then preference persists in Extension context and repository choice shows managed status/current selection without writing repository state.

## AC-015: Wiki 頁面可被發現
- Requirement: REQ-015
- Scenario: Given Wiki pages more than 12 When user opens Knowledge area Then can filter/search or explicitly show all pages; no page is silently inaccessible due to fixed truncation.

## AC-016: Public prompt regression
- Requirement: NFR-001
- Scenario: Given each of nine intents When composed with existing fixtures Then `chatText`, mutation/read-only classification, warnings and redaction remain compatible with current tests.

## AC-017: Security boundary regression
- Requirement: NFR-002
- Scenario: Given source inspection and bootstrap/security fixtures When run existing security/bootstrap tests Then no new process/network/general write path appears and all existing safety tests pass.

## AC-018: Presentation seam regression
- Requirement: NFR-003
- Scenario: Given state matrix fixtures When run extension UI/presentation tests Then guidance, grouping, readiness, diagnostic mapping and empty/loading/error views produce deterministic user-observable results.

## AC-019: Full repository compatibility
- Requirement: NFR-004
- Scenario: Given existing Python and Extension verification commands When run package, smoke, typecheck, npm tests and Python suite Then all required commands pass without changing engine schema or Wiki.

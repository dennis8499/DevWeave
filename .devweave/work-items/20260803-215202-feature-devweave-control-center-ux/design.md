# 系統設計：改善 DevWeave Control Center UX 與使用者導引

<!-- DEVWEAVE:artifact=design version=1 work=20260803-215202-feature-devweave-control-center-ux -->

## 設計摘要

Extension 保持「filesystem projection + public prompt handoff + confirmed bootstrap write」三個既有 seam，不新增 engine、process、network 或一般 workspace write。新增一個 Extension-local `presentation` deep module，集中所有 UI 需要的語意轉換，讓 Webview 只處理 DOM、互動狀態與 host message。

Dashboard 改為單一 Webview 內的四個區域：`overview`、`work`、`knowledge`、`verification`。預設進入 `overview` 與 `concise` display mode；使用者可展開進階資訊或切換區域，reviewer 不必在首次畫面閱讀 raw audit。所有 authoritative workflow decision 仍透過公開 `$devweave next/status/approve/revise` prompt 交給 Codex/engine。

## 選項比較

### DEC-001: 四區域分頁加 progressive disclosure

- Requirements: REQ-001, REQ-002, REQ-008, NFR-004
- Option A：保留單一長頁，只調整順序與 CSS。
- Option B：同一 Webview 保留一個 host/protocol，但以四個區域按鈕、concise/advanced detail 與 bounded list 分隔內容。
- Decision：選 Option B。
- Rationale：不增加 Webview/host lifecycle 或 public API，卻能把 overview、work、knowledge、verification/audit 的閱讀任務分開；section state 只屬 UI，不污染 repository。
- Consequences：需要 section navigation、ARIA tab semantics、state preservation 與新的 render dispatch；詳細資料仍可由既有 snapshot 開啟。

### DEC-002: Extension-local presentation seam，不重建 engine

- Requirements: REQ-003, REQ-005, REQ-006, REQ-008, NFR-001, NFR-003
- Option A：在 Webview render functions 中繼續散落 command/status/gate 判斷。
- Option B：新增 `src/presentation.ts`，以小型純函式介面輸出 command presentation、snapshot guidance、review readiness、diagnostic copy、audit event 與 localized labels。
- Decision：選 Option B。
- Rationale：將 engine vocabulary 與 UI 文案集中，caller 只需取得小型 view model；測試可在不啟動 DOM 或 VS Code Host 的情況下驗證複雜語意。
- Consequences：需維護 projection mapping；mapping 不能被描述為 engine validation，所有 guidance/readiness 都帶有 snapshot provenance。

### DEC-003: Snapshot honesty 與 next handoff

- Requirements: REQ-005, REQ-006, REQ-011, REQ-012
- Option A：以 `capturedAt` 與 work `updated_at` 推斷 engine freshness，並在 Extension 內決定 next action。
- Option B：顯示「filesystem snapshot，非 engine 權威」，移除單純時間比較 warning；本地只產生 snapshot guidance，並把 `$devweave next [work-id]` 作為權威 handoff。
- Decision：選 Option B。
- Rationale：Extension 沒有 engine/process seam，不能證明 source fingerprint 或 gate currentness；Option B 避免 false confidence 與 false warning。
- Consequences：使用者在 Codex Chat 送出 next/status 後仍需 Refresh；UI 必須清楚解釋此交接。

### DEC-004: 任務語言 command catalog，維持 public wire contract

- Requirements: REQ-003, REQ-007, REQ-011, NFR-001
- Decision：在 `presentation.ts` 定義九個 `PublicCommandName` 的固定 catalog：group、繁中 label、technical label、description、requiresWork、mutation 與 handoff copy；`PublicCommandIntent`、parser、composer output、sanitization、warnings 不變。
- Command groups：
  - `start`：開始功能、回報問題、整理程式。
  - `progress`：查看狀態、詢問下一步。
  - `review`：修改方向、核准目前階段。
  - `knowledge`：建立 Codebase Wiki。
- `approve` 的 preview 只顯示目前 gate 與 governance effect，不加入 gate argument；`revise` 顯示可能使既有 gate/evidence 失效。

### DEC-005: Extension context preference 與 bounded browsing

- Requirements: REQ-014, REQ-015, NFR-004
- Decision：`displayMode` 儲存在 `ExtensionContext.workspaceState`；Webview 透過 typed `setDisplayMode` message 更新，repository snapshot 不增加偏好欄位。Knowledge 頁面預設最多顯示 12 頁，但提供 query/type filter 或「顯示全部」入口；query/filter 只作用於已讀 snapshot，不觸發額外 repository scan。
- Multi-root QuickPick 對每個 folder 顯示名稱、managed/unmanaged 狀態與 URI；選取後仍由既有 root resolver 建立 filesystem reader。

## 介面與資料流

### Extension-local presentation interface

`src/presentation.ts` 提供以下純函式與型別，供 host/webview/test 共用：

- `commandPresentations(): readonly CommandPresentation[]`
- `buildSnapshotGuidance(snapshot, selectedWork): SnapshotGuidance`
- `buildReviewReadiness(snapshot, work): ReviewReadiness`
- `presentDiagnostic(diagnostic): DiagnosticPresentation`
- `presentAuditEvent(raw): AuditEventPresentation`
- `presentStatus/phase/gate/risk(value): string`

核心型別：

- `DashboardSection = "overview" | "work" | "knowledge" | "verification"`
- `DisplayMode = "concise" | "advanced"`
- `DashboardPreferences = { displayMode: DisplayMode }`
- `CommandPresentation = { name, group, label, technicalLabel, description, requiresWork, mutation }`
- `SnapshotGuidance = { kind, title, detail, command?: PublicCommandName, workId?: string, authoritative: false }`
- `ReviewReadiness = { gate: GateName | null, status: "ready" | "attention" | "not_ready" | "closed", summary, checks: ReviewCheck[] }`
- `DiagnosticPresentation = { title, detail, resolution, code, path? }`
- `AuditEventPresentation = { at, event, summary, raw }`

既有 `WorkspaceSnapshot`、`WorkItemProjection`、`PublicCommandIntent` 與 `PromptBundle.chatText` 保持 engine-compatible；新增型別是 Extension UI projection，不寫回任何 machine ledger。

### Host/Webview protocol

- `HostToWebviewMessage.snapshot` 增加 optional `preferences?: DashboardPreferences`。
- `WebviewToHostMessage` 增加 `{ type: "setDisplayMode"; mode: DisplayMode }`，parser 僅接受兩個合法 mode 且拒絕 extra fields。
- `DashboardCallbacks` 增加 `getPreferences()` 與 `setDisplayMode(mode)`；controller 使用 `context.workspaceState`，不觸碰 repository。
- snapshot、preview、copy、bootstrap、error 的既有 message names 與 semantics 不變。

### Webview state

- Local state：`selectedSection`（預設 overview）、`displayMode`（由 host preference 初始化）、`selectedWorkId`、`selectedCommand`、`pendingIntent`、`wikiQuery`、`wikiType`、`showAllWikiPages`、`showAllAudit`、`busy`。
- `render()` 先保留目前 element 的 `data-focus-key`，更新 DOM 後還原同一 focus target；每個 mutation/refresh/initialize action 由單一 busy guard 防止重複送出。
- 初始 HTML 顯示 loading state；host response 或 error 解除 busy，status message 使用 `role=status`/`role=alert`。

### View composition

- `overview`：repository state、snapshot provenance、active work summary、empty/onboarding state、snapshot guidance、command launcher、bootstrap/setup notices。
- `work`：active/closed selector、gate summary、blocker、artifacts、requirements/design/plan、task state；closed work 只顯示 audit-safe detail，不能成為 revise/approve 的 implicit current work。
- `knowledge`：health、bootstrap recommendation、review status、affected/pending pages、query/type filter、bounded/all page list。
- `verification`：review readiness、commands/evidence、baseline/Wiki promotion、acceptance checks、human-readable audit timeline 與 raw event toggle。

### Data flow

1. Controller 透過 `WorkspaceSnapshotReader` 讀取 filesystem；不重算 Git/source fingerprint。
2. DashboardPanel 將 snapshot 與 workspaceState preference 送入 Webview。
3. Webview 使用 presentation functions 產生 labels/guidance/readiness，純渲染四個區域。
4. 使用者選取 public command 後，既有 `previewAction → actionPreview → copyAction → copyResult` flow 保持不變；preview 額外使用 presentation summary，不改 clipboard text。
5. `setDisplayMode` 只更新 Extension context；Refresh 只重新讀取 snapshot。
6. Bootstrap 仍由 controller 的固定 manifest installer 執行；完成結果轉為 setup/next-step notice。

## 失敗模式與回復

- Critical diagnostic：維持既有 mutation blocked；overview 先顯示人話 diagnostic 與 status handoff，technical code/path 可展開，status command 仍可用。
- Malformed/unsupported state：presentation functions 使用 fail-closed fallback，不自行修復或猜測 gate/currentness。
- Preview/copy/clipboard error：保持既有 host error message，Webview 顯示 inline alert、解除 busy、保留 selected section/work/command。
- Bootstrap conflict/error：維持 installer 的 no-overwrite/rollback；結果畫面列出 created/adopted/conflict/error 與「修正後重新整理」指引，不宣稱初始化成功。
- Invalid preference/message：protocol parser 拒絕；mode 使用 concise fallback，不修改 repository。
- 大量 Wiki/event：初次 bounded list，提供明確 show-all/search；不增加無界 filesystem scan。
- Rollback：Extension UI 變更可由移除新 bundle/回復 source；不需要資料 migration。既有 bootstrap rollback 不改動。

## 高風險分析

- Migration：不適用；不修改 Python schema、project/state/evidence/Wiki machine data。
- Security：維持 CSP、typed protocol、no process/network、prompt sanitization、bootstrap fixed manifest、path allowlist 與 no-overwrite tests；新增 preference 僅寫 `workspaceState`。
- Compatibility：public command output、BootstrapInstaller、existing snapshot fields 與 legacy projection 保持相容；新增 host message fields optional，舊 snapshot message 仍可解析。
- Performance：presentation mapping 為純記憶體運算；Reader scan 範圍不變；Wiki/event list 有界且 show-all 是明確 user action。
- Observability：保留 OutputChannel protocol/bootstrap errors；UI 只顯示 snapshot capture time 與 work updated time，不虛構 engine observation。

## 設計決策

## DEC-001: 四區域 progressive disclosure
- Requirements: REQ-001, REQ-002, REQ-008, NFR-004
- Decision: 同一 Webview 以 overview/work/knowledge/verification 分區，concise default、advanced details 可展開。
- Rationale: 降低首屏認知負擔，保留 reviewer 所需深度，不增加第二個 lifecycle。
- Consequences: 需要 typed section state、focus restoration 與新 CSS；既有 snapshot/read-only boundary 不變。

## DEC-002: Presentation deep module
- Requirements: REQ-003, REQ-008, REQ-009, REQ-010, NFR-003
- Decision: 新增純函式 `presentation.ts` 作為 command/status/readiness/diagnostic/audit 語意 seam。
- Rationale: 提高 caller leverage、測試 locality，避免 Webview render function 重複 engine vocabulary。
- Consequences: UI mapping 需跟隨既有 model；不允許把 projection 結果稱為 authoritative engine validation。

## DEC-003: Non-authoritative snapshot guidance
- Requirements: REQ-005, REQ-006, REQ-011, REQ-012
- Decision: 移除單純 timestamp freshness warning；顯示 snapshot honesty，next 以 public prompt handoff 取得 engine authority。
- Rationale: 避免 false warning/false confidence，符合 Extension no-process boundary。
- Consequences: 使用者仍需在 Codex Chat 送出 prompt 並 Refresh。

## DEC-004: Public command catalog and handoff copy
- Requirements: REQ-003, REQ-007, REQ-011, NFR-001
- Decision: command grouping/labels/purpose/will-do copy 由 presentation catalog 提供；clipboard text 與 parser 不變。
- Rationale: 讓使用者以任務理解 command，同時維持 machine/public compatibility。
- Consequences: 需更新 UI、package command titles、README 與相關 tests。

## DEC-005: Extension-owned preference and bounded knowledge browsing
- Requirements: REQ-013, REQ-014, REQ-015, NFR-004
- Decision: display mode 使用 workspaceState；Wiki query/type/show-all 只操作 snapshot；multi-root labels 顯示 managed status。
- Rationale: 提供 advanced/reviewer scalability，不把 UI metadata 污染 repository。
- Consequences: protocol 增加一個 typed preference message；需要 preference and browsing regression tests。

## DEC-006: No living baseline update in this work
- Requirements: NFR-001, NFR-002, NFR-004
- Decision: 本 work 不修改 `.devweave/baseline/*`；UX 是既有 accepted Extension capability 的 presentation refinement，不改 engine/governance truth。
- Rationale: scope 僅 `vscode-extension/**`，避免把 UI detail 當成新的 governance contract。
- Consequences: G3 acceptance 記錄 no baseline update rationale；Wiki affected pages 仍依 Knowledge Review 規則處理。

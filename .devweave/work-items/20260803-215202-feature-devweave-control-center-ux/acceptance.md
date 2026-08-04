# 功能驗收：改善 DevWeave Control Center UX 與使用者導引

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260803-215202-feature-devweave-control-center-ux -->

## 驗證矩陣

本次產品 source fingerprint 為：
`7fa9cf005809326eaa299931f21eb41db791f1b02bea8495b6721de1835882db`。

以下 current evidence 均為 `status: passed`、`stale: false`、`binds_current_source: true`。

| Acceptance | Requirement | 結果 | Current evidence | Tasks |
| --- | --- | --- | --- | --- |
| AC-001 | REQ-001 | 通過；總覽先呈現 workspace state、snapshot provenance、目前工作／空狀態、guidance 與 CTA。 | EVID-009 | TASK-003 |
| AC-002 | REQ-002 | 通過；提供總覽、工作項目、知識、驗證與稽核四個繁中區域。 | EVID-009 | TASK-003 |
| AC-003 | REQ-003 | 通過；command 以開始工作、查看進度、審查決策、建立知識分組，public prompt text 維持原 contract。 | EVID-006、EVID-009 | TASK-001、TASK-003、TASK-004、TASK-006 |
| AC-004 | REQ-004 | 通過；active work 與 closed history 分組，無 active 時提供開始新工作，closed 不會被 implicit select。 | EVID-009 | TASK-002、TASK-003 |
| AC-005 | REQ-005 | 通過；標示 filesystem snapshot 非 engine 權威，移除 timestamp freshness warning。 | EVID-009 | TASK-001、TASK-002、TASK-003 |
| AC-006 | REQ-006 | 通過；snapshot guidance 明確非權威，並提供 `$devweave next [work-id]` handoff。 | EVID-006、EVID-009 | TASK-001、TASK-003、TASK-004 |
| AC-007 | REQ-007、REQ-012 | 通過；初始化 direct write 與其他 prompt-only handoff 分開說明，bootstrap 後有 hook、verification、第一個 work 導引。 | EVID-005、EVID-009 | TASK-002、TASK-003、TASK-004、TASK-006 |
| AC-008 | REQ-008 | 通過；reviewer readiness 顯示目前 gate、blocker、task、evidence、Knowledge 與 approve/revise 效果。 | EVID-009 | TASK-001、TASK-003、TASK-004 |
| AC-009 | REQ-009 | 通過；task、failed/stale evidence 與待更新頁面提供人話狀態、原因與下一步。 | EVID-009 | TASK-001、TASK-003、TASK-004 |
| AC-010 | REQ-010 | 通過；diagnostic 先顯示修復建議，audit 以時間軸呈現並保留 raw event 展開。 | EVID-009 | TASK-001、TASK-004 |
| AC-011 | REQ-011 | 通過；preview 包含會做什麼、不會做什麼、work/gate context、Codex Chat 與 Refresh 交接。 | EVID-006、EVID-009 | TASK-004、TASK-006 |
| AC-012 | REQ-012 | 通過；空 verification profile 明確顯示需要設定，不宣稱 ready。 | EVID-005、EVID-009 | TASK-002、TASK-003、TASK-004 |
| AC-013 | REQ-013 | 自動驗證通過；ARIA/live status、focus preservation、busy/error guard、high-contrast、reduced-motion、窄視窗 CSS 已實作。實際 GUI 手動矩陣因 Computer Use native pipe 不可用，列為 residual risk。 | EVID-009 | TASK-003、TASK-004、TASK-005 |
| AC-014 | REQ-014 | 通過；concise/advanced 只存 workspaceState，multi-root 顯示 managed 狀態與 repository path。 | EVID-006、EVID-007、EVID-009 | TASK-001、TASK-002、TASK-005 |
| AC-015 | REQ-015 | 通過；Knowledge 提供搜尋、分類與顯示全部入口，初始 bounded list 不會靜默遺漏頁面。 | EVID-009 | TASK-003、TASK-005 |
| AC-016 | NFR-001 | 通過；39 個 Extension tests、17 個 CLI regression tests、typecheck、package、smoke 與 Python suite 均通過，九個 public prompt contract 未改。 | EVID-004、EVID-005、EVID-006、EVID-007、EVID-008、EVID-009 | TASK-001、TASK-004、TASK-006、TASK-007 |
| AC-017 | NFR-002 | 通過；未新增 process、shell、Git、network、Codex API 或一般 workspace write；bootstrap confirmation 與安全測試通過。 | EVID-005、EVID-006、EVID-008、EVID-009 | TASK-002、TASK-003、TASK-004、TASK-005、TASK-007 |
| AC-018 | NFR-003 | 通過；presentation、selection、protocol 與 source contract 皆由 Extension-local seam 測試。 | EVID-006、EVID-007、EVID-009 | TASK-001、TASK-003、TASK-004、TASK-007 |
| AC-019 | NFR-004 | 通過；managed、uninitialized、legacy、malformed、closed、multi-work projection 維持相容，full regression 83/83。 | EVID-004、EVID-005、EVID-007、EVID-008、EVID-009 | TASK-003、TASK-005、TASK-007 |

## Profile 證據

本 work item 是 `feature`，已完成 profile 所需的 acceptance + regression：

| Evidence | Kind | 執行結果 |
| --- | --- | --- |
| EVID-004 | `acceptance` | `extension-package` exit code 0；production bundle 成功。 |
| EVID-005 | `acceptance` | `extension-smoke` exit code 0；VS Code Extension Host activation/view smoke 成功。 |
| EVID-006 | `regression` | `extension-tests` exit code 0；17 個 parser、snapshot、prompt、security tests 通過。 |
| EVID-007 | `regression` | `extension-typecheck` exit code 0。 |
| EVID-008 | `regression` | `unit-tests` exit code 0；Python 83/83 通過。 |
| EVID-009 | `acceptance` | presentation／state／protocol／source contract acceptance matrix 通過，涵蓋 AC-001～AC-015。 |

較早建立但仍 current/passed 的證據也納入本次驗收覆蓋：

| Evidence | Kind | 執行結果 |
| --- | --- | --- |
| EVID-001 | `test` | Extension unit/security regression；npm test 39/39 與 typecheck 通過，涵蓋 AC-016～AC-019。 |
| EVID-002 | `build` | Production package 與 VS Code Extension Host smoke 通過，涵蓋 AC-016～AC-017。 |
| EVID-003 | `regression` | Python full repository regression 83/83 通過，涵蓋 AC-016、AC-017、AC-019。 |

另有直接執行的 Extension npm test 39/39、`git diff --check` 與完整 Python 83/83 結果；CLI verify evidence 為 G3 的正式 evidence。

## 基線更新

未更新 `.devweave/baseline/`。已透過 DevWeave CLI 記錄空 targets：

本次只改善 Extension presentation、Webview accessibility、public prompt handoff 與 Extension workspaceState display preference，未改變 Python engine、gates、evidence、baseline schema 或治理規則，因此不更新 living baseline。

沒有 declared baseline target，也沒有未宣告的 baseline diff。

## Wiki 知識提升

Knowledge Review 已由 CLI 記錄為 `promote`；review change fingerprint 為產品 source fingerprint：
`7fa9cf005809326eaa299931f21eb41db791f1b02bea8495b6721de1835882db`。

- rationale：本次 Extension UX 變更產生可重用的 presentation boundary、public prompt handoff、workspaceState preference、active/closed selection 與 bounded Wiki browsing 知識；既有 source-bound 頁面需 refresh，不新增 engine schema 或額外內容頁。
- affected pages：`wiki/overview.md`、`wiki/modules/knowledge-engine.md`。
- promote upserts：上述兩頁；沒有 delete。
- coupled pages：`wiki/index.md`、`wiki/log.md`。
- 四頁均已以 `knowledge seal` seal；沒有 scaffold placeholder、template token、critical lint 或 stale warning。
- verification 後 `knowledge status`：`health: healthy`、`bootstrap.complete: true`、`pending_refresh: []`、`uncovered_changed_paths: []`、`warnings: []`。
- Wiki knowledge fingerprint 在 promotion 後更新，但產品 evidence 仍綁定同一個 current product source fingerprint。

## 殘餘風險

沒有 waiver、critical blocker 或 out-of-scope product change。已知限制如下：

1. Computer Use native pipe 無法連線，因此尚未完成實際 VS Code Webview 的 keyboard-only、focus、high contrast、reduced motion 與窄視窗手動 walkthrough；本次以 deterministic presentation/source tests、typecheck、package 與 Extension Host smoke 驗證，仍需在本機 UI 開啟後補做一次手動驗收。
2. Extension 仍是 filesystem projection；Codex Chat／engine 完成操作後必須由使用者 Refresh，Extension 不會自行判定權威 next 或直接執行 workflow。

除上述手動 UI walkthrough 外，沒有本 work 產生的已知阻礙。

## 驗收結論

DevWeave Control Center UX 已完成：總覽優先、四區域 progressive disclosure、繁中任務語言 command catalog、active/closed work 分組、誠實 snapshot provenance、reviewer readiness、可讀 audit、Wiki bounded browsing、prompt handoff 說明、workspaceState preference 與安全邊界均已落地。

G1、G2 目前均為 approved/current；7 個實作 task 已完成；EVID-004～EVID-009 全部 current/passed；Extension package、smoke、typecheck、npm tests 與 Python 83 項 regression 全部通過。既有 dirty VSIX 未被本 work 覆寫或重建；產品變更限於 `vscode-extension/**`，Wiki 只在 verification 依已核准 Knowledge plan refresh/seal，baseline targets 為空。

此 acceptance 已準備 G3 review。請使用者確認上述 residual risk 後，明確核准 G3；核准後再執行 `close`。

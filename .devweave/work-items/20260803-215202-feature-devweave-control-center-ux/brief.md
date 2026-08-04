# 工作摘要：改善 DevWeave Control Center UX 與使用者導引

<!-- DEVWEAVE:artifact=brief version=1 work=20260803-215202-feature-devweave-control-center-ux kind=feature -->

## 問題與目標

DevWeave Control Center 已能安全投影 managed workspace、呈現 work item 狀態，並將九個公開 `$devweave` 命令以 preview/copy 方式交給 Codex Chat；但目前 Dashboard 把 workspace health、命令產生、work detail、Wiki、verification、acceptance 與 raw audit 全部堆在同一個長頁面，且直接使用 G1/G2/G3、fingerprint、baseline、evidence、mutation 等 engine 術語。

本工作項的目標使用者包含第一次使用 DevWeave 的開發者、日常執行 work item 的開發者，以及需要審查 gate/evidence 的 reviewer。預設體驗採新手優先，治理細節仍可展開。成功訊號是使用者開啟 Extension 後能快速回答「目前在哪裡、下一步是什麼、會不會寫檔、複製後要去哪裡」，而 reviewer 能在不閱讀 raw event log 的情況下判斷 gate readiness。

本次改善不改變 DevWeave engine 或 public command contract；它將複雜度收斂在 Extension 內部的 presentation seam，讓 caller 看到較小、任務導向的介面，並保留完整的深度治理資料供進階檢視。

## 現況證據

### Wiki facts

- G1 依序記錄 `wiki/index.md`、`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md` 與 `wiki/modules/knowledge-engine.md`；目前 context 已保存頁面 status、content hash 與 source fingerprint。
- Wiki 明確指出 Extension 是 filesystem projection，engine/approved artifacts 才是權威來源；Extension 不執行 Python、shell、Git、network 或一般 workflow mutation。
- `wiki/overview.md` 與 `wiki/modules/knowledge-engine.md` 的 stored source fingerprint 已 stale；本 work 以 current source 與 approved baseline 為事實來源，不修改 Wiki。

### Source-backed facts

- `vscode-extension/webview/main.ts` 目前在同一頁渲染 repository diagnostics、repository metadata、command composer、work gates、artifacts、requirements/design/plan、Knowledge、tasks/evidence、verification、acceptance 與 audit。
- Command composer 直接以 `new/feature/refactor/bug/next/status/wiki bootstrap/revise/approve` 技術命令作為主要選擇；preview/copy contract 已經是公開 `$devweave` 命令，不能改成 machine CLI 或任意 JSON intent。
- `WorkspaceSnapshotReader` 讀取 filesystem projection；`engineObservedAt` 是 work state `updated_at` 的最大值，並非 Extension 即時向 engine 取得的 authoritative observation。
- Extension bootstrap 是唯一既有寫入 seam，且由 modal confirmation、固定 manifest、no-overwrite、conflict、rollback 與資產 hash 驗證保護；其他操作只複製 prompt。
- 目前 repository 有 7 個 closed work item、0 個 active work item；Extension snapshot reader 仍會讀取並顯示 closed history。
- 既有驗證基線為 Extension typecheck、26 個 unit/security tests、production package、VS Code Extension Host smoke，以及 root Python 83-test regression suite，先前均通過。

### Inferences

- 單一長頁與技術命令下拉會讓新手先學 engine vocabulary，才有機會完成一般任務；這與「降低瀏覽與操作認知成本」的產品目標不一致。
- 沒有 active work 時要求選擇 work item，會把 closed history 誤呈現為目前工作上下文。
- 以 snapshot time 與 state `updated_at` 比較 freshness 可能反覆顯示警告，即使沒有 source drift 證據；UI 必須改用誠實的 non-authoritative snapshot wording。
- 現有 `nextSafeAction` 是 UI 推導而非 engine `next` 結果，因此只能標示為 snapshot guidance，並應提供公開 `$devweave next` handoff。

### Unresolved gaps

- Repository 沒有真實使用者研究、telemetry 或可量化的首次完成時間；本 work 以狀態矩陣、可觀察文案、手動 accessibility review 與 deterministic tests 作為代理驗證。
- Extension 不會直接查詢 Codex Chat/engine，因此不能在本地宣稱 gate currentness 或 verification readiness；所有 authoritative claim 必須保留為 Codex/engine handoff。

## 範圍

### P0：任務導向總覽與清楚交接

- 將 Dashboard 重整為 `總覽`、`工作項目`、`知識`、`驗證與稽核` 四個區域，總覽預設只放 workspace state、目前工作、snapshot guidance、blocker 與主要 CTA。
- 將 command composer 改為任務語言分組，保留既有 public command intent、prompt text、sanitization 與 preview/copy 行為。
- 統一主要 UI、Command Palette、bootstrap 結果與提示文案為繁體中文；技術 ID、phase、path 與 raw event 放到次要或展開內容。
- 將 active work 與 closed history 分組；無 active work 時提供開始新工作 CTA，不要求從 closed history 選擇。
- 明確區分 filesystem snapshot、Codex Chat prompt handoff 與 bootstrap direct write；初始化完成後顯示 verification setup 與建立第一個 work 的後續導引。

### P1：日常開發、reviewer 與錯誤處理

- 加入 gate/reviewer readiness summary，呈現目前 gate、blocker、failed/stale evidence、缺少的條件與 approve/revise 的實際效果。
- 將 tasks、evidence、Wiki affected/pending refresh 與 diagnostics 改為可行動的狀態和人話修復建議。
- 將 raw event log 改為可讀 timeline 並保留可展開原文；prompt preview 顯示 will do / will not do / after copy 三段交接說明。
- 加入 loading、error、duplicate action 防護、focus 保留、ARIA/live region、keyboard、high contrast、reduced motion 與窄視窗支援。

### P2：可選的進階與規模化體驗

- 提供簡潔/進階顯示偏好，儲存在 Extension context，不寫入 repository。
- 改善 multi-root repository 選擇與 managed/unmanaged 標籤。
- Wiki 增加搜尋、分類與顯示全部頁面的入口。

## 非目標

- 不修改 Python engine、DevWeave schema、state/events/evidence ledger、Wiki content、baseline 或 hook policy。
- 不新增 branch、commit、push、PR、deployment、telemetry、network、Codex API 或直接執行 Python/shell/Git/engine 的能力。
- 不改變九個公開 `$devweave` 命令的名稱、參數語意、prompt text contract 或 security sanitization。
- 不讓 Extension 宣稱 filesystem projection 等於 engine authoritative state；`next` 仍透過 prompt handoff 取得權威建議。
- 不覆蓋或重建目前工作樹中已存在的 `vscode-extension/devweave-control-center-0.1.0.vsix` 變更。

## 風險

風險等級：standard

- 主要風險是 Webview information architecture、共用 host/webview presentation model 與現有 selection/preview/copy flow 的回歸；以 pure projection seam、table-driven state tests、typecheck、package 與 Extension Host smoke 降低風險。
- public prompt、BootstrapInstaller、filesystem path safety、CSP、no-process/no-network boundary 與既有初始化寫入行為保持不變，變更可由移除或停用 UI bundle 回復，不涉及資料 migration。
- P2 只使用 Extension context preference 與 bounded filesystem projection；不得把偏好或搜尋索引寫入 repository。

## Profile 補充

本 work item 採 feature profile：現況、價值、影響面與相容性已由上述 source-backed discovery 定義。第一個可驗證切片是 managed workspace 的總覽/空狀態/命令分組/公開 prompt preview handoff；其後在同一個 Extension presentation seam 補 reviewer readiness、診斷、timeline、accessibility 與 P2 顯示能力。所有 product source 變更限於 `vscode-extension/**`，G3 需要 acceptance 與 regression evidence。

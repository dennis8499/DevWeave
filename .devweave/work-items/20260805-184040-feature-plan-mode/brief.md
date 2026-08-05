# 工作摘要：初始 Plan Mode 導流

<!-- DEVWEAVE:artifact=brief version=1 work=20260805-184040-feature-plan-mode kind=feature -->

## 問題與目標

目前 Plan Mode 只在 G1/G2 的重大需求或設計問題出現後才被提及；使用者從普通模式提出新工作、bug、重構或 Wiki bootstrap 時，沒有在第一次會改變 Work Item 的操作前收到清楚導流。這會讓使用者先建立或修改工作項目，才發現後續需要切換模式。

本工作讓所有 pre-G2 的變更入口在任何 Work Item mutation 前完成 Plan Mode preflight。Router 只把 `request_user_input` 的可見性視為 host capability 證據：可見時繼續既有 G1/G2 流程；不可見時提示切換 Plan Mode 並停止。只有使用者明確選擇 compatibility，才允許逐題、結構化的 numbered fallback。Control Center 在總覽、操作預覽與複製結果中提供相同的 handoff，但不嘗試切換 host mode。

成功訊號是：普通模式的初始 mutation 不建立 Work Item、不 bind、不 revise、不建立 bootstrap Work Item；切換 Plan Mode 後重送可正常進入 G1 且不重複建立；既有 `$devweave ...` chatText 與 CLI 協定保持相容；Control Center 的提示清楚且複製仍可用。

## 現況證據

本次 G1 已依 index-first 順序記錄五個 Wiki context pages：`wiki/index.md`、`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`。引擎回報五頁皆為 active/current，content hash 與 source fingerprint 已記錄，沒有需要先以 raw source 補查的 Wiki gap。

已記錄的 Wiki 事實是：Plan Mode 目前是 G1/G2/Gate material decision 的正式入口；host tool visibility 是外部能力；Repository、Skill 與 Extension 不應建立 fake adapter、question state 或宣稱可以切換 host mode；Extension 只負責投影與 handoff。

必要的 source evidence 顯示：`.agents/skills/devweave/SKILL.md` 與 `references/native-question-contract.md` 尚未定義初始 `start` 前的 preflight 順序；`vscode-extension/src/prompt.ts` 只產生原始 `$devweave ...` prompt 與 mutation metadata；`src/presentation.ts` 的無 active/pre-G2 guidance 沒有 Plan Mode handoff；`webview/main.ts` 只有一般 preview/copy handoff；Extension source 沒有 `request_user_input` 或 host mode adapter；目前 Extension 版本是 0.2.1。red-capable static check 已重現「initial Router/Control Center entry has no Plan Mode handoff」。

以上 evidence 支持將改動集中在 Router/contract、Extension additive presentation metadata/UI、測試與治理文件。host 能否實際切換及使用者跨回合重新送出仍屬外部手動驗收，不能由 repository 推測或自動化。

## 範圍

- 更新 DevWeave router 與 native-question contract：`new`、`feature`、`refactor`、`bug`、`wiki bootstrap`，以及會回到 G1/G2 的 `revise`，均在建立或修改 Work Item 前做 Plan Mode preflight。
- 定義 host capability 不可見時的停止提示，以及只有使用者明確選擇 compatibility 才啟用的逐題 numbered fallback；保留既有 Gate、protocol 與 lifecycle。
- 在 `PromptBundle` 與 `SnapshotGuidance` 加入最小 optional `PlanModeGuidance` metadata，至少包含 `required` 與 `stage`；`chatText` 維持原內容。
- 在 Control Center 總覽、mutation preview 與 copy result 顯示 Plan Mode handoff；保留複製能力，不新增 checkbox、host command 或 mode adapter。
- 更新 root policy、使用手冊、Control Center README、bootstrap `AGENTS.md`、相關 Wiki 與 accepted baseline；新增 repository contract、Extension unit/typecheck/package/smoke evidence。
- 將 Extension 升至 0.2.2，產生並驗證新的 0.2.2 VSIX，同時保留既有 0.2.1 artifact。

## 非目標

- 不修改 Python engine 的 CLI、JSON schema、question state、ledger 欄位或建立 fake `request_user_input` adapter。
- 不讀取、切換或模擬 Codex host mode；Extension 不新增 host command、勾選確認或 Help 頁專用導流。
- 不改變 `$devweave ...` chatText、既有 command catalog、PreviewGate、G1/G2/G3 approval semantics 或 post-G2 approved task 行為。
- 不在本工作建立 branch、worktree、commit、push、issue、PR、deployment 或 production instrumentation。
- 不把外部 host 的切換結果當成 repository 可自動證明的狀態；手動 round-trip 由 G3 驗收。

## 風險

風險等級：standard

- 初始 preflight 的順序若錯誤，可能在停止前已建立 Work Item；以 Router contract、CLI workspace 檢查與手動驗收鎖定 mutation boundary。
- `PlanModeGuidance` 是 additive optional metadata，需確認舊 consumer 不因缺欄位失效；以 unit、typecheck、package verifier 與 chatText exact assertions 驗證。
- VSIX 版本升級要保留 0.2.1 可回溯 artifact；package/smoke test 驗證 0.2.2 manifest、bootstrap assets 與檔案存在性。
- Wiki 與 baseline 的治理更新必須等 verification 階段的 Knowledge Review，並遵守最多五個 content pages、index/log coupling 與 seal 規則。
- 這是標準風險、可逆的文件/路由/UI/metadata 變更；不自動切換 host，也不擴大外部權限。

## Profile 補充

這是 feature work：現況是 initial pre-G2 entry 缺少 Plan Mode 導流；價值是讓第一次 mutation 前的模式邊界可預期，避免無意建立或修改 Work Item；影響面涵蓋 DevWeave router/contract、Control Center presentation/webview、治理文件與 release artifact；相容性要求是保留既有 chatText、CLI protocol、work lifecycle、post-G2 flow，以及 0.2.1 artifact。

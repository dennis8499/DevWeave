# 工作摘要：DevWeave V2 app-server harness

<!-- DEVWEAVE:artifact=brief version=1 work=20260825-163914-feature-devweave-v2-app-server-harness kind=feature -->

## 問題與目標

DevWeave 0.2.3 已具備可追溯 Work Item、Gate、受控驗證與唯讀 VS Code Control Center，但主要互動仍是「檔案快照 → 預覽 → 複製 prompt → Codex Chat → 手動 Refresh」。這個模型沒有直接使用 Codex app-server 的 thread/turn/event/approval primitive，也把產品事實分散在 `AGENTS.md`、`.devweave/baseline/`、`wiki/` 與大量歷史 ledger，增加 agent 導航成本、雙重真實來源與維護負擔。

本工作項要交付 DevWeave 2.0.0：以 Codex app-server 的 stdio JSONL 介面作為 VS Code rich client 的主要執行面、以 project-scoped MCP 提供 agent-safe workflow tools、以 host-owned 操作保留 approval 與不可逆 mutation 權限，並以單一 typed ExecPlan、風險自適應 Gate、受控驗證和 `docs/` 知識樹取代 v1 lifecycle。V1 不做 dual-read；只提供一次性唯讀 export/index，原始歷史仍可由 Git history 取回。

成功訊號是：使用者可在 VS Code 內啟動、恢復、steer、中斷及審查 Codex run，不再依賴 clipboard handoff；agent 只能經 allowlisted MCP tools 推進已核准計畫；每次 run 在乾淨基線上建立隔離分支並產生階段 commit；V2 state 可中斷恢復；風險級別決定必要 Gate 與 review 強度；文件、驗證與 UI evidence 可由機械檢查證明 current。

## 現況證據

### Wiki facts

- `wiki/index.md` 將現況描述為單一 `$devweave` router、G1/G2/G3、Wiki-first、受控 verification 與唯讀 Control Center。
- 五個相關內容頁都被 `knowledge status` 標記為 `stale_source`。頁面仍明確記載 Extension 不執行 Python、shell、Git、network 或 Codex API，workflow mutation 依賴 preview/copy/refresh。
- Wiki 描述的 Verification Policy v2 已有 `shell=False`、bounded timeout、dependency closure、writer barrier、declared outputs、source-bound evidence 與 high-risk isolated review，可作為 V2 保留的安全基礎，但不能作為 V2 app-server/MCP 行為的證據。

### Source-backed facts

- `vscode-extension/package.json` 目前版本是 0.2.3，公開命令仍以開啟 dashboard、初始化、refresh、copy-next-action 與 Wiki preview 為主；repository 搜尋不到 app-server、Codex SDK 或 MCP server 整合。
- `.codex/` 只有 `hooks.json`，沒有 project-scoped `config.toml`；目前 PowerShell PATH 找不到 `codex`，故 V2 必須把 CLI preflight 做成明確 hard prerequisite，不能靜默 fallback 或自動下載。
- `.agents/skills/devweave/scripts/devweave_core.py` 為 5,396 行／222,794 bytes，`vscode-extension/src/snapshot.ts` 為 1,039 行／44,646 bytes；root `AGENTS.md` 為 92 行／12,072 bytes，顯示核心責任與 agent 指引過度集中。
- Git 目前追蹤 21 個 v1 Work Item state、411 個 evidence JSON 與三個 VSIX binary；這些 runtime/history artifact 使 HEAD 膨脹，且不適合作為 V2 的主要知識入口。
- 既有 targeted baseline 在本工作項啟動前通過：repository contract 16 tests、Extension unit 88 tests，且 `doctor` 為綠色；`knowledge status` 則是 warning、bootstrap incomplete、5/7 pages stale。
- OpenAI 官方 Harness Engineering 文章建議以小型 map 型 `AGENTS.md`、結構化 repo knowledge、可執行 invariants、可觀察性與持續清理維持 agent legibility：<https://openai.com/zh-Hant/index/harness-engineering/>。
- OpenAI 官方 Codex app-server 文件與 platform 文章提供 initialize、thread start/resume、turn start/steer/interrupt、streamed item/plan/diff/usage、review、approval 與 MCP 狀態等整合面；本工作項只採穩定介面，排除 experimental `tool/requestUserInput` 與 dynamic tools：<https://developers.openai.com/codex/app-server/>、<https://developers.openai.com/blog/codex-as-a-platform>。

### Inferences

- 將 Extension 從 filesystem projection/clipboard adapter 改為 app-server client，可以直接使用 Codex 已有的執行、事件與 approval semantics，減少平行 orchestrator 與狀態漂移。
- 將 agent tools 與 host-only mutations分層，可同時提高自動化程度與人工作業關卡的不可繞過性。
- 將 accepted knowledge 統一至 `docs/`、縮短 root map、把 ephemeral run state 排除於 Git，可降低每次 agent 啟動的 context 成本與 stale knowledge 面積。
- 因為同時改變 lifecycle、storage、Git、Extension 與 public interface，clean cutover 比 dual-read 簡單，但必須以 high-risk Gate、export 與完整回歸保護資料可回復性。

### Unresolved gaps

- 五個 Wiki 內容頁的 stored/computed source fingerprint 不一致；V2 不修補這套舊 Wiki，而是在已核准設計後以 `docs/` 單一真實來源取代並保留可稽核 export。
- 目前環境找不到 Codex CLI；這不阻止設計與純單元測試，但 app-server E2E 必須在 PATH 或設定的絕對路徑可解析後才可宣稱通過。不得以 mock 結果冒充真實 E2E。
- app-server WebSocket transport 與 experimental request-user-input/dynamic tools 不在本版認證範圍；若未來採用，必須另開工作項。

## 範圍

- 建立 V2 app-server adapter、event reducer、run supervisor、project-scoped MCP server、typed domain model、storage/recovery、risk policy、Git transaction、verification/review 與 observability modules。
- 將 VS Code Extension 改為 app-server rich client，提供 start/resume/steer/interrupt/review、pending decision、plan/diff/tool/usage、verification 與 diagnostics UI；移除 clipboard-first workflow。
- 提供 agent-facing MCP tools：`run_inspect`、`context_read`、`plan_save`、`decision_request`、`task_update`、`verification_run`、`verification_read`、`completion_request`。
- 提供 host-only operations：`run_start`、`run_resume`、`decision_resolve`、`gate_decide`、`run_cancel`；提供 CLI：`doctor`、`inspect`、`check`、`verify`、`export-v1`、`mcp-serve`。
- 以 `docs/`、`ARCHITECTURE.md`、短版 `AGENTS.md` 和 typed ExecPlan 重組知識；加入 architecture/dependency/file-size/traceability 檢查。
- 完成 v1 一次性 export/index，從 V2 HEAD 移除舊 raw runtime ledger、Wiki 雙重真實來源與 tracked VSIX binaries；保留 Git history 回復路徑。
- 更新 Python、TypeScript、tests、fixtures、build/package、project policy、README、ignore 與 baseline，使 Windows x64／VS Code first certification 可重現。

Machine scope 已以 replace semantics 記錄：`.agents`、`.codex`、`.devweave`、`.gitignore`、`AGENTS.md`、`ARCHITECTURE.md`、`README.md`、`docs`、`fixtures`、`skills-lock.json`、`tests`、`vscode-extension`、`wiki`。

## 非目標

- 不提供 v1/v2 dual-read、原地 schema migration 或 v1 mutation compatibility；V1 僅可 export/index。
- 不自動下載、安裝或更新 Codex CLI，也不以其他 CLI、clipboard 或假 server fallback。
- 不採 app-server experimental WebSocket、`tool/requestUserInput` 或 dynamic tools；pending decision 由 DevWeave 保存，決議由 host-only operation 完成。
- 不宣稱 macOS、Linux、Marketplace publishing、remote push、PR 或 merge 支援；本版只認證 Windows x64 與 VS Code。
- 不保存 raw chain-of-thought、完整 prompts、secrets 或未界定的 telemetry；不建立第二個 remote tracker 或 database service。
- 不自動合併或切回 base branch；V2 run 結束後仍留在 run branch，後續整合由使用者決定。

## 風險

風險等級：high

- 這是允許 breaking change 的 clean cutover，會改變 public CLI/MCP、workflow state、Git ownership、Gate、知識模型、Extension runtime 與 packaging。
- 主要失敗模式是 approval bypass、錯誤 repo mutation、run 無法恢復、v1 歷史遺失、verification false-positive、app-server protocol drift 與 UI 將 projection 誤報為 authoritative state。
- 緩解方式是 host/agent capability 隔離、typed protocol boundary、atomic/append-safe state、乾淨 Git preflight、phase commits、source-bound evidence、max-three review loop、V1 export、Git history recovery、完整 high profile 與 exactly-one isolated final reviewer。
- 本次已在乾淨 `master` 基線後建立 `devweave/20260825-163914-app-server-harness`；`master` ref 維持 `3662d8622b46a1cab6931da988db3c4280def783` 不變。未經使用者另行要求不 push、PR、merge 或切回。

## Profile 補充

本工作項採 feature profile，但實際是跨 Python engine、TypeScript Extension、repository governance、資料保留與 release surface 的平台級 replacement。使用者已確認：app-server primary、risk-adaptive gates、V2 clean cutover、同 checkout clean branch、每階段 commit、`docs/` 單一知識來源、Codex CLI hard prerequisite，以及 breaking changes 可接受。這些決策已視為 material requirements，不留 compatibility 推斷空間。

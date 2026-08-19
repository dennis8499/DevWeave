# 工作摘要：建立公開跨平台 deterministic CI baseline

<!-- DEVWEAVE:artifact=brief version=1 work=20260819-115533-feature-deterministic-ci-baseline kind=feature -->

## 問題與目標

DevWeave 目前沒有 GitHub Actions workflow；所有回歸證據主要來自維護者在單一 Windows 主機上手動執行。這使 pull request 與 `master` push 缺少公開、可重複且能及早發現跨平台問題的 checks，也讓後續 P0 改善缺少共同的 characterization baseline。

本工作項服務 repository 維護者與外部貢獻者。目標是在不改變 DevWeave lifecycle、CLI 或 runtime semantics 的前提下，以 deterministic tests 持續證明 Python engine、Guard、command policy、repository contract 與 VS Code Extension 的既有開發合約。成功訊號是：PR 與 `master` push 會顯示分工清楚的 Python、Node 與 hygiene checks，失敗組合可獨立辨識，README 同時提供本機等價命令與支援邊界。

## 現況證據

### Wiki 事實

- 已依序讀取 `wiki/index.md`、`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md` 與 `wiki/modules/vscode-extension.md`。
- Wiki 說明 Python 3.11+ 是技術門檻、現行 release certification 只涵蓋特定 Windows 環境，且 deterministic verification、repository contract、Windows launcher 與 explicit capability boundary 都是既有品質契約。
- 索引尚無公開 CI 模組頁；overview、architecture 與 VS Code Extension 頁面的 stored source fingerprint 均已過期，不能拿舊的 Windows 測試數量或認證敘述當作跨平台事實。

### Source-backed 事實

- 2026-08-19 檢查確認 `.github/workflows/ci.yml` 不存在。
- `README.md` 目前沒有 CI badge；驗證章節只列 PowerShell 形式的 Python／Doctor／project／command／`git diff --check`，沒有 POSIX 或 Node 等價命令。
- `vscode-extension/package.json` 已提供 `typecheck`、`test` 與 `build` scripts，且有 committed lockfile 可供 `npm ci` 使用。
- `tests/test_repository_contract.py` 的 Doctor fixture 目前對 Windows capability names 一律只檢查 `ok`；尚未明確區分 Windows 真實 launcher probe 與非 Windows 的具名 skip reason。
- 改善套件 P0-00 要求 PR／`master` 上的公開 CI、Python 3.11–3.14、Windows／Ubuntu／macOS、Node 20／22、`git diff --check`、最低權限、checkout 不持久化 credentials、明確 unsupported capability 與本機等價命令。
- 人工作業分支上的乾淨基線已完成：Doctor 全綠；Python 129 項通過、1 項因 Windows symlink privilege 明確跳過；Extension 的 `npm ci`、typecheck、unit tests 與 build 均通過。

### 推論

- 以單一 workflow 拆成 Python、Node、hygiene 三種 job，可讓 PR checks 清楚定位失敗來源；matrix `fail-fast: false` 可保留所有 OS／版本結果。
- Python matrix 橫跨三個作業系統即可履行跨平台 runtime 契約；Node matrix 採 Windows／Ubuntu 已能驗證兩個主要 shell/path 家族，P0-00 不需再付出 macOS Node jobs 的時間成本。
- Workflow contract 應由 repository test 靜態固定，否則 YAML 被刪除、縮減 matrix、放寬權限或改成浮動 action tag 時，本機測試無法及早阻止退化。

### 未解缺口

- GitHub-hosted runners 的真實執行結果必須等人類 push／開 PR 後才能觀察；Codex 不替使用者 commit、push 或建立 PR。G3 前可完成 workflow contract 與本機全套驗證，首次遠端執行則是人類發布分支後的操作確認。
- 現有 Wiki 過期與缺少 CI 模組頁會在 G3 Knowledge Review 以 promote 計畫處理；目前沒有未回答、會改變 G1 範圍的 material requirement。

## 範圍

- 新增 `.github/workflows/ci.yml`，在所有 pull request 與 `master` push 執行：
  - Python：Ubuntu、Windows、macOS × Python 3.11、3.12、3.13、3.14。
  - Node：Ubuntu、Windows × Node 20、22，依序執行 `npm ci`、typecheck、unit test、build。
  - Hygiene：`git diff --check`。
- 更新 `tests/test_repository_contract.py`，固定 workflow trigger、matrix、權限、完整 action SHA、checkout credential、命令與 Doctor capability truth contract。
- 更新 `README.md`，加入 CI badge、PowerShell／POSIX／Node 本機等價命令，以及「CI matrix」與「特定 Windows release certification」的差異。
- G3 更新 `.devweave/baseline/quality.md`，並規劃提升公開 CI 模組知識、刷新受 README 影響的 overview／architecture、同步 Wiki index/log/seal。

## 非目標

- 不呼叫 Codex API，也不以 LLM review 取代 deterministic tests。
- 不修改 lifecycle、Gate、state、event、evidence、command policy 或 Guard semantics。
- 不重構 `devweave_core.py`，不順帶實作 P0-01 以後的改善項目。
- 不執行或新增 Extension smoke、package、VSIX release、部署、Marketplace 發布。
- 不加入 auto-fix、自動 commit、自動開 PR、branch protection 或 repository settings mutation。
- 不使用付費 larger runner、自架 runner或 macOS Node matrix；不宣稱 P0-00 已擴張正式 release certification。

## 風險

風險等級：standard

這項變更不碰產品 runtime，但會成為 PR 合併品質訊號，錯誤 YAML、錯誤 matrix 或供應鏈設定可能造成假綠、全面阻塞或不必要的 runner 消耗。第三方 Actions 與 dependency install 也形成 CI supply-chain 邊界。

緩解方式是：top-level `permissions: contents: read`、checkout `persist-credentials: false`、官方 Actions 以完整 commit SHA 固定並附版本註解、matrix `fail-fast: false`、不用 secrets／Codex API、repository contract 靜態固定安全與矩陣契約、既有本機全套測試維持綠燈。公開 repository 的 standard GitHub-hosted runners 不需另付 runner 費用；本工作項不啟用 larger runner 或額外付費服務。變更可藉移除 workflow、回復 README／contract test／quality baseline 完整還原。

## Profile 補充

- 現況：repository 無公開 CI，Windows 本機基線已通過但無 PR 可見證據。
- 價值：為 P0-01 之後的完整性、安全與可維護性變更提供共同的不退化基準。
- 影響面：GitHub Actions 設定、repository contract、README、quality baseline 與相關 Wiki；不改公開 CLI 或 runtime。
- 相容性：Python 3.11–3.14 與 Node 20／22 是 CI 驗證矩陣；既有特定 Windows release certification 仍維持原義。既有使用者若不使用 GitHub Actions，不會受到 runtime 行為改變。

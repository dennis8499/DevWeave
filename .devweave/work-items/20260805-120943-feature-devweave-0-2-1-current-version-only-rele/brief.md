# 工作摘要：DevWeave 0.2.1 current-version-only release contract

<!-- DEVWEAVE:artifact=brief version=1 work=20260805-120943-feature-devweave-0-2-1-current-version-only-rele kind=feature -->

## 問題與目標

DevWeave 0.2.1 已成為唯一要驗收與交付的 VSIX，但現有封裝 verifier、Extension regression test、公開文件、accepted baseline 與 Codebase Wiki 仍把 0.1.0／0.2.0 binary retention 當成 release 必要條件。最新 repository 狀態已移除三個 VSIX，導致 Extension test 因缺少 0.1.0 直接失敗，也使 `npm.cmd run package` 無法完成 current artifact 驗證。

本工作要把 0.2.1 release contract 統一成 current-version-only：只產生、驗證、安裝與交付 `devweave-control-center-0.2.1.vsix`，舊版 VSIX 不存在不得造成失敗。成功訊號是 final RC 上所有自動化與端到端驗收通過、公開說明一致、產出可重現且綁定單一 HEAD／SHA-256。

## 現況證據

### Wiki facts

- 已依序記錄 `wiki/index.md`、overview、knowledge workflow architecture、Knowledge Engine module 與 VS Code Extension module；五頁均為 active，但四個內容頁的 source fingerprint 已因本工作 source 變更而 stale。
- Overview、knowledge workflow 與 VS Code Extension 三個內容頁仍把 0.2.0／0.1.0 retention、廣泛 Windows／VS Code／Python 支援及舊測試數量列為 0.2.1 契約，因此已記錄 contradiction gap；Knowledge Engine 雖無 legacy release 承諾，仍因 repository contract source 變更成為 affected page。

### Source-backed facts

- `vscode-extension/scripts/verify-package.mjs` 明確 `stat` 並比對 0.1.0／0.2.0 的固定大小與 SHA-256。
- `vscode-extension/test/unit/package-version.test.ts` 要求 0.1.0、0.2.0、0.2.1 三個 artifact 同時存在；目前執行結果為 72/73，唯一失敗是 0.1.0 `ENOENT`。
- README、使用手冊、Extension README、內嵌 Help、三份 baseline 與三個 Wiki content pages 均存在舊版保留／回退文字。
- Python full suite 實際執行 98 項，97 通過、1 項因目前 Windows symlink privilege 略過；文件仍分別記載 94 或 96 項。
- Current source-derived package 實際產生 58 個 bootstrap files／118 個 VSIX entries；第 58 個 bootstrap file 是 Plan-first 所需的 `native-question-contract.md`，Wiki／baseline 的 57／117 已過期，不能以刪除必要 contract 來迎合舊數字。
- G3 acceptance validation 已機械確認 `debug.log` 清理漏列於 machine scope，且 `wiki/modules/knowledge-engine.md` 必須列入 affected-page refresh；兩者均是原核准 release cleanup／Knowledge Review 意圖的治理 coverage 修正，不改產品需求或公開介面。
- `doctor`、Extension typecheck 與 `git diff --check` 已通過；目前沒有其他 active work item。

### Inferences

- Package builder 已從 `package.json` 導出 0.2.1 並排除所有 `.vsix` 輸入；移除 legacy assertions 不需要改變 archive format、bootstrap manifest、public command 或 runtime behavior。
- Current-only policy 是公開 release contract 變更，必須以 regression test 固定，不能只刪除 failing assertion。

### Unresolved gaps

- Final 0.2.1 VSIX 的大小與 SHA-256 只能在所有 source、文件與 baseline 穩定後產生。
- Symlink containment test 需要在相同 Windows build、具 symlink 權限的隔離環境補驗；若環境仍不可用，零缺陷門檻將保持 No-Go。
- VSIX 的 GUI 安裝／重裝／解除安裝與實際 Control Center walkthrough 必須在 verification 階段完成。

## 範圍

- 封裝 verifier 與 package-version regression test改為只要求目前 package version 0.2.1，並持續驗證 current VSIX、metadata、manifest、bundle entries、source length 與 SHA-256。
- 更新 repository／Extension 公開文件與內嵌 Help，移除舊 binary retention／downgrade 承諾，明確說明事故處理為停止散布並停用或解除安裝 0.2.1，且不刪除 repository 資料。
- 將公開認證描述限定於本次實測環境；較廣的 engine/minimum version 可保留為技術相容門檻，但不得描述成已完成本次認證。
- 對齊 accepted baseline、98 項 Python suite 數量與 repository contract regression；verification 再依 Knowledge Review 更新四個受影響 Wiki pages、index 與 append-only log。
- 建置並驗證唯一 release artifact `vscode-extension/devweave-control-center-0.2.1.vsix`，清理非發布 `debug.log`。

## 非目標

- 不恢復、重建、驗證、交付或支援 0.1.0／0.2.0 VSIX。
- 不新增 Marketplace、自動更新、跨平台或其他 Windows build／CPU 架構的認證承諾。
- 不改變公開 chat verbs、Machine CLI、JSON schema version 1、G1/G2/G3、Hook、Wiki lifecycle 或 Extension command IDs。
- 不以刪除或跳過 release regression test 代替 current artifact integrity verification。
- 不建立 branch、worktree、commit、push、PR 或 remote release。

## 風險

風險等級：high

本工作改變公開交付、認證與事故處理契約。若 verifier 過度放寬，可能發布缺檔或內容漂移的 VSIX；若文件未同步，使用者會收到互相矛盾的回退與支援資訊。產品程式行為、workspace data 與 bootstrap write seam 不應改變，實作可透過單一 regression seam 回復；high-risk G3 仍需 current isolated read-only Independent Review。

## Profile 補充

Profile：feature。

第一個可驗證 outcome 是：在 0.1.0／0.2.0 均不存在的 repository，Extension unit suite 全綠，`npm.cmd run package` 只產生並完整驗證 0.2.1，且所有公開說明一致。相容性要求是 existing 0.2.1 public commands、bootstrap content、安全邊界與 machine contracts 零變更。

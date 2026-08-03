# 工作摘要：空白 VS Code 專案初始化產生 DevWeave 流程內容

<!-- DEVWEAVE:artifact=brief version=1 work=20260803-112312-feature-vs-code-devweave kind=feature -->

## 問題與目標

目前 VS Code Extension 在尚未初始化的 workspace 只會讀取 snapshot，並將
`python -B .agents/skills/devweave/scripts/devweave.py --repo . init` 包裝成要複製到
Codex Chat 的 prompt。對完全空白的 workspace 而言，repository 內沒有可執行的
DevWeave skill、engine、hook 或 `.devweave` starter，因此使用者無法只靠 Extension
完成導入。

本 feature 要讓使用者在 VS Code 開啟一個空白 Git workspace 後，透過 Extension 的
初始化入口完成 DevWeave bootstrap。初始化由 Extension 內建的版本化資產完成，不依賴
Codex Chat、手動 Python CLI、網路或第二個安裝工具；完成後 workspace 應具備執行
DevWeave workflow 所需的 engine、skill、hook、project state、baseline 與 Wiki starter。

成功訊號是：使用者確認初始化後，Extension 顯示 repository 已 managed，且下列內容
可由 workspace filesystem 讀取；重新整理後不再顯示 `project_missing`：

- `.agents/skills/devweave/` 的 router、engine、references 與 assets。
- `.codex/hooks.json`。
- `.devweave/project.json`、baseline、`work-items/` 與必要 cache 目錄。
- root `wiki/` 的 index、overview、log 與類別目錄。

## 現況證據

Wiki-first context 已依序讀取 `wiki/index.md`、`wiki/overview.md`；`overview.md` 是
placeholder，已記錄 gap：「缺少 VS Code Extension 初始化入口、空白專案判定與產生
內容的現況證據」。因此以下以目前 source 與 accepted baseline 補足缺口。

- `.devweave/baseline/architecture.md` 定義 `WorkspaceSnapshotReader` 只使用 VS Code
  workspace file API，Extension 不呼叫 Python、shell、Git、外部網路或 repository
  write API；`vscode-extension/README.md` 也把 Extension 定義為唯讀 prompt composer。
- `vscode-extension/src/snapshot.ts` 在 `.devweave/project.json` 不存在時只回傳
  `project_missing` warning、空 work items 與 `mutationBlocked: false`。
- `vscode-extension/src/prompt.ts` 的 `init` action 只產生 engine init command，並將
  `.devweave/project.json`、`.devweave/baseline/`、`wiki/` 列為 prompt targets。
- `vscode-extension/webview/main.ts` 對未初始化狀態顯示「Copy initialization prompt」，
  並明確告知 Extension 不會執行 CLI 或改變 repository bytes。
- `.agents/skills/devweave/scripts/devweave_core.py:init_project` 能非破壞性建立
  `.devweave`、三份 baseline 與 Wiki starter，但目前任意新 workspace 沒有這份 engine
  與 bundled assets；VSIX 目前只包含 Extension bundle、webview 與 icon。

## 範圍

1. 新增 Extension-owned bootstrap installer 與 VS Code filesystem write adapter，
   僅在使用者明確確認且 workspace 尚未 managed 時執行。
2. 將可執行 DevWeave workflow 所需的 skill、Python engine、references、assets 與
   hook 以版本化、唯讀來源包入 VSIX，並由 installer 複製至 repository。
3. 以 engine 相容格式產生 project defaults、baseline、work-item/cache 目錄與 Wiki
   starter；建立後重新讀取 snapshot、顯示成功或逐路徑 diagnostic。
4. 對既有相容檔案採用、不覆寫使用者內容；對不相容或不安全目標 fail closed。
5. 更新 Extension UI、public command/activation metadata、使用手冊、unit/security/
   smoke tests 與 package verification。
6. 在 verification 階段更新反映「Extension 可執行 bootstrap write」的 accepted
   architecture、product 與 quality baseline（若完整 diff 證實受影響）。

## 非目標

- 不安裝或內嵌 Python、Git、Codex/VS Code 本身，也不替 workspace 建立 Git repository。
- 不執行任意 shell、Python CLI、Git command、網路下載或其他外部 process；初始化是
  Extension 內的檔案操作。
- 不替使用者建立第一個 work item、不跳過 G1/G2/G3、不核准 gate，也不執行產品 mutation。
- 不覆寫既有 `project.json`、hook、skill、baseline、Wiki 或其他使用者檔案；既有不相容
  內容的修復與 migration 另立 work item。
- 不提供 branch、commit、push、PR、deployment、remote tracker 或一般專案 scaffold。
- 不改變已 managed repository 的既有唯讀 dashboard 與 Codex Chat workflow；只增加空白
  workspace 的一次明確初始化能力。

## 風險

風險等級：high

這項變更首次讓 Extension 寫入 repository，且會安裝可被 Codex hook 使用的 Python
engine/skill 檔案，屬於 public behavior、供應鏈與安全邊界變更；若路徑驗證或衝突處理
錯誤，可能覆寫使用者內容或留下半套 workflow。採用以下控制：

- 所有寫入路徑由固定 manifest allowlist 產生並限制在 workspace root；拒絕 absolute、
  traversal、symlink escape 與 manifest 外路徑。
- 初始化需要明確 UI confirmation；不經由背景 activation 自動寫入。
- 只建立不存在的檔案，內容不一致時停止並逐路徑回報；重複初始化必須是 idempotent。
- 資產不從網路取得，package verification 檢查 bundle manifest，unit/security/smoke
  tests 覆蓋空白、相容、衝突、失敗與 UI activation 情境。
- 既有 managed workspace 維持唯讀行為；高風險 gate 額外要求獨立 review evidence。

## Profile 補充

本工作採 `feature` profile：以目前空白 workspace 行為為基線，新增一個可獨立驗證的
bootstrap vertical slice；影響 Extension 的 workspace/filesystem adapter、webview
初始化入口、VSIX 資產、使用手冊與測試，並維持既有 managed workspace 的相容性。

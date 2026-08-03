# DevWeave Control Center

DevWeave Control Center 是一個 desktop-first 的 VS Code Extension，將 DevWeave 的檔案狀態投影成可瀏覽的 Sidebar、Dashboard、Work Item detail 與 Wiki-first workspace。

## 設計邊界

- Extension 平時只讀取 workspace filesystem snapshot，不呼叫 Python、shell 或 Git；唯一的 repository write 是使用者在 modal confirmation 後觸發的固定 bootstrap manifest 安裝。
- Bootstrap 只會建立缺少的 DevWeave engine/skill、hook、project、baseline、Wiki starter 目標；既有內容必須與 bundle 完全相同才會採用，衝突時 fail closed，不覆寫使用者檔案。
- Extension 只產生使用手冊列出的九個公開 `$devweave` 對話命令；使用者先檢查公開命令 preview，再確認複製到 Codex Chat。
- Bootstrap 不依賴 Codex Chat、Python、shell、Git、network 或其他外部 process；安裝完成後仍由既有 DevWeave engine 負責 workflow state、gates 與 evidence。
- DevWeave engine、JSON contract、gates、evidence、baseline 與 Wiki 仍是權威來源。
- UI 使用 VS Code theme tokens、Codicons、鍵盤 focus、ARIA labels、high-contrast 與 reduced-motion 支援。
- Extension 不提供 branch、commit、push、PR、release 或版本比較/還原功能。

## 開發與驗證

在 `vscode-extension/` 目錄執行：

```powershell
npm install
npm run typecheck
npm test
npm run package
npm run test:smoke
```

`npm run package` 會產生 `dist/extension.js` 與 `dist/webview/` production bundle。`npm run test:smoke` 會使用 VS Code Extension Host 驗證 activation、Activity Bar view 與公開 commands。

## 使用方式

1. 在 VS Code 開啟 DevWeave repository。
2. 若 workspace 尚未初始化，從 Command Palette 執行 `DevWeave: Initialize Workspace`，或開啟 DevWeave Dashboard 按下初始化按鈕；確認 modal 後 Extension 會直接安裝完整 bootstrap bundle。
3. 從 Activity Bar 開啟 DevWeave；Sidebar 會顯示 repository 與所有 work items，包括 closed work items。
4. 在 Dashboard 檢視 gates、phase、tasks、evidence、Wiki health、syntactic bootstrap recommendation、coverage、Knowledge Review 與 next safe action；這些資料與檔案開啟入口維持唯讀，source currentness 仍以 engine 為準。
5. 在「產生 Codex 對話命令」表單選擇 `new`、`feature`、`refactor`、`bug`、`next`、`status`、`revise`、`approve` 或 `wiki bootstrap`，填入欄位後先預覽，再按「Confirm and copy」複製公開 `$devweave ...` 命令。
6. 單一 work item 會自動帶入；多個 work item 必須先在 Dashboard 選擇。`next` 與 `status` 可取消帶入 work ID；`revise` 與 `approve` 沒有目前 work 時不能送出。
7. 在 Codex Chat 審閱並送出命令，由 DevWeave engine 執行後回到 Extension 使用 Refresh Snapshot 重新讀取磁碟狀態。

Codebase Wiki bootstrap 有三個等價入口：公開命令下拉選單、Knowledge 面板在推薦時顯示的「Bootstrap Codebase Wiki」按鈕，以及 Command Palette 的 `DevWeave: Bootstrap Codebase Wiki`。三者都只產生並預覽 `$devweave wiki bootstrap`；Extension 不直接執行 machine CLI、不寫 Wiki，也不新增 process 或 network 權限。Command Palette 入口會先顯示 modal prompt，只有確認後才複製。

表單不提供 Doctor、Validate、Task、Knowledge、Evidence、Close、gate 參數或任意 `ActionIntent JSON` composer。`approve` 只帶 work ID；目前 gate 仍在 Dashboard 中唯讀呈現。

Extension 會明確標示 `Filesystem snapshot`、`Last engine-observed state` 與 refresh warning；它不會自行執行 `sync_state` 或重建 fingerprint。

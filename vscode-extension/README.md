# DevWeave Control Center

DevWeave Control Center 是一個 desktop-first 的 VS Code Extension，將 DevWeave 的檔案狀態投影成可瀏覽的 Sidebar、Dashboard、Work Item detail 與 Wiki-first workspace。

## 設計邊界

- Extension 平時只讀取 workspace filesystem snapshot，不呼叫 Python、shell 或 Git；唯一的 repository write 是使用者在 modal confirmation 後觸發的固定 bootstrap manifest 安裝。
- Bootstrap 只會建立缺少的 DevWeave engine/skill、hook、project、baseline、Wiki starter 目標；既有內容必須與 bundle 完全相同才會採用，衝突時 fail closed，不覆寫使用者檔案。
- 所有會改變狀態的動作都先顯示 Action Preview；使用者確認後，Extension 只將完整 prompt 複製到 Codex Chat。
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
4. 在 Dashboard 或 work item detail 檢視 gates、phase、tasks、evidence、Wiki health 與 next safe action。
5. 選擇 workflow 動作後檢查 Action Preview，再按「複製到 Codex Chat」並由使用者送出 prompt。
6. 由 DevWeave engine 執行後，回到 Extension 使用 Refresh Snapshot 重新讀取磁碟狀態。

Extension 會明確標示 `Filesystem snapshot`、`Last engine-observed state` 與 refresh warning；它不會自行執行 `sync_state` 或重建 fingerprint。

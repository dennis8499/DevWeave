# DevWeave Control Center

DevWeave Control Center 是以新手為先的 VS Code Extension。它把 DevWeave repository 的檔案狀態整理成五個區域：`總覽`、`工作項目`、`知識`、`驗證與稽核`、`說明`，讓你先知道目前狀態與下一步，再按需要查看治理細節。

## 先記住三件事

- Dashboard 是 filesystem snapshot，不是 engine 的權威狀態。完成 Codex Chat 操作後，請回到 Extension 按「重新整理檔案快照」。
- 初始化是唯一的 direct write：你在 modal 中確認後，Extension 才會套用固定 bootstrap bundle。它不覆寫衝突檔案，失敗時會 fail closed 或 rollback。
- 其他 `$devweave` 操作都是 prompt handoff：Extension 只產生、預覽並複製 prompt；你要到 Codex Chat 貼上、審閱並送出。

## 第一次使用

1. 在 VS Code 開啟 DevWeave repository，從 Activity Bar 開啟 DevWeave Control Center。
2. 若尚未初始化，按「初始化 DevWeave」並確認寫入範圍；若只完成部分初始化，按「初始化／補齊 DevWeave」。補齊只建立無衝突缺檔，不覆寫既有內容。完成後依提示確認 Codex hook、設定 verification commands，再建立第一個 work item。
3. 在「總覽」先看 repository state、目前工作、snapshot 來源、阻塞原因與主要 CTA。
4. 從「工作項目」分開查看進行中的 work 與已結束的歷史；closed work 只有在明確選取後才會顯示，不能被自動當成目前工作。
5. 選擇一個任務，按 Preview public command，確認「會做什麼／不會做什麼／複製後要做什麼」，再複製到 Codex Chat。

## 公開命令怎麼選

Dashboard 用任務語言分組，旁邊仍保留技術命令名稱：

- 開始工作：開始新工作（`new`）、新增功能（`feature`）、回報問題（`bug`）、整理程式（`refactor`）。
- 查看進度：查看目前狀態（`status`）、詢問下一步（`next`）。
- 審查決策：修改方向（`revise`）、核准目前階段（`approve`）。`approve` 會核准畫面標示的目前 gate，公開命令不加入 gate 參數；`revise` 可能讓既有 gate 或 evidence 失效。
- 建立知識：建立 Codebase Wiki（`$devweave wiki bootstrap`）。

九個公開 command 的 prompt text、sanitization、read-only/mutation 判斷保持原有 contract。Extension 不提供 machine CLI、任意 JSON intent、Git、branch、commit、push、PR 或直接 engine 執行。

## Wiki 與驗證

「知識」區域會顯示 Wiki health、bootstrap 建議、受影響或待更新頁面，並提供搜尋、分類與「顯示全部」入口。文字搜尋是標題／路徑／摘要的大小寫不敏感包含式查詢，輸入後按 Enter 才套用；分類是精確 type 篩選。Wiki bootstrap 有三個等價入口：

- 公開命令選單的「建立 Codebase Wiki」
- Knowledge 面板的 bootstrap CTA
- Command Palette 的 `DevWeave: 建立 Codebase Wiki（複製 prompt）`；舊版 technical label `DevWeave: Bootstrap Codebase Wiki` 對應同一個 command ID，方便既有文件辨識。

「驗證與稽核」區域會先顯示目前 gate、reviewer readiness、blocker、未完成 task、failed/stale evidence 與 Knowledge 待處理項目，再提供 command metadata、evidence、baseline/Wiki 詳細資料與可展開的 raw event。沒有 verification command/profile 時，介面會明確標示需要設定，不會宣稱已完成驗證。

## 顯示與操作

- 預設是「簡潔模式」；可切換「進階資訊」，偏好只儲存在 Extension 的 workspaceState，不寫入 repository。
- Multi-root workspace 選擇器會顯示 folder、未初始化／已管理／未啟用 managed 狀態與路徑。
- Webview 支援鍵盤 focus、ARIA live status、high contrast、reduced motion 與窄視窗；操作忙碌時會防止重複 refresh、copy 或 bootstrap。

## 設計邊界

- 平時只讀取 workspace filesystem snapshot，不呼叫 Python、shell、Git、network 或 Codex API。
- 唯一的 repository write 是使用者確認後的固定 bootstrap manifest；一般 prompt 操作不寫入 workspace。
- DevWeave engine、JSON contract、gates、evidence、baseline 與 Wiki 仍是權威來源。

## 開發與驗證

在 `vscode-extension/` 目錄執行：

```powershell
npm install
npm run typecheck
npm test
npm run package
npm run test:smoke
```

`npm run package` 會產生 0.2.0 production bundle、完整 bootstrap manifest 與 `devweave-control-center-0.2.0.vsix`；`npm run test:smoke` 會使用 VS Code Extension Host 驗證 activation、Activity Bar view 與公開 commands。

## 打包 VSIX

既有的 `devweave-control-center-0.1.0.vsix` 不會被覆寫；package verification 會檢查兩個 artifact、manifest integrity 與 VSIX 必要 entries。

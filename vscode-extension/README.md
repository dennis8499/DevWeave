# DevWeave Control Center

DevWeave Control Center 是以新手為先的 VS Code Extension。它把 DevWeave repository 的檔案狀態整理成五個區域：`總覽`、`工作項目`、`知識`、`驗證與稽核`、`說明`，讓你先知道目前狀態與下一步，再按需要查看治理細節。

本頁對應 DevWeave 0.2.1 Windows 公開版。正式支援 Windows、VS Code 1.90+、Python 3.11+、Git 與 Codex；交付方式是 repository 與 VSIX，不包含 Marketplace 上架，也不承諾 macOS/Linux 支援。

## 先記住三件事

- Dashboard 是 filesystem snapshot，不是 engine 的權威狀態。完成 Codex Chat 操作後，請回到 Extension 按「重新整理檔案快照」。
- 初始化是唯一的 direct write：你在 modal 中確認後，Extension 才會套用固定 bootstrap bundle。它不覆寫衝突檔案，失敗時會 fail closed 或 rollback。
- 其他 `$devweave` 操作都是 prompt handoff：Extension 只產生、預覽並複製 prompt；你要到 Codex Chat 貼上、審閱並送出。

## 第一次使用

1. 在 VS Code 開啟 DevWeave repository，從 Activity Bar 開啟 DevWeave Control Center。
2. 若尚未初始化，按「初始化 DevWeave」並確認寫入範圍；若只完成部分初始化，按「初始化／補齊 DevWeave」。補齊只建立無衝突缺檔，不覆寫既有內容。project、三份 baseline 與 Wiki starter 若已存在但內容符合 semantic contract，會顯示 adopted 而不是 false conflict；AGENTS、skills、hook 與其他 policy controls 仍採 exact bytes。完成後依提示確認 Codex hook、設定 verification commands，再建立第一個 work item。
3. 在「總覽」先看 repository state、目前工作、snapshot 來源、阻塞原因與主要 CTA。
4. 從「工作項目」分開查看進行中的 work 與已結束的歷史；closed work 只有在明確選取後才會顯示，不能被自動當成目前工作。
5. 選擇一個任務，按「預覽公開操作」，確認「會做什麼／不會做什麼／複製後要做什麼」，再複製到 Codex Chat。

## Windows 安裝 VSIX

1. 從 repository 取得 `vscode-extension/devweave-control-center-0.2.1.vsix`。
2. 在 VS Code 開啟 Extensions 視窗，按右上角 `...`，選擇「Install from VSIX…」，選取該檔案並等待安裝完成。
3. 重新載入 VS Code（若畫面提示需要 reload），再開啟 DevWeave repository，從 Activity Bar 選擇 DevWeave Control Center。

也可以在 Windows 終端執行 `code --install-extension vscode-extension/devweave-control-center-0.2.1.vsix`。VSIX 只支援本公開版的 Windows 範圍；本 release 不會自動從 Marketplace 更新。

## Preview、Codex handoff 與 Refresh

公開操作固定遵循這個順序：在 Control Center 選擇 work 或 task →「預覽公開操作」→確認 prompt 的目的、邊界與下一步→「複製 prompt」→到 Codex Chat 貼上、審閱並送出→回到 Extension 按「重新整理檔案快照」。

Preview 綁定目前 panel、操作 intent 與 workspace snapshot revision。Refresh、切換 work、初始化結果或檔案 snapshot 更新後，舊 preview 會失效，必須重新預覽；因此不會把過期 prompt 複製出去。複製時若 Windows clipboard 暫時失敗，該次 preview 會保留一次重試機會，成功後即消耗。

## Legacy command

既有 `devweave.copyNextAction` command ID 保留相容性，但現在只會開啟 Control Center：

- 只有一個 active work 時，自動開啟該 work 的 next action preview，仍需確認後才複製。
- 有多個 active work 時，必須先在 Control Center 明確選取 work；沒有 active work 時，畫面會引導建立或選取 work。
- `status` 可明確查詢全部 active work；`next` 在多 work 情況不會猜測目標。

## 公開命令怎麼選

Dashboard 用任務語言分組，旁邊仍保留技術命令名稱：

- 開始工作：開始新工作（`new`）、新增功能（`feature`）、回報問題（`bug`）、整理程式（`refactor`）。
- 查看進度：查看目前狀態（`status`）、詢問下一步（`next`）。
- 審查決策：修改方向（`revise`）、核准目前階段（`approve`）。`approve` 會核准畫面標示的目前 gate，公開命令不加入 gate 參數；`revise` 可能讓既有 gate 或 evidence 失效。
- 建立知識：建立 Codebase Wiki（`$devweave wiki bootstrap`）。

九個公開 command 的 prompt text、sanitization、read-only/mutation 判斷保持原有 contract。Extension 不提供 machine CLI、任意 JSON intent、Git、branch、commit、push、PR 或直接 engine 執行。

## Wiki 與驗證

初始化 bundle 的 Wiki 路徑採 reserved-starter compatibility：`wiki/index.md`、`wiki/overview.md`、`wiki/log.md` 只要求 regular file、正確 frontmatter type；既有自訂 Wiki 內容不會被覆寫。初始化前 Python engine 會先檢查 Wiki，reserved conflict 會阻止 partial `.devweave` state；Extension 則只在使用者確認後補齊 missing paths，並把合法 evolved project/baseline/Wiki bytes 投影為 adopted。

「知識」區域會顯示 Wiki health、bootstrap 建議、受影響或待更新頁面，並提供搜尋、分類與「顯示全部」入口。文字搜尋是標題／路徑／摘要的大小寫不敏感包含式查詢，輸入後按 Enter 才套用；分類是精確 type 篩選。Wiki bootstrap 有三個等價入口：

- 公開命令選單的「建立 Codebase Wiki」
- Knowledge 面板的 bootstrap CTA
- Command Palette 的 `DevWeave: 建立 Codebase Wiki（開啟預覽）`；舊版 technical label `DevWeave: Bootstrap Codebase Wiki` 對應同一個 command ID，方便既有文件辨識。

「驗證與稽核」區域會先顯示目前 gate、reviewer readiness、blocker、未完成 task、failed/stale evidence 與 Knowledge 待處理項目，再提供 command metadata、evidence、baseline/Wiki 詳細資料與可展開的 raw event。High-risk G3 另顯示 `Independent Review` readiness：missing、unavailable 或 advisory 是 attention，critical finding 是 not-ready；passed 且綁定目前 source 才會顯示 ready。Extension 只投影 snapshot、raw report path/hash 與 findings，不會啟動 Agent、執行 engine 或自行判定／核准 gate。沒有 verification command/profile 時，介面會明確標示需要設定，不會宣稱已完成驗證。

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

`npm run package` 會從 `package.json` 產生 0.2.1 production bundle、完整 bootstrap manifest 與 `devweave-control-center-0.2.1.vsix`；`npm run test:smoke` 會使用 VS Code Extension Host 驗證 activation、Activity Bar view 與公開 commands。Extension unit tests 目前為 73 項，全部通過。

## 打包 VSIX

既有的 `devweave-control-center-0.2.0.vsix` 與 `devweave-control-center-0.1.0.vsix` 不會被覆寫；package verification 會檢查 0.2.1 及兩個保留 artifact、manifest integrity 與 VSIX 必要 entries。需要回退時，可在 VS Code 重新安裝保留的 0.2.0 VSIX。

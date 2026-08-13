# DevWeave Control Center

DevWeave Control Center 是以新手為先的 VS Code Extension。它把 DevWeave repository 的檔案狀態整理成五個區域：`總覽`、`工作項目`、`知識`、`驗證與稽核`、`說明`，讓你先知道目前狀態與下一步，再按需要查看治理細節。

本頁對應 DevWeave 0.2.3 Windows 公開版；本次提供 0.2.3 VSIX，並保留 0.2.2 與 0.2.1 artifact。本次認證環境是 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host；本次實際基準為 Python full suite 111 項（1 項因 symlink 權限 skipped）與 Extension unit tests 88 項。VS Code 1.90+ 與 Python 3.11+ 只是技術門檻。交付方式是 repository 與 VSIX，不包含 Marketplace 上架，也不承諾 macOS/Linux 支援。

若發生發布事故，立即停止散布並停用或解除安裝 0.2.3；這些操作不會自動刪除 `.devweave`、Wiki 或 workspace 資料。保留 workspace snapshot 與 logs，0.2.2 與 0.2.1 artifact 可作為回溯參考，修復後產生新版本。

## 先記住三件事

- Dashboard 是 filesystem snapshot，不是 engine 的權威狀態。完成 Codex Chat 操作後，請回到 Extension 按「重新整理檔案快照」。
- 初始化是唯一的 direct write：你在 modal 中確認後，Extension 才會套用固定 bootstrap bundle。它不覆寫衝突檔案，失敗時會 fail closed 或 rollback。
- 其他 `$devweave` 操作都是 prompt handoff：Extension 只產生、預覽並複製 prompt；你要到 Codex Chat 貼上、審閱並送出。
- 所有 pre-G2 mutation prompt 都有 Plan Mode preflight handoff：請先切換 Plan Mode，再貼到 Codex Chat；Extension 不會嘗試切換 host mode，也不會新增 checkbox 或 host command。

## 第一次使用

1. 在 VS Code 開啟 DevWeave repository，從 Activity Bar 開啟 DevWeave Control Center。
2. 若尚未初始化，按「初始化 DevWeave」並確認寫入範圍；若只完成部分初始化，按「初始化／補齊 DevWeave」。補齊只建立無衝突缺檔，不覆寫既有內容。project、三份 baseline 與 Wiki starter 若已存在但內容符合 semantic contract，會顯示 adopted 而不是 false conflict；AGENTS、skills、hook 與其他 policy controls 仍採 exact bytes。完成後依提示確認 Codex hook、設定 verification commands，再建立第一個 work item。
3. 在「總覽」先看 repository state、目前工作、snapshot 來源、阻塞原因與主要 CTA。
4. 從「工作項目」分開查看進行中的 work 與已結束的歷史；closed work 只有在明確選取後才會顯示，不能被自動當成目前工作。
5. 選擇一個任務，按「預覽公開操作」，確認「會做什麼／不會做什麼／複製後要做什麼」，再複製到 Codex Chat。

## Windows 安裝 VSIX

1. 從 repository 取得 `vscode-extension/devweave-control-center-0.2.3.vsix`。
2. 在 VS Code 開啟 Extensions 視窗，按右上角 `...`，選擇「Install from VSIX…」，選取該檔案並等待安裝完成。
3. 重新載入 VS Code（若畫面提示需要 reload），再開啟 DevWeave repository，從 Activity Bar 選擇 DevWeave Control Center。

也可以在 Windows 終端執行 `code --install-extension vscode-extension/devweave-control-center-0.2.3.vsix`。本 release 不會自動從 Marketplace 更新。

## Windows PreToolUse 與 Doctor

`.codex/hooks.json` 是唯一的 repository hook contract：`PreToolUse` 使用 exact matcher `^(Bash|apply_patch|Edit|Write)$`，handler 同時宣告 POSIX `command` 與 Windows `commandWindows`，不依賴 `$repo` 或 shell-specific current-directory 假設。Windows path 使用 `powershell.exe -NoLogo -NoProfile -NonInteractive`，先設定不依賴 shell variable 的 .NET UTF-8 console input/output，再以 `py -3 -X utf8 -B` 由 Git root 定位 `guard.py`。

在 repository root 執行以下單行命令即可做環境診斷；CMD、Windows PowerShell 5.1、PowerShell 7 與 VS Code terminal 都使用同一行：

`py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py doctor`

Doctor 會檢查 Python、Git、`py -3`、`cmd.exe`、Windows PowerShell 5.1、PowerShell 7、hook schema，以及 root／`vscode-extension` nested cwd 的 launcher probe。若是 launcher failure，先修復 PATH、Python launcher、Git 或缺少的 shell；若 launcher 成功但工具被拒絕，則是 gate、scope 或 Wiki policy deny。這個 hook 是 Codex guardrail，不是 Windows OS sandbox；hosted、global 或 plugin-owned tool path 不在本 repository hook 的保證範圍。

## Preview、Codex handoff 與 Refresh

公開操作固定遵循這個順序：在 Control Center 選擇 work 或 task →「預覽公開操作」→確認 prompt 的目的、邊界與下一步→「複製 prompt」→到 Codex Chat 貼上、審閱並送出→回到 Extension 按「重新整理檔案快照」。

如果 preview 或 copied result 顯示 Plan Mode handoff，請先切換 Plan Mode，再貼到 Codex Chat；這是 Router 的 mutation 前置條件提示，仍可複製 prompt，Extension 不會讀取或切換 Codex host mode。

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

Verification metrics 會在 evidence 的 bounded projection 中顯示 duration、profile selected/skipped 與 usage availability。`usage.status=unavailable` 是合法且預期的結果：Extension 不接觸 Codex host token/cost，也不從 snapshot bytes 猜測 Token。要降低低風險驗證成本，可在 CLI 以 `verify --profile low|standard --path <repo-relative-path>` 做 affected-path selection；high profile 仍保留完整 package、smoke 與 Python suite coverage。選擇器會顯示跳過原因與 dependency closure，release-only package 不會因間接依賴被非 high profile 執行。

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
npx --yes @vscode/vsce package --allow-missing-repository
```

`npm run package` 會從 `package.json` 產生 0.2.3 production bundle 與完整 bootstrap manifest，接著以 `package-vsix.mjs --output <candidate.vsix>` 建立同目錄 candidate，交由 `verify-package.mjs --artifact <candidate.vsix>` 檢查後才 promotion current artifact。Verifier 或 promotion 失敗時保留 current 與 0.2.2／0.2.1 retained artifacts，candidate 只做 best-effort cleanup；`npm run test:smoke` 會使用 accepted VS Code 1.131.0 cache 驗證 activation、Activity Bar view 與公開 commands。Extension unit tests 與 package evidence 以本次實際結果為準。

## 打包 VSIX

Package verification 必須明確接收 `--artifact`，只讀取 extension root 內的 candidate；builder 必須明確接收 `--output`，並以 `wx` 防止覆寫。Verifier 會檢查 package／bundle version、58 個 bootstrap files、119 個 VSIX entries、必要 entries、source byte length／SHA-256、candidate VSIX SHA-256，以及嵌入 hook 與 root `.codex/hooks.json` 的一致性。Release transaction 只有在 candidate 通過驗證後才同目錄 atomic rename promotion current；既有 0.2.2 與 0.2.1 VSIX 保留作為 retained artifacts，其他 VSIX 不是本次封裝、驗收或回復條件。

# 工作摘要：Windows 跨 Shell PreToolUse 與工具呼叫相容性

<!-- DEVWEAVE:artifact=brief version=1 work=20260810-130022-feature-openai-hooks-windows-shell-pretooluse kind=feature -->

## 問題與目標

目前 repository 的 `.codex/hooks.json` 只有一條 Windows-oriented `command`，把 PowerShell launcher 當成所有 Codex command runner 的共同入口，且沒有依 OpenAI Hooks contract 分開宣告 Windows adapter。這使實際執行邊界、Python launcher 版本、UTF-8 transport、Codex matcher 覆蓋範圍與 VS Code source-derived bootstrap contract 不夠明確；operator 也缺少一個能直接顯示 Windows 先決條件與實際 launcher probe 的 doctor。

本工作要把 DevWeave 的本地工具呼叫與單一 `PreToolUse` guard 固定成可驗證的跨 Windows shell contract：精確匹配 repository 可理解的 mutation/read tools；提供 POSIX fallback `command` 與 Windows 專用 `commandWindows`；以 `py -3` 啟動固定 Python 3；維持 guard 的 raw UTF-8、fail-closed、deny JSON 與 process exit semantics；並讓 CMD、Windows PowerShell 5.1、PowerShell 7 及 VS Code integrated terminal 可用同一份 source-derived bootstrap。Extension 版本升至 0.2.3，保留 0.2.2 artifact。

## 現況證據

### Wiki facts

- `wiki/index.md` 要求 G1 先讀 index，再讀最多五個相關頁面；本工作已記錄 `wiki/index.md`、`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md` 與 `wiki/modules/vscode-extension.md` 的 ordered context、content hash、stored/computed source fingerprint。
- 既有 Wiki 描述單一 `PreToolUse` guard、Git-root resolution、UTF-8 bytes、policy deny 與 process failure 的分層，以及 Extension 只從根目錄 hook 產生 bootstrap、不能靜默覆寫 workspace hook。
- Wiki 也記錄 current-only VSIX verifier、58 個 bootstrap files、119 個 VSIX entries 與現有 0.2.2 release boundary；這些資料會在 G3 由新的 0.2.3 source evidence 取代或刷新。

### Source-backed facts

- `.codex/hooks.json` 現在只有一個 `PreToolUse` group，matcher 為 `^(Bash|apply_patch|Edit|Write)$`，沒有 `timeout` 或 `commandWindows`。
- `.agents/skills/devweave/scripts/guard.py` 以 `sys.stdin.buffer`／`sys.stdout.buffer` 直接 UTF-8 bytes 讀寫；malformed input 或未預期例外會輸出 deny JSON 並以 exit 0 結束。現有 `_is_devweave_cli` 已接受 `py`／`py.exe` 與 `-3` 旗標。
- `doctor` 目前只檢查目前 Python interpreter、Git、project、skill、hook、configured commands 與 Wiki compatibility，沒有 Windows shell/`py -3`/launcher probe matrix。
- `vscode-extension/esbuild.mjs` 會把根目錄 `.codex/hooks.json` source-derive 到 bootstrap；package、lock、verifier、package-version/bootstrap tests 與 help/README 仍固定 0.2.2 且 verifier 目前拒絕 `commandWindows`。
- 現有 repository contract 已有 root/nested cwd、CMD、Windows PowerShell、raw UTF-8、malformed JSON 與 read-only Bash silence 的 process tests，可擴充到 `commandWindows`、PowerShell 7 與同一 launcher matrix。

### Inferences

- 既有 guard policy、JSON decision schema 與 `esbuild` source-derived seam 可以保留；主要變更集中在 hook wire configuration、doctor diagnostics、contract tests、release metadata 與治理文件。
- Windows shell 相容性最可靠的證據必須是 child-process matrix，而不是只檢查 JSON 字串；root 與 nested cwd、非 ASCII payload、正常 allow/deny 與 launcher failure 需要分別觀察。
- high-risk review 必須檢查 hook matcher 是否精確、`commandWindows` 是否只作 Windows adapter、missing runtime 是否 fail closed，以及 Extension bundle 是否與根 hook 完全一致。

### Unresolved gaps

- 四個非 index Wiki page 的 stored source fingerprint 已過期；本工作已先登記 gap，再以上述最小 source ranges 補查。G3 必須刷新受影響頁面與 coupled index/log，不能把 stale Wiki 當成 current source truth。
- 目前 repository 尚未有正式的 `commandWindows` package/verifier contract，也未由 doctor 報告 VS Code integrated terminal 的可操作 guidance；具體 cross-shell probe implementation 留到 G2 design。
- VS Code integrated terminal 的 profile 啟動與 Codex host trust 不是 Python engine 可自動證明的狀態；需在 G3 保留 manual walkthrough marker，並以 doctor/child-process evidence 證明 repository 可提供的部分。

## 範圍

- `.codex/hooks.json`：單一 `PreToolUse`、精確 matcher、`timeout`、status message、POSIX `command` 與 Windows `commandWindows`。
- guard/engine contract：保留 `guard.py` 的 policy、UTF-8 bytes、deny JSON 與 exit semantics；擴充 `doctor` 的 Windows prerequisites、trust/launcher guidance 與實際 probe。
- Python repository contract tests：覆蓋 CMD、Windows PowerShell 5.1、PowerShell 7、root/nested cwd、raw UTF-8、malformed JSON、read-only silence 與 normal logical result。
- VS Code source-derived release：`package.json`、`package-lock.json`、verifier、unit/package tests、embedded help/README 與 current 0.2.3 VSIX；保留 0.2.2 artifact，58/119 integrity counts 若 manifest 未增加檔案則維持。
- `README.md`、`docs/使用手冊.md`、root `AGENTS.md`、accepted baselines 與四個受影響 Wiki content pages、index/log；文件中的 operator command 改為可在 CMD、Windows PowerShell 5.1、PowerShell 7 與 VS Code terminal 貼上的單行形式。
- high-risk G3 所需的 current tests、package/smoke/typecheck、doctor、diff、Wiki promotion/seal、baseline 更新與 exactly-one isolated read-only reviewer。

## 非目標

- 不改變 `guard.py` 的 allow/deny policy、hook JSON decision schema、work binding、G1/G2/G3 gate 或 fail-closed safety；不以相容性為由放寬未綁定、未核准 G2、scope 或 Wiki restrictions。
- 不用 wildcard matcher；不攔截 hosted tools、外部/global/plugin hooks，也不宣稱 repository hook 是 OS sandbox。
- 不新增 `PermissionRequest`、`PostToolUse`、`SessionStart`、`Stop` 等事件，不建立 fake `request_user_input`、host mode adapter、second router、CLI schema/ledger 欄位或自動安裝 Python/Git/PowerShell。
- 不修改 Codex host、VS Code terminal profile、Windows execution policy、使用者 PATH 或全域設定；VS Code Extension 不執行 shell/Python/Git/network。
- 不建立 branch、worktree、commit、push、issue、PR、deployment 或 production instrumentation。
- 不移除 0.2.2 VSIX，不驗證舊版作為 current package，也不把 VS Code integrated terminal manual check 假裝成 engine 自動 evidence。

## 風險

風險等級：high

- Hook configuration 是 public security boundary；matcher、launcher quoting、Git-root resolution 或 timeout 錯誤可能造成工具呼叫失敗、guard bypass 或不必要阻擋。
- `commandWindows` 與 POSIX `command` 必須保持同一 stdin/stdout contract；Windows 不同 shell 的 quoting 與 code page 可能讓非 ASCII payload 被破壞。
- `doctor` 若以 caller shell 推測能力，可能在 VS Code 或 PowerShell 版本間產生假陽性；必須以可辨識的 executable probes 與實際 launcher probe 回報 diagnostics。
- Extension bootstrap、VSIX verifier、文件與 Wiki 必須同步；release version 不一致會使 source-derived installation fail closed。
- 因涉及安全、public hook protocol、cross-process matrix 與 release artifact，G3 需由既有 router 啟動 exactly one isolated read-only Independent Review Agent，並由人員進行最終 Gate approval。

## 已回答的 material decisions

- 相容性：使用者已選擇完整 Windows 矩陣，正式涵蓋 CMD、Windows PowerShell 5.1、PowerShell 7 與 VS Code integrated terminals；外部 host/global/plugin hooks 在 boundary 外。
- matcher：使用精確的可理解工具集合 `Bash|apply_patch|Edit|Write`，未來 MCP mutation 只有明確列舉才加入。
- launcher：使用官方雙路徑設定，保留 POSIX `command`，另提供 Windows-specific `commandWindows`；不以未宣告的 wildcard 或 shell-specific workaround 取代 hook schema。
- events：只強化必要的 `PreToolUse`，不新增其他 hook events。
- Windows Python：以 `py -3` 固定 Python 3；缺少 launcher/runtime 時 doctor 顯示診斷，hook 不因 logical deny 變成 process failure。
- Extension：升至 0.2.3，保留 0.2.2 artifact；verifier 只驗證 current artifact。
- operator surface：提供單行跨 shell 命令與 doctor matrix，避免依賴 PowerShell backtick 多行貼上。

# 需求與驗收條件：Windows 跨 Shell PreToolUse 與工具呼叫相容性

<!-- DEVWEAVE:artifact=requirements version=1 work=20260810-130022-feature-openai-hooks-windows-shell-pretooluse -->

## 假設與限制

- 本工作是 `feature`、`high` risk；既有 DevWeave lifecycle、CLI JSON envelope、guard decision schema、G1/G2/G3 gates 與 source-derived Extension bootstrap seam 維持有效。
- 正式相容性範圍是原生 Windows 的 CMD、Windows PowerShell 5.1、PowerShell 7，以及從 VS Code integrated terminal 使用上述 profiles 的操作；Python 3.11+、Git、Codex repository trust 是先決條件。
- `command` 是 POSIX fallback，`commandWindows` 是 Windows-specific adapter；兩者必須將同一份 Codex stdin JSON 交給同一個 `guard.py`，不維護第二套 policy。
- Codex hook matcher 只涵蓋 DevWeave 可判讀的 `Bash`、`apply_patch`、`Edit`、`Write`；hosted tools、外部/global/plugin hooks 與未列舉的 MCP mutation 不在本次 local hook contract。
- Wiki 在 verification 前 read-only；G3 由 Knowledge Review 選擇 `promote`，最多更新四個受影響 content pages，並同步 `wiki/index.md`、`wiki/log.md` 與 seals。既有 stale page 必須先以 gap 解釋，不能以 Wiki inference 覆蓋 source evidence。
- 0.2.3 是 current Extension release；0.2.2 artifact 保留。Manifest 未增加 bootstrap files 時維持 58 個 files 與 119 個 VSIX entries，所有 counts 以實際 build evidence 為準。

## 需求與驗收條件

## REQ-001: PreToolUse matcher 必須精確且可追溯

- Priority: must
- Acceptance: AC-001, AC-007
- Description: `.codex/hooks.json` 必須只有必要的 `PreToolUse` guard group，matcher 精確覆蓋 `Bash`、`apply_patch`、`Edit`、`Write`，不得使用 wildcard；command handler 必須包含明確 timeout 與 status message，並保留 repository trust guidance。

## REQ-002: Hook 提供雙路徑 launcher 並以 Git root 定位 guard

- Priority: must
- Acceptance: AC-002, AC-003, AC-005
- Description: hook command 必須提供 POSIX `command` 與 Windows `commandWindows`；Windows adapter 以 `powershell.exe -NoLogo -NoProfile -NonInteractive` 呼叫 `py -3 -X utf8 -B`，由 `git rev-parse --show-toplevel` 導向 `.agents/skills/devweave/scripts/guard.py`，不得依賴 current cwd、`$repo` 或 PowerShell profile。

## REQ-003: Guard transport 與 policy semantics 維持 fail-closed

- Priority: must
- Acceptance: AC-003, AC-007
- Description: `guard.py` 必須繼續以 raw UTF-8 bytes 讀取/輸出 hook JSON；正常 allow、policy deny、malformed JSON 與未預期例外均須遵守既有 stdout/exit contract，malformed/exception 不得放行，且不得把正常 logical deny 變成 non-zero process failure。

## REQ-004: Windows child-process matrix 必須驗證實際 launcher

- Priority: must
- Acceptance: AC-002, AC-003
- Description: repository contract 必須實際啟動 `commandWindows`，至少涵蓋 `cmd.exe /d /s /c`、Windows PowerShell 5.1 與 `pwsh`；每個 runner 都要在 repository root 與 `vscode-extension` nested cwd 驗證，並測試繁中 raw UTF-8 payload、unbound Write deny、malformed JSON deny、read-only Bash silence 與 normal logical result 的 exit/JSON 行為。

## REQ-005: Doctor 顯示可操作的 Windows prerequisites 與 launcher probe

- Priority: must
- Acceptance: AC-004, AC-007
- Description: `devweave doctor` 必須在不寫入 repository 的前提下檢查 `py -3`、Git、`cmd.exe`、Windows PowerShell 5.1、PowerShell 7 的 availability，顯示 Codex hook trust/schema guidance，並使用實際 hook launcher probe 回報 success/failure；缺少必要 runtime 時回報明確診斷，不以猜測宣稱相容。

## REQ-006: Source-derived Extension release 與 current-only verifier 一致

- Priority: must
- Acceptance: AC-005, AC-006
- Description: `vscode-extension` package/lock、bootstrap manifest、verifier、unit tests、README/help 與 current VSIX 必須一致使用 0.2.3；verifier 必須檢查 root hook 與 embedded hook 的雙路徑 semantic contract、version、hash/length、required entries、current artifact，並保留 0.2.2 artifact。

## REQ-007: Operator 文件說明四種 Windows 執行環境與邊界

- Priority: must
- Acceptance: AC-006
- Description: README、繁中使用手冊、root `AGENTS.md`、accepted baselines、受影響 Wiki 與 Extension help 必須說明 CMD、Windows PowerShell 5.1、PowerShell 7、VS Code integrated terminal 的 one-line operation、`py -3`/Git prerequisites、hook trust、doctor、launcher failure 與 policy deny 的區別，以及 hook 不是 OS sandbox 的限制。

## NFR-001: 不放寬安全與範圍邊界

- Priority: must
- Acceptance: AC-001, AC-003, AC-007
- Description: 實作不得新增 wildcard matcher、其他 hook events、hosted-tool interception、fake host adapter、global configuration、CLI/schema/ledger field 或 bypass；未綁定 work、未通過 G2、scope 外與 Wiki 違規寫入的既有 deny 行為必須維持。

## NFR-002: 跨 shell 可重現且 UTF-8 保真

- Priority: must
- Acceptance: AC-002, AC-003, AC-004
- Description: launcher 不得依賴 profile、shell variable、current cwd 或多行貼上狀態；root/nested cwd 與 raw Chinese payload 必須有 deterministic process-level evidence，doctor 輸出需能讓 operator 判斷缺少哪個 executable 或 trust step。

## NFR-003: Release 可逆且 source-derived

- Priority: must
- Acceptance: AC-005, AC-006
- Description: Extension build 只由 current source 產生 0.2.3；既有 0.2.2 artifact 不得被刪除或當作 current input，VSIX integrity failure 必須 fail closed，且 runtime 不新增 child process、shell、network 或 workspace write seam。

## AC-001: Hook schema 僅保護精確可理解工具

- Requirement: REQ-001, NFR-001
- Scenario: Given root `.codex/hooks.json`，When repository contract inspect hook schema，Then 只有一個 `PreToolUse` handler，matcher exact 覆蓋 `Bash`、`apply_patch`、`Edit`、`Write`，有 timeout/status message，沒有 wildcard 或額外 events。

## AC-002: 四種 Windows terminal path 都能啟動 Windows adapter

- Requirement: REQ-002, REQ-004, NFR-002
- Scenario: Given managed repository、root 或 `vscode-extension` cwd 與 valid UTF-8 hook payload，When 由 `cmd.exe /d /s /c`、Windows PowerShell 5.1、PowerShell 7，或 VS Code terminal profile 執行相同 one-line Windows adapter，Then launcher 能從 Git root 找到 `guard.py`，process 啟動成功，payload 不因 shell quoting 或 code page 遺失。

## AC-003: Logical deny、malformed input 與 read-only allow 的 process contract 不變

- Requirement: REQ-003, REQ-004, NFR-001, NFR-002
- Scenario: Given unbound `Write`、含繁中 path 的 policy deny、malformed JSON、以及 read-only `Bash`，When hook 由各 Windows runner 執行，Then deny cases 輸出合法 UTF-8 `hookSpecificOutput.permissionDecision=deny`、read-only allow 保持空 stdout，所有正常 logical results exit 0；malformed/exception 不得放行。

## AC-004: Doctor 會揭露缺少 executable 或 launcher 問題

- Requirement: REQ-005, NFR-002
- Scenario: Given Windows environment with some of `py -3`、Git、`cmd.exe`、Windows PowerShell 5.1、PowerShell 7 missing or unavailable，When operator runs the documented one-line `doctor` command，Then report contains named checks、可理解 detail、hook trust/schema guidance 與 launcher probe result；完整環境則 report `ok=true` 並列出每項通過。

## AC-005: 0.2.3 source-derived package 與 root hook 完全一致

- Requirement: REQ-002, REQ-006, NFR-003
- Scenario: Given current source and retained 0.2.2 artifact，When `npm.cmd run package` and verifier execute，Then current package/bundle/VSIX version is 0.2.3，embedded hook matches root dual-path contract，required entries/hash/length/counts pass，0.2.2 remains present and is not used as current input。

## AC-006: 文件與 Wiki 對 operator 邊界一致

- Requirement: REQ-006, REQ-007, NFR-003
- Scenario: Given final verified source，When repository contract and Knowledge Review inspect release/help/README/AGENTS/baseline/Wiki，Then all current surfaces describe the same four-terminal Windows scope、one-line commands、`py -3` prerequisites、trust、doctor、policy/process distinction、0.2.3 current/0.2.2 retained，且 Wiki promotion 不超過四個 content pages 並同步 index/log/seal。

## AC-007: 全套既有與新增驗證無安全回歸

- Requirement: REQ-001, REQ-003, REQ-005, NFR-001
- Scenario: Given final product/Wiki/baseline diff，When Python full suite、repository contract、doctor、Extension unit/typecheck/package/smoke、VSIX verifier、launcher matrix、`git diff --check` 與 high-risk isolated review execute，Then all required evidence is current and passing，除明確 advisory warning 外沒有 critical finding，且 G3 human approval remains required。

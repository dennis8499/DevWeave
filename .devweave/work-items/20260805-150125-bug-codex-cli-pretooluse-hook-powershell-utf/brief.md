# 工作摘要：修正 Codex CLI PreToolUse Hook 的 PowerShell 與 UTF-8 失敗

<!-- DEVWEAVE:artifact=brief version=1 work=20260805-150125-bug-codex-cli-pretooluse-hook-powershell-utf kind=bug -->

## 問題與目標

Codex CLI 執行 repository 的 `PreToolUse` hook 時，Windows PowerShell runner
會讓目前的 launcher 以 exit code 1 結束，因而顯示 `PreToolUse hook (failed)`，
即使 DevWeave guard 的本意只是回傳正常的 policy deny。目標是讓同一個
repository-managed hook 在 Codex 的 Windows `cmd.exe` 與 PowerShell 外層都能
穩定啟動，正確處理繁體中文路徑與 UTF-8 hook payload，並保留既有 allow/deny
政策與 `permissionDecision` JSON 契約。

成功訊號：launcher 在兩種 Windows runner 下都以 exit code 0 結束並輸出可解析
的 hook JSON；未綁定寫入仍為 `deny`，唯讀操作仍不產生不必要的阻擋；package
bootstrap、repository contract 與完整回歸測試均通過。

## 現況證據

### Wiki facts

本 Work Item 已依 index-first 規則記錄 `wiki/index.md`、
`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、
`wiki/modules/knowledge-engine.md` 與 `wiki/modules/vscode-extension.md`。
目前頁面共同描述「標準 `command` 經 `cmd.exe` 啟動 PowerShell、guard deny
仍 exit 0」，但沒有描述 PowerShell 外層 runner 的 quoting 或 UTF-8 stdin
邊界。

### Source-backed facts and failing reproduction

1. `.codex/hooks.json` 目前以巢狀 PowerShell command 使用 `$repo`：
   `powershell -NoProfile -Command "$repo = git rev-parse --show-toplevel; python -B (Join-Path $repo '.agents\\skills\\devweave\\scripts\\guard.py')"`。
   以 `cmd.exe /d /s /c` 執行可得到 exit 0 與 deny JSON；以 PowerShell 作為
   外層 runner 時，外層先展開 `$repo`，造成 `= : The term '=' is not recognized`
   並使 launcher exit 1。
2. `guard.py` 以 `json.load(sys.stdin)` 讀取 hook input。Windows 非 UTF-8
   console stdin 可能是 CP950；直接傳入含 `C:\\Users\\小豬的電腦` 的 raw UTF-8
   JSON 時，現行程式會解析失敗並回傳錯誤 deny；ASCII escaped JSON 則可通過。
3. guard 的正常 policy deny 已約定為合法 JSON、process exit 0；本修正不得
   把 policy 結果與 launcher process failure 混在一起。

### Inferences

根因是 launcher 依賴 shell 變數在多層 Windows quoting 下的展開，以及 guard
把 hook transport encoding 交給 host console encoding。用不含 shell variable
的 Git-root expression 加上明確 UTF-8 stdin/stdout，能在不變更 guard policy
schema 的前提下收斂兩個失敗面。

### Unresolved gaps

Codex host 是否在每個版本與啟動方式都使用相同的 Windows shell invocation
仍屬外部 host 行為；本 Work Item 以官方 hook runner contract、兩種本機
process-level runner 測試與 package source consistency 作為可重現的相容性界線。

## 範圍

本工作項包含：

- 修正 `.codex/hooks.json` 的 Windows launcher，使 command 不依賴外層
  PowerShell 會誤展開的變數，並明確要求 `powershell.exe`、UTF-8、非互動模式。
- 修正 `.agents/skills/devweave/scripts/guard.py` 的 hook input/output
  encoding 邊界；解析失敗時仍輸出合法 deny JSON 並 exit 0。
- 擴充 `tests/test_repository_contract.py` 的 process-level regression，涵蓋
  `cmd.exe`、PowerShell、repository root/subdirectory、ASCII/繁中 payload、
  allow/deny 與 malformed input。
- 更新 `vscode-extension/scripts/verify-package.mjs`、使用手冊與 source-bound
  Wiki，讓 bootstrap/package contract 與實際 launcher 一致；重建 0.2.1 package。

## 非目標

不修改 Codex CLI、Windows/PowerShell、Python runtime 或 OS code page；不新增
`commandWindows` 平行設定、不改變 guard policy JSON schema、不放寬未綁定或未
通過 G2 的寫入政策；不處理 VS Code UI、DevWeave lifecycle schema、其他平台
shell、branch/worktree/commit/push、發布流程或既有無關測試失敗。

## 風險

風險等級：high

本變更觸及 Codex public hook/bootstrap control，且錯誤處理若不慎可能讓
安全 guard 失效，因此維持 high risk。主要風險是 Windows shell quoting、
console encoding 與 package 內嵌來源不一致；以雙 runner process regression、
UTF-8 raw payload、package verifier、完整 Python/Extension tests 與 high-risk
independent review 降低風險。來源修改可透過回復同一組 hook/guard/test/package
檔案撤回，且不需要資料 migration。

## Profile 補充

Profile：bug。

- Expected：Codex Windows hook launcher 對正常 policy result 以 exit 0 回傳
  可解析 JSON。
- Actual：PowerShell 外層執行現行 command 時 launcher exit 1；raw UTF-8
  中文 payload 也可能被 CP950 stdin 錯誤解析。
- Root-cause hypothesis：巢狀 `$repo` 造成 PowerShell re-expansion，且
  `json.load(sys.stdin)` 未固定 transport encoding。
- Failing reproduction：已在 G1 以現行 source 的 cmd/PowerShell process probe
  重現，並將失敗結果記錄為 Work Item evidence；修正後必須以同一 process
  seam 產生 green regression。

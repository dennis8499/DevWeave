# 工作摘要：修正 Windows Codex PreToolUse Hook 失敗

<!-- DEVWEAVE:artifact=brief version=1 work=20260805-104700-bug-windows-codex-pretooluse-hook kind=bug -->

## 問題與目標

在原生 Windows Codex 中執行本 repository 的 Bash、apply_patch、Edit 或 Write 時，會看到 `PreToolUse hook (failed)` 與 `hook exited with code 1`。目標是讓 Codex 能成功啟動 DevWeave guard，恢復受保護操作的正常 allow/deny 流程；成功訊號是 hook process 正常完成，真正不被允許的寫入改以 DevWeave JSON policy denial 回報。

## 現況證據

### Wiki facts

- `wiki/index.md` 指向 `wiki/modules/vscode-extension.md` 與 `wiki/modules/knowledge-engine.md`；兩頁都記錄 0.2.1 是 Windows 公開版、bootstrap 會攜帶 hook，且 Extension bundle 由 source-derived manifest 產生。
- 本次已先記錄 index-first context：`wiki/index.md`、`wiki/overview.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`；沒有發現 gap。

### Source-backed facts

- `.codex/hooks.json` 的標準 `command` 使用 `python3 "$(git rev-parse --show-toplevel)/..."`，另有未被目前 Codex runner 採用的 `commandWindows`。
- Windows 下目前 Codex command hook 使用 `cmd.exe /C` 執行標準 `command`；`cmd.exe` 不理解 `$()`。在本機以 `cmd.exe /d /s /c` 重現原命令會失敗；PowerShell launcher 可成功啟動 `guard.py`。
- `guard.py` 的 `main()` 對邏輯拒絕輸出 JSON 並返回 0，因此目前的 process failure 發生在 launcher，不是 DevWeave gate decision。
- `vscode-extension/esbuild.mjs` 會直接複製根目錄 `.codex/hooks.json` 到 bootstrap；`vscode-extension/scripts/verify-package.mjs` 與 0.2.1 VSIX 是 release 驗證面。

### Inferences

- 根因是 canonical hook command 與 Windows shell 不相容；修正標準 `command` 即可保留 guard 邏輯與 JSON protocol。

### Unresolved gaps

- 尚未以修正後的 source 啟動新 Codex session 驗證 UI 顯示；列入 G3 acceptance。

## 範圍

更新 `.codex/hooks.json` 的 Windows-first launcher，移除 `commandWindows`；新增 repository contract 的 process-level hook regression；更新 hook troubleshooting 文件；重建 source-derived 0.2.1 bootstrap/VSIX 並驗證 legacy VSIX 保持不變；G3 時 promote `wiki/modules/vscode-extension.md` 並同步 index/log。

## 非目標

不修改 `.agents/skills/devweave/scripts/guard.py`、DevWeave gate 規則、stdin/stdout JSON schema、CLI/state/evidence ledger 或寫入安全政策；不新增 WSL、macOS、Linux 支援；不由 Extension 靜默覆寫既有 workspace 的 exact `.codex/hooks.json`。

## 風險

風險等級：high

此變更位於 Codex 寫入 guard 的啟動接縫；launcher 失敗會讓受保護操作全部失去可靠的 policy evaluation。變更集中在 command adapter，guard 行為不變，可由 source diff、cmd.exe smoke、Python guard tests、Extension package、VSIX verifier 與完整 Windows verification 回復／驗證。0.1.0 與 0.2.0 VSIX 必須保留原 bytes/hash。

## Profile 補充

### Bug profile

- Expected：Windows Codex 執行 PreToolUse hook，hook process 正常完成；不允許的操作收到 `permissionDecision: deny`。
- Actual：Codex 顯示 `PreToolUse hook (failed)`／`hook exited with code 1`。
- Reproduction：由 Codex Windows runner 以 `cmd.exe /C` 執行目前 `.codex/hooks.json` 的標準 Unix command；`$()` 路徑替換不生效，hook launcher 失敗。
- Root-cause hypothesis：標準 `command` 應改為 PowerShell launcher；`commandWindows` 不是可依賴的 Codex platform override。

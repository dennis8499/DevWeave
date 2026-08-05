# 需求與驗收條件：修正 Windows Codex PreToolUse Hook 失敗

<!-- DEVWEAVE:artifact=requirements version=1 work=20260805-104700-bug-windows-codex-pretooluse-hook -->

## 假設與限制

本工作採使用者已確認的 Windows-first 策略；正式 acceptance 只涵蓋原生 Windows、Python 3.11+、Git 與 Codex。Codex 經標準 `command` 以 Windows shell 啟動 hook；既有 guard JSON contract 與 DevWeave policy 不變。

## 需求與驗收條件

## REQ-001: Windows Codex 可啟動 DevWeave guard

- Priority: must
- Acceptance: AC-001
- Description: `.codex/hooks.json` 的標準 `command` 必須由 `cmd.exe /d /s /c` 啟動 PowerShell，從 Git root 找到並執行 `guard.py`；不得依賴未被 Codex 採用的 `commandWindows` 欄位。

## REQ-002: 保留既有 allow/deny policy contract

- Priority: must
- Acceptance: AC-002
- Description: launcher 修正不得改變 `guard.py` 的 stdin JSON、stdout `hookSpecificOutput` 或 DevWeave gate 判定；正常 allow 與 policy deny 都必須以 process exit code 0 完成。

## REQ-003: Bootstrap 與 release artifact 使用修正後 hook

- Priority: must
- Acceptance: AC-003
- Description: source-derived bootstrap manifest、嵌入 0.2.1 VSIX 的 hook 與根目錄 `.codex/hooks.json` 必須一致；0.1.0／0.2.0 legacy VSIX bytes/hash 不得變動。

## NFR-001: 可驗證的 process-level regression

- Priority: must
- Acceptance: AC-004
- Description: repository contract test 必須透過 Windows `cmd.exe` 實際執行 hook，驗證成功 exit、合法 hook output，以及未綁定寫入仍為 JSON `permissionDecision: deny` 而非 process failure。

## NFR-002: 使用者可理解的 failure distinction

- Priority: should
- Acceptance: AC-005
- Description: 使用手冊必須區分 launcher/process failure 與 DevWeave policy denial，並說明重新啟動／信任 hook 與既有 exact bootstrap 的更新邊界。

## AC-001: Windows launcher smoke

- Requirement: REQ-001
- Scenario: Given repository root、Git、Python 與修正後 `.codex/hooks.json`，When `cmd.exe /d /s /c` 執行標準 hook command，Then process exit code 為 0 且 `guard.py` 被成功啟動。

## AC-002: Policy denial remains JSON

- Requirement: REQ-002
- Scenario: Given managed repository 中沒有 bound active work，When hook 收到未綁定 Write payload，Then process exit code 為 0、stdout 是合法 JSON 且 `hookSpecificOutput.permissionDecision` 為 `deny`。

## AC-003: Package source consistency

- Requirement: REQ-003
- Scenario: Given regenerated 0.2.1 production package，When package verifier 讀取 bootstrap manifest 與 VSIX，Then embedded hook 使用修正後 command，source hash/byte length 一致，且 legacy artifact hash 維持固定值。

## AC-004: Regression suite

- Requirement: NFR-001
- Scenario: Given repository contract、guard unit tests、Extension tests、typecheck、package 與 smoke suite，When 完整 high-risk verification 執行，Then 所有必要命令通過且 `git diff --check` 無錯誤。

## AC-005: Troubleshooting contract

- Requirement: NFR-002
- Scenario: Given 使用者遇到 hook 問題，When 閱讀使用手冊 hook section，Then 可區分 process failed 與 policy deny，並知道 exact bootstrap 不會被 Extension 靜默覆寫。

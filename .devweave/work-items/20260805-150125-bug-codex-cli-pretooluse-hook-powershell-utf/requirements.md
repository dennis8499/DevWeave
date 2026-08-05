# 需求與驗收條件：修正 Codex CLI PreToolUse Hook 的 PowerShell 與 UTF-8 失敗

<!-- DEVWEAVE:artifact=requirements version=1 work=20260805-150125-bug-codex-cli-pretooluse-hook-powershell-utf -->

## 假設與限制

1. 以目前 Codex 官方 Windows hook runner 可觀察到的 `command` execution
   contract 作為支援界線；不以本機不能取得的 host session metadata 猜測
   其他 invocation。
2. 需要相容 Windows Python 3.11+、PowerShell 與 `cmd.exe`，並維持 stdlib-only
   guard、既有 hook JSON envelope、既有 DevWeave policy 與 root/subdirectory
   `cwd` resolution。
3. 使用者已選定單一 shell-neutral `command` 與 explicit UTF-8 hardening；
   `commandWindows` 不納入方案。若實作發現需要改變此決策，必須回到
   `$devweave revise`，不得在 implementation 偷換設計。
4. Wiki 只在 verification 的 Knowledge Review/approved promote plan 中更新；
   G1/G2 與 implementation 階段保持唯讀。

## 需求與驗收條件

## REQ-001: Windows runner 可啟動 hook

- Priority: must
- Acceptance: AC-001, AC-002
- Description: `.codex/hooks.json` 的單一 PreToolUse command 必須可由
  `cmd.exe /d /s /c` 與 PowerShell 外層啟動，從 Git root 找到 `guard.py`；
  在 repository root 與 nested `cwd` 執行時均須以 process exit 0 結束。

## REQ-002: UTF-8 hook transport

- Priority: must
- Acceptance: AC-002, AC-003
- Description: hook 對含繁體中文 repository path、`cwd` 與 tool input 的 raw
  UTF-8 JSON 必須正確解析並輸出可用 UTF-8 JSON，不得因 Windows CP950 console
  encoding 造成 JSON parse failure 或 mojibake。

## REQ-003: 既有 guard policy 不變

- Priority: must
- Acceptance: AC-001, AC-003
- Description: 未綁定 Work Item 的寫入仍回傳
  `hookSpecificOutput.permissionDecision=deny`；read-only Bash 仍不產生
  policy output；malformed/不可解析 input 必須 fail closed 為合法 deny JSON，
  且所有正常 policy 結果的 process exit 都是 0。

## REQ-004: Bootstrap source consistency

- Priority: must
- Acceptance: AC-004
- Description: VS Code 0.2.1 build-time bootstrap 必須從根目錄 hook 產生，
  verifier 必須檢查新的 PowerShell、UTF-8、Python 與 no-`commandWindows`
  semantic contract，並產生可驗證的 current VSIX。

## NFR-001: Shell 與 encoding determinism

- Priority: must
- Acceptance: AC-001, AC-002, AC-003
- Description: launcher 不得依賴會被外層 shell 重複展開的變數或未指定
  console code page；測試必須直接啟動真實 Windows child process，而非只測
  字串或 mock。

## NFR-002: Compatibility and safety

- Priority: must
- Acceptance: AC-003, AC-004, AC-005
- Description: 保持 Python 3.11+、stdlib-only、既有 JSON envelope 與
  fail-closed guard；不得放寬未綁定或未通過 G2 的寫入限制，也不得新增
  `commandWindows` 或改動其他平台行為。

## NFR-003: Regression coverage

- Priority: must
- Acceptance: AC-001, AC-002, AC-003, AC-004, AC-005
- Description: repository contract 必須涵蓋 cmd/PowerShell、root/subdir、
  ASCII/UTF-8、allow/deny/malformed；package、typecheck、Extension test、
  smoke 與 Python full suite 必須可重跑且結果可記錄。

## AC-001: cmd.exe launcher contract

- Requirement: REQ-001, REQ-003, NFR-001
- Scenario: Given current repository hook and an unbound `Write` payload, when
  Codex-equivalent `cmd.exe /d /s /c "<command>"` runs it from the repository
  root with JSON input, then process exit is 0, stdout is valid JSON, and the
  decision is `deny` with `hookEventName=PreToolUse`.

## AC-002: PowerShell launcher contract

- Requirement: REQ-001, REQ-002, NFR-001
- Scenario: Given the same hook and a PowerShell outer runner, when the command
  runs from both repository root and a nested `vscode-extension` cwd with raw
  UTF-8 JSON containing the Chinese repository path, then process exit is 0 and
  stdout is valid JSON with the expected deny decision.

## AC-003: policy and malformed-input safety

- Requirement: REQ-002, REQ-003, NFR-001, NFR-002
- Scenario: Given UTF-8 payloads for an unbound write, a read-only Bash command,
  and malformed JSON, when each runner invokes the guard, then write/malformed
  cases return valid deny JSON, read-only returns no policy output, and every
  normal result exits 0 without uncaught traceback or encoding error.

## AC-004: bootstrap/package consistency

- Requirement: REQ-004, NFR-002, NFR-003
- Scenario: Given the updated root hook, when `npm.cmd run package` rebuilds the
  current Extension bundle, then the bootstrap hook is byte/source-consistent,
  verifier checks the new launcher contract, and only the certified 0.2.1 VSIX
  is accepted.

## AC-005: repository verification

- Requirement: NFR-002, NFR-003
- Scenario: Given the fixed source, when targeted repository contract tests,
  Python full suite, Extension unit tests, typecheck, smoke test, package
  verifier and `git diff --check` run, then all required commands pass with
  current evidence and no stale failure remains.

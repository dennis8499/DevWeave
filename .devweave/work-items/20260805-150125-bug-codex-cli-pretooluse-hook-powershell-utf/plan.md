# 執行計畫：修正 Codex CLI PreToolUse Hook 的 PowerShell 與 UTF-8 失敗

<!-- DEVWEAVE:artifact=plan version=1 work=20260805-150125-bug-codex-cli-pretooluse-hook-powershell-utf -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立跨 runner 的紅燈回歸測試

- Traces: REQ-001, REQ-002, REQ-003, NFR-001, NFR-003, AC-001, AC-002, AC-003, DEC-001, DEC-002
- Inputs: G1 failing reproduction、現行 `.codex/hooks.json`、guard policy envelope。
- Output: `tests/test_repository_contract.py` 的真實 `cmd.exe`/PowerShell
  child-process tests；涵蓋 root/nested cwd、raw UTF-8 中文 payload、allow/deny
  與 malformed input，先對現行 source 產生預期紅燈。
- Verification: targeted repository contract tests；記錄 red reproduction
  與修正後 green regression。
- Dependencies: G2 approval。

## TASK-002: 修正 launcher 與 guard transport adapter

- Traces: REQ-001, REQ-002, REQ-003, NFR-001, NFR-002, AC-001, AC-002, AC-003, DEC-001, DEC-002, DEC-003
- Inputs: TASK-001 red tests、已核准 `design.md`。
- Output: `.codex/hooks.json` 使用 shell-neutral PowerShell launcher；
  `guard.py` 以明確 UTF-8 bytes 解析/輸出，保留 policy JSON、fail-closed 與
  process exit 0 semantics。
- Verification: TASK-001 targeted tests、`tests/test_guard.py` 與直接的
  malformed/UTF-8 probes。
- Dependencies: TASK-001。

## TASK-003: 同步 package verifier、文件與 source-derived bundle

- Traces: REQ-004, NFR-002, NFR-003, AC-004, AC-005, DEC-004
- Inputs: TASK-002 fixed root hook/guard。
- Output: `vscode-extension/scripts/verify-package.mjs` 檢查新的 launcher
  semantic contract；更新 `docs/使用手冊.md`；執行 package 產生 current
  `dist/bootstrap` 與 0.2.1 VSIX。
- Verification: `npm.cmd run package`、package verifier、artifact hash/entry
  checks、`git diff --check`。
- Dependencies: TASK-002。

## TASK-004: 完成全量驗證與 G3 知識提升

- Traces: NFR-002, NFR-003, AC-005, DEC-004
- Inputs: TASK-001 至 TASK-003 current source、diff、evidence 與 accepted baseline。
- Output: Python/Extension verification evidence、Knowledge Review disposition、
  declared Wiki promote plan（最多五個 content pages plus index/log coupling）、
  refreshed/sealed affected pages與 acceptance artifact。
- Verification: root unit suite、Extension tests/typecheck/smoke/package、
  DevWeave `validate`、high-risk isolated review、完整 Wiki diff reconciliation。
- Dependencies: TASK-003、current G2 build approval。

## 驗證策略

1. TDD red → minimal green：先以 TASK-001 的 process-level test 捕捉現行
   PowerShell exit 1/UTF-8 parse failure，再完成 TASK-002，最後保留測試作為
   regression oracle。
2. Targeted：repository hook contract、guard policy tests、cmd/PowerShell
   raw UTF-8 probes，包含 root/subdirectory 與 deny/allow/malformed。
3. Build：`vscode-extension/npm.cmd run package`、`typecheck`、Extension unit
   tests 與 smoke；verifier 必須拒絕舊 launcher semantic contract。
4. Full：`python -B -m unittest discover -s tests -v`、`npm.cmd run test`、
   `npm.cmd run typecheck`、`npm.cmd run test:smoke`、`npm.cmd run package`、
   `git diff --check`；每項以 DevWeave verify 登錄 current evidence。
5. High-risk：完成 final diff/scope/Wiki/baseline/evidence stabilization 後，
   只由 DevWeave router 啟動 exactly one isolated read-only Independent Review；
   unavailable/advisory 只作 warning，具名 critical finding 需 exact waiver。
6. Manual acceptance：使用者在 Codex `/hooks` 重新信任變更並以新 session，
   在 root 與 nested workspace 觸發一次正常 read-only 與受 guard 阻擋的 write。

## 基線更新計畫

不更新 `.devweave/baseline/`：本 Work Item 不改變已接受的單一 router、hook
guardrail、fail-closed policy、JSON envelope 或 verification command；精確的
Windows launcher/UTF-8 行為屬 source-bound Wiki 與 Extension package contract，
於 TASK-004 的 Knowledge Review 中更新並 seal。若 G3 reconciliation 發現
accepted governance truth 需要變更，必須停止並透過 `$devweave revise` 回到最早
受影響 phase。

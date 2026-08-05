# 執行計畫：修正 Windows Codex PreToolUse Hook 失敗

<!-- DEVWEAVE:artifact=plan version=1 work=20260805-104700-bug-windows-codex-pretooluse-hook -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 更新 canonical Windows hook launcher

- Traces: REQ-001, REQ-002, AC-001, AC-002, DEC-001
- Inputs: 已核准 `.codex/hooks.json`、Codex Windows command contract、既有 `guard.py` interface。
- Output: 標準 `command` 使用 PowerShell/Git root/Python launcher；`commandWindows` 移除；guard.py 不變。
- Verification: 以 `cmd.exe /d /s /c` 執行 allow 與 unbound Write payload，確認 exit/output contract。
- Dependencies: none

## TASK-002: 建立 process-level hook regression

- Traces: NFR-001, AC-004, DEC-001
- Inputs: TASK-001、既有 `tests/test_guard.py` 與 repository contract test。
- Output: `tests/test_repository_contract.py` 驗證 hook JSON、cmd.exe 啟動、合法 deny JSON 與 zero exit；保留既有 guard unit coverage。
- Verification: root `python -B -m unittest discover -s tests -v`。
- Dependencies: TASK-001

## TASK-003: 更新文件與 source-derived 0.2.1 package

- Traces: REQ-003, NFR-002, AC-003, AC-005, DEC-002
- Inputs: TASK-001、`vscode-extension/esbuild.mjs` source copy flow、package verifier、hook troubleshooting section。
- Output: 使用手冊區分 process failure/policy deny；verifier 檢查 embedded hook semantics；重建 `dist/bootstrap` 與 0.2.1 VSIX，legacy artifacts 不變。
- Verification: `npm.cmd run package`、package verifier、VSIX embedded hook/hash inspection。
- Dependencies: TASK-001, TASK-002

## TASK-004: 完成 high-risk G3 knowledge 與 acceptance evidence

- Traces: REQ-003, AC-001, AC-002, AC-003, AC-004, AC-005, DEC-002
- Inputs: TASK-001 至 TASK-003 的 current diff、test/package evidence 與現場 Codex acceptance。
- Output: `wiki/modules/vscode-extension.md` promote、`wiki/index.md`/`wiki/log.md` coupling/seal、acceptance artifact、Knowledge Review、完整 G3 evidence；high-risk independent review 由 router 啟動一次。
- Verification: `npm.cmd run test`、`npm.cmd run typecheck`、`npm.cmd run test:smoke`、root unit tests、`git diff --check`、Codex UI manual acceptance。
- Dependencies: TASK-003

## 驗證策略

- Targeted：cmd.exe launcher smoke、allow payload、unbound Write deny payload、JSON parse 與 exit code assertions。
- Regression：root Python tests，包含 guard/repository contract；不修改既有 guard policy tests。
- Package：Extension tests、typecheck、production package、manifest/source hash、VSIX required entries 與 legacy 0.1.0/0.2.0 fixed hashes。
- Manual acceptance：新 Codex session 載入 repository hook 後，PreToolUse 不再顯示 process failure；未綁定或 gate 不允許的寫入顯示 DevWeave policy reason。
- High-risk G3：完整 diff/scope/baseline/evidence reconciliation、Knowledge Review promote/seal、一次 isolated read-only Independent Review 與 human acceptance approval。

## 基線更新計畫

不更新 `.devweave/baseline/*`；本次不改 accepted system boundary、guard policy、schema 或 verification profile。新的 Windows hook/bootstrap 行為在 G3 promote 到 `wiki/modules/vscode-extension.md`，並同步 `wiki/index.md` 與 append-only `wiki/log.md`。

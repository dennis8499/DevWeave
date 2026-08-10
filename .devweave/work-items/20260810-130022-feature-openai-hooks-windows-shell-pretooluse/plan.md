# 執行計畫：依 OpenAI Hooks 最佳實踐強化 Windows 跨 Shell PreToolUse 相容性

<!-- DEVWEAVE:artifact=plan version=1 work=20260810-130022-feature-openai-hooks-windows-shell-pretooluse -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立精確雙路徑 PreToolUse hook contract

- Traces: REQ-001, REQ-002, REQ-003, NFR-001, AC-001, AC-002, AC-003, DEC-001, DEC-002
- Inputs: G2-approved `design.md`、既有 `.codex/hooks.json`、`guard.py` stdin/stdout contract、OpenAI Hooks schema boundary
- Output: 根 `.codex/hooks.json` 使用 exact matcher、`command`/`commandWindows`、timeout 30 與 status message；guard policy/decision schema 未放寬
- Verification: repository contract schema assertions、direct guard unit suite、raw UTF-8 malformed/deny process checks
- Dependencies: none

## TASK-002: 擴充唯讀 doctor Windows matrix diagnostics

- Traces: REQ-005, NFR-002, AC-004, AC-007, DEC-003
- Inputs: TASK-001 hook schema、既有 `doctor(repo)` Interface、stdlib subprocess/shutil capabilities
- Output: doctor checks `py -3`、Git、CMD、Windows PowerShell 5.1、PowerShell 7、hook schema/trust guidance 與 actual launcher probe，缺少 runtime 時有明確 false/detail
- Verification: initialized fixture doctor test、real repository doctor JSON、no-write assertion、missing/invalid probe targeted tests where safe
- Dependencies: TASK-001

## TASK-003: 實作 Windows child-process regression matrix

- Traces: REQ-004, NFR-001, NFR-002, AC-002, AC-003, AC-007, DEC-004
- Inputs: TASK-001 `commandWindows`、root/nested repository fixtures、existing repository contract harness
- Output: CMD、Windows PowerShell 5.1、PowerShell 7 在 root/nested cwd 的 raw UTF-8、unbound Write deny、malformed JSON deny、read-only Bash silence 與 exit contract tests
- Verification: `python -B -m unittest tests.test_repository_contract -v`，以及完整 `unit-tests` profile；缺少 required shell 不 silently skip
- Dependencies: TASK-001

## TASK-004: 產生並驗證 0.2.3 source-derived Extension release

- Traces: REQ-006, NFR-003, AC-005, AC-007, DEC-005
- Inputs: TASK-001 root hook、`vscode-extension/esbuild.mjs` source-derived mapping、current 0.2.2 package/artifact
- Output: package/lock/verifier/tests/help metadata current 0.2.3；root/embedded hook semantic/byte contract、58 bootstrap files、119 VSIX entries 與 retained 0.2.2 artifact
- Verification: `npm.cmd run typecheck`、`npm.cmd run test`、`npm.cmd run package`、`npm.cmd run test:smoke`、verifier/package-version/bootstrap tests
- Dependencies: TASK-001

## TASK-005: 更新 operator 文件與 release boundary

- Traces: REQ-007, NFR-001, NFR-002, NFR-003, AC-006, AC-007, DEC-005
- Inputs: TASK-001/002/004 current behavior、G1 brief/requirements、root `AGENTS.md` precedence
- Output: README、繁中使用手冊、root policy、Extension README/help 說明四種 Windows terminal、one-line command、`py -3`/Git/trust/doctor、process-vs-policy failure 與 0.2.3/0.2.2 boundary
- Verification: repository documentation contract、UTF-8/link checks、`git diff --check`
- Dependencies: TASK-002, TASK-004

## TASK-006: 完成 current evidence、baseline 與 Knowledge Review promotion

- Traces: REQ-006, REQ-007, NFR-003, AC-005, AC-006, AC-007, DEC-006, DEC-007
- Inputs: TASK-001–TASK-005 verified diff、current test/package/doctor logs、G1 Wiki context/gaps、high-risk review context
- Output: 三份 accepted baseline、四個 refreshed Wiki content pages、coupled index/log/seals、current acceptance/evidence 與 exactly-one router-owned isolated review record
- Verification: DevWeave `knowledge review/plan/seal`、baseline CLI、full `validate --gate acceptance`、human G3 approval; no direct ledger edits
- Dependencies: TASK-003, TASK-004, TASK-005

## 驗證策略

### Targeted

- `.codex/hooks.json` JSON/schema/matcher/timeout/dual launcher assertions。
- `guard.py` direct contract for raw UTF-8, malformed JSON, deny JSON, read-only silence and exit 0。
- `devweave doctor` real JSON plus initialized-fixture/no-write checks。
- Child-process matrix through `cmd.exe /d /s /c`、`powershell.exe -NoLogo -NoProfile -NonInteractive`、`pwsh -NoLogo -NoProfile -NonInteractive` at root and `vscode-extension` cwd。

### Regression/build

- DevWeave configured high-risk profiles: `unit-tests`、`extension-typecheck`、`extension-tests`、`extension-package`、`extension-smoke`。
- `python -B -m unittest tests.test_repository_contract -v` for the repository contract and `git diff --check`。
- `npm.cmd run typecheck`、`npm.cmd run test`、`npm.cmd run package`、`npm.cmd run test:smoke` in `vscode-extension`。
- Package verifier checks current 0.2.3 only, root/embedded hook equality, source length/hash, 58 files, 119 entries and retained 0.2.2.

### Manual acceptance

- In VS Code integrated terminal, manually execute the documented one-line commands with CMD, Windows PowerShell 5.1 and PowerShell 7 profiles; confirm repository trust and observe the same deny/allow semantics.
- Confirm missing runtime/trust guidance is actionable and that Extension does not execute shell/Python/Git or silently overwrite an exact hook.

### High-risk acceptance

- Stabilize final product/Wiki/baseline/diff/scope/evidence first.
- Existing router starts exactly one isolated read-only Independent Review Agent; record result through machine-only `review record`.
- `passed` or warning-only fallback is reportable; named critical security/data-loss/irreversible/scope finding blocks G3 unless exact narrow `review-critical` waiver exists.

## 基線更新計畫

Verification 以 DevWeave baseline CLI 更新：

- `.devweave/baseline/architecture.md`：雙路徑 hook adapter、doctor diagnostic seam、guard policy/source-derived Extension boundary。
- `.devweave/baseline/product.md`：完整 Windows terminal scope、0.2.3 current package 與 0.2.2 retained artifact。
- `.devweave/baseline/quality.md`：Windows child-process matrix、doctor checks、UTF-8/process-vs-policy contract、58/119 package integrity 與 high-risk review bar。

Knowledge Review 採 `promote`，最多四個 content upsert：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`；完成後由 engine coupled `wiki/index.md`、`wiki/log.md`，刷新 source fingerprints 並 seal。G2 與 implementation 階段不得直接修改 Wiki。

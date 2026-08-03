# 執行計畫：建立 DevWeave Control Center VS Code Extension

<!-- DEVWEAVE:artifact=plan version=1 work=20260803-090218-feature-devweave-control-center-vs-code-extensio -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 TypeScript Extension scaffold 與 package contract

- Traces: REQ-001, NFR-004, AC-001, AC-014, DEC-003, DEC-007
- Inputs: approved `design.md`、VS Code contribution requirements、Node/npm runtime。
- Output: `vscode-extension/package.json`、TypeScript/esbuild configuration、activation entry、vanilla Webview build/test scripts、local CSP-compatible asset layout。
- Verification: `npm --prefix vscode-extension run typecheck`、`npm --prefix vscode-extension run package`。
- Dependencies: none

## TASK-002: 實作 workspace snapshot reader 與 contract projection

- Traces: REQ-001, REQ-002, REQ-006, REQ-010, NFR-001, AC-001, AC-002, AC-006, AC-010, DEC-002, DEC-005
- Inputs: `.devweave/project.json`、work-item files、baseline、Wiki、hook、skill metadata、malformed/legacy fixture scenarios。
- Output: typed `WorkspaceSnapshot`、`WorkspaceSnapshotReader`、bounded UTF-8 file reads、minimal frontmatter/state parsers、schema/managed/path diagnostics、snapshot provenance/freshness model。
- Verification: Node unit tests for uninitialized、managed false/true、zero/multiple/closed work、malformed/unsupported schema、placeholder/stale Wiki、missing hook；no child process or write API imports。
- Dependencies: TASK-001

## TASK-003: 實作 typed ActionIntent 與 deterministic PromptComposer

- Traces: REQ-004, REQ-005, REQ-009, NFR-003, AC-004, AC-005, AC-009, AC-013, DEC-001, DEC-004
- Inputs: existing public chat verbs、machine CLI parser/handlers、approved scope/gate rules、PromptBundle interface。
- Output: complete ActionIntent union、canonical argument renderer、public/machine prompt templates、path/secret/raw-log sanitization、governance warnings、stable PromptBundle output。
- Verification: prompt snapshot tests for every project/lifecycle/governance/knowledge/task/evidence/verification/waiver/gate action；same input produces byte-equivalent output and no absolute path/shell operator/raw log/secret-like value。
- Dependencies: TASK-002

## TASK-004: 建立 Host controller、TreeView、watcher、clipboard 與 Webview protocol

- Traces: REQ-002, REQ-005, REQ-010, NFR-004, AC-002, AC-005, AC-010, AC-014, DEC-002, DEC-003, DEC-004
- Inputs: `WorkspaceSnapshotReader`、`PromptComposer`、`ClipboardAdapter`、VS Code contribution points。
- Output: Extension activation/deactivation、repository/work-item TreeDataProvider、single active dashboard panel、file watcher with debounce、file opener、clipboard adapter、strict typed `postMessage` protocol、unknown-message fail-closed handling。
- Verification: host unit tests with mocked VS Code ports；activation smoke test；clipboard copy test；watcher refresh test；static assertion that no `child_process`/shell/write API is used。
- Dependencies: TASK-002, TASK-003

## TASK-005: 實作 Dashboard、Work Detail 與 Wiki/verification information architecture

- Traces: REQ-003, REQ-007, REQ-008, REQ-009, NFR-002, AC-003, AC-007, AC-008, AC-009, AC-012, DEC-003, DEC-006
- Inputs: typed snapshot/protocol、eight phase mapping、three gate mapping、requirements/design/plan/evidence/knowledge projections。
- Output: Overview、next safe action、G1/G2/G3 track、artifact trace、task board、verification/acceptance、Wiki-first/G3 knowledge、audit sections；vanilla HTML/CSS with VS Code theme tokens、Codicons、CSP、ARIA、keyboard focus、high-contrast、reduced motion。
- Verification: Webview DOM/message tests；manual light/dark/high-contrast/font-scaling/reduced-motion review；keyboard-only navigation；narrow-width layout check。
- Dependencies: TASK-004

## TASK-006: 完成所有 action entry 與 Action Preview interaction

- Traces: REQ-004, REQ-005, REQ-008, REQ-009, NFR-003, AC-004, AC-005, AC-008, AC-009, AC-013, DEC-004, DEC-006
- Inputs: PromptComposer、stage-specific dashboard sections、project/work/knowledge/task/evidence data。
- Output: repository init/doctor/project/command actions、work lifecycle actions、risk/scope/baseline/waiver actions、knowledge context/plan/seal actions、task/evidence/verify actions、approve/revise/close actions；統一 preview/copy flow 與 approval warning。
- Verification: one UI action test per ActionIntent；preview field completeness；copy-only invariant；multi-work selection and closed-work restrictions；no prompt is sent or executed by Extension。
- Dependencies: TASK-005

## TASK-007: 建立 contract、security、prompt 與 regression test suite

- Traces: REQ-006, NFR-001, NFR-003, NFR-004, AC-006, AC-011, AC-013, AC-014, DEC-001, DEC-002, DEC-005, DEC-007
- Inputs: existing `fixtures/devweave`、repository contract behavior、projection/composer/host modules。
- Output: Node unit/contract tests、fixture snapshots、sanitization tests、read-only API import guard、existing Python suite integration command definitions、failure-mode coverage。
- Verification: `npm --prefix vscode-extension test`、`python -B -m unittest discover -s tests -v`、`git diff --check`。
- Dependencies: TASK-003, TASK-004, TASK-006

## TASK-008: 完成 activation/package/accessibility smoke verification

- Traces: REQ-001, REQ-002, NFR-002, NFR-004, AC-001, AC-002, AC-012, AC-014, DEC-003, DEC-007
- Inputs: complete Extension package、compiled Webview、host tests、VS Code Desktop runtime。
- Output: production package artifact、activation smoke test、contribution/tree/dashboard registration verification、accessibility checklist result、extension README/usage notes inside `vscode-extension/`。
- Verification: `npm --prefix vscode-extension run package`、`npm --prefix vscode-extension run test:smoke`、manual accessibility matrix。
- Dependencies: TASK-005, TASK-007

## TASK-009: 設定 DevWeave verification commands 並完成 implementation handoff

- Traces: NFR-001, NFR-004, AC-011, AC-014, DEC-007, DEC-008
- Inputs: completed Extension scripts、approved task ledger、current project verification profile。
- Output: via DevWeave `command set`, register `extension-typecheck`、`extension-tests`、`extension-package` 與 `extension-smoke` commands with high-risk profile selection；所有 implementation tasks completed；G3 verification inputs ready。不得在此 task 直接修改 baseline/Wiki。
- Verification: `devweave command list` confirms exact argv/cwd/profile mapping；targeted command dry validation；task ledger and plan parity。
- Dependencies: TASK-007, TASK-008

## 驗證策略

- Targeted：每個 task 先執行其 listed typecheck、unit、host 或 Webview check，並以 task completion note/evidence 回填。
- Regression：保留現有 `python -B -m unittest discover -s tests -v`，覆蓋 DevWeave engine、guard、Wiki、CLI contract；新增 Node tests 覆蓋 projection、PromptComposer、Webview protocol 與 no-side-effect invariant。
- Build/package：執行 `extension-typecheck`、`extension-tests`、`extension-package`；VS Code Desktop 可用時執行 `extension-smoke`。
- High-risk review：G3 前加入 current independent review evidence，檢查 process/write prohibition、CSP、path/secret sanitization、schema compatibility、scope 與 rollback。
- Manual acceptance：以 uninitialized、managed false、managed true、zero/multiple/closed work、每個 phase、Wiki placeholder/stale、knowledge promotion、stale refresh、approval/revise/close warning 與 light/dark/high-contrast/keyboard/reduced-motion matrix 驗收。
- G3 acceptance：所有 AC 必須有 current passing source-bound evidence；feature work 必須有 acceptance 與 regression evidence；baseline architecture update 需透過 `baseline --target` 宣告並在 verification/acceptance 依 guard 更新，Wiki 只有在 affected-page status 證明需要時才 promotion。

## 基線更新計畫

- G3 宣告並更新 `.devweave/baseline/architecture.md`，記錄 VS Code Extension 與 repository-owned Python engine、Codex Chat、hook、state/evidence、Wiki 的 accepted system boundary，對應 DEC-008。
- 不更新 product/quality baseline，除非 verification 顯示新的 accepted quality policy；若沒有其他 baseline change，於 G3 以 engine CLI 記錄 no-update rationale。
- 不建立空的 Wiki knowledge plan；`wiki/` 目前的 placeholder/health warning 保留，只有 `knowledge status` 顯示本 work item 真正 affected page 時才進行 planned promotion。

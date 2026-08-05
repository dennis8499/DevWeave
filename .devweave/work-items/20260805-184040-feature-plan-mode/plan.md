# 執行計畫：初始 Plan Mode 導流

<!-- DEVWEAVE:artifact=plan version=1 work=20260805-184040-feature-plan-mode -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 更新 Router 初始 preflight 與 native contract

- Traces: REQ-001, REQ-002, REQ-003, NFR-001, AC-001, AC-002, AC-003, DEC-001
- Inputs: approved `brief.md`/`requirements.md`、Wiki context、現有 `.agents/skills/devweave/SKILL.md` 與 `references/native-question-contract.md`
- Output: Router 在指定 pre-G2 entry points 的 mutation seam 前完成 Plan Mode preflight；contract 明確定義 host capability、停止、compatibility fallback、result safety 與 `init` 例外。
- Verification: repository contract fragments、static ordering review、普通模式 stop/no-Work-Item walkthrough、explicit compatibility fallback contract check。
- Dependencies: none

## TASK-002: 建立 PlanModeGuidance model 與 PromptComposer mapping

- Traces: REQ-004, NFR-001, AC-004, AC-005, DEC-002, DEC-005
- Inputs: TASK-001、`PromptBundle`／`SnapshotGuidance` 現有 Interface、phase enum、既有 prompt sanitization/warning tests
- Output: optional `PlanModeGuidance` type、按 command/phase 的純 mapping；`chatText` 與既有 mutation/read-only behavior byte-for-byte 相容。
- Verification: Extension unit tests for all configured commands, initial/G1/G2/post-G2 mapping, unknown/closed handling, exact chatText and no host adapter string。
- Dependencies: TASK-001

## TASK-003: 更新 SnapshotGuidance 與 overview handoff projection

- Traces: REQ-005, NFR-002, AC-006, DEC-002, DEC-003, DEC-005
- Inputs: TASK-002、`buildSnapshotGuidance`、overview/onboarding render、no-active/pre-G2/post-G2/multiple-active snapshot fixtures
- Output: no active work 與 pre-G2 selected work 的 overview 顯示 Plan Mode 下一步；post-G2、closed、initialize/setup 不產生錯誤 blocker。
- Verification: presentation unit tests and webview contract assertions for guidance metadata, readable handoff, no-active, pre-G2, post-G2, multiple active and closed history。
- Dependencies: TASK-002

## TASK-004: 更新 preview/copy handoff 並保留 PreviewGate safety

- Traces: REQ-005, NFR-002, AC-007, DEC-003
- Inputs: TASK-002、TASK-003、既有 `actionPreview`／`copyResult` envelope、`PreviewGate`、Webview status/copy flow
- Output: mutation preview 與 copied result 顯示「先切換 Plan Mode，再貼到 Codex Chat」handoff；preview、copy、stale reset、clipboard retry 與 raw chatText 維持可用。
- Verification: Webview unit/static tests、PreviewGate regression tests、copy success/error/stale checks、manual preview-to-copy walkthrough。
- Dependencies: TASK-003

## TASK-005: 同步 repository policy、使用手冊與 bootstrap policy asset

- Traces: REQ-006, NFR-001, AC-008, DEC-001, DEC-003, DEC-004
- Inputs: TASK-001、TASK-004、root `AGENTS.md`、`README.md`、`docs/使用手冊.md`、`vscode-extension/README.md`、`vscode-extension/assets/bootstrap/AGENTS.md`
- Output: 文件一致描述初始 preflight、明確 compatibility fallback、Extension 不切換 host mode、0.2.2 release；bootstrap asset 仍符合 exact policy bundle。
- Verification: repository contract/manual keyword tests, UTF-8/link checks, bootstrap source comparison and package source manifest check。
- Dependencies: TASK-004

## TASK-006: 完成 Extension 0.2.2 package contract

- Traces: REQ-007, NFR-001, NFR-002, AC-008, AC-009, DEC-004
- Inputs: TASK-002、TASK-004、TASK-005、`package.json`、package verifier、source-derived bootstrap manifest
- Output: version 0.2.2、updated verifier expectation、new `devweave-control-center-0.2.2.vsix`; 0.2.1 VSIX remains present and no host mode adapter is bundled。
- Verification: typecheck, unit tests, production package/verifier, VSIX entry/hash/version assertions, smoke test。
- Dependencies: TASK-005

## TASK-007: 更新 accepted baseline 與 Wiki knowledge plan in verification

- Traces: REQ-006, REQ-007, NFR-002, AC-008, AC-009, DEC-004
- Inputs: TASK-001 through TASK-006 final diff, current source fingerprint, affected Wiki pages and accepted `.devweave/baseline/` contracts
- Output: verification-only `promote` plan with no more than five content pages, coupled `wiki/index.md`/`wiki/log.md`, page seals, and baseline entries for the accepted initial preflight/0.2.2 contract; no Wiki write occurs during G2 or implementation。
- Verification: `knowledge review --disposition promote`, plan/coverage/refresh/seal validation, baseline validation, complete Wiki diff reconciliation。
- Dependencies: TASK-006

## TASK-008: 完成 full evidence、manual acceptance 與 G3 artifacts

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, NFR-001, NFR-002, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005
- Inputs: TASK-001 through TASK-007 outputs、approved scope、current Git diff and evidence graph
- Output: current acceptance artifact, evidence linked to AC/TASK, manual acceptance record for ordinary/Plan/compatibility/multiple-work/stale-preview/post-G2 flows, and G3-ready baseline/Knowledge Review state。
- Verification: Python full suite, repository contract, Extension unit/typecheck/package/smoke, `git diff --check`, manual acceptance matrix, final `validate --gate acceptance`。
- Dependencies: TASK-007

## 驗證策略

- Targeted contract: inspect Router/native contract ordering; assert no initial `start`/`bind`/`revise`/bootstrap mutation before host preflight and explicit compatibility; assert no fake adapter, question state, CLI/schema/ledger field or `request_user_input` in Extension source。
- Extension regression: test optional metadata for every public command and phase; exact `chatText`; overview guidance for no active/pre-G2/post-G2/multiple active; preview/copy handoff; PreviewGate stale/retry/copy safety; accessibility and no Help-specific block。
- Build/release: `npm run typecheck`, `npm test`, `npm run package`, `npm run test:smoke`; verify 0.2.2 package, manifest/hash/byte-length, VSIX entries and preserved 0.2.1 artifact。
- Repository verification: configured Python full suite, repository contract, UTF-8/link checks and `git diff --check`。
- Manual acceptance: ordinary-mode initial mutation stops without a Work Item; Plan Mode resubmission reaches G1; unavailable host requires explicit compatibility before fallback; pre-G2/post-G2, multiple active and stale preview behavior remains correct。
- Knowledge/baseline: after source and evidence stabilization, use `promote` for durable router/Control Center/package knowledge, update at most five content pages plus coupled index/log, seal pages, and update accepted baseline through CLI/artifact workflow only。

## 基線更新計畫

- `.devweave/baseline/product.md`: accepted capability for initial pre-G2 Plan Mode handoff, explicit compatibility fallback, and 0.2.2 Control Center release while preserving 0.2.1。
- `.devweave/baseline/architecture.md`: Router mutation seam, optional metadata interface, PreviewGate/Webview projection boundary, and no host adapter/state contract。
- `.devweave/baseline/quality.md`: preflight mutation safety, chatText/protocol compatibility, Extension no-adapter contract, and 0.2.2 package/manual verification commands。
- Baseline files remain read-only until verification/G3 stabilization; record targets and rationale with the DevWeave baseline CLI, never edit machine ledgers directly。

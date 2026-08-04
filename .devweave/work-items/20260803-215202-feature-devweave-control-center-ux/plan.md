# 執行計畫：改善 DevWeave Control Center UX 與使用者導引

<!-- DEVWEAVE:artifact=plan version=1 work=20260803-215202-feature-devweave-control-center-ux -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 Extension presentation seam 與 typed preference protocol
- Traces: REQ-003, REQ-005, REQ-006, REQ-008, REQ-009, REQ-010, REQ-014, NFR-001, NFR-003, AC-003, AC-005, AC-006, AC-008, AC-009, AC-010, AC-014, AC-016, AC-018, DEC-002, DEC-003, DEC-004, DEC-005
- Inputs: approved `brief.md`, `requirements.md`, `design.md`; current `model.ts`, `protocol.ts`, `dashboard.ts`, `snapshot.ts`, existing prompt/parser tests.
- Output: `src/presentation.ts` with command catalog, localized labels, snapshot guidance, readiness, diagnostics, audit parsing and status helpers; additive model/protocol/dashboard preference types with strict parser support; no engine schema or prompt text change.
- Verification: red/green unit tests for all public command catalog entries, guidance states, readiness/diagnostic/audit projections and `setDisplayMode`; `npm run typecheck`.
- Dependencies: none.

## TASK-002: 修正 workspace/work selection、onboarding 與 tree grouping
- Traces: REQ-004, REQ-005, REQ-007, REQ-012, REQ-014, NFR-002, NFR-004, AC-004, AC-005, AC-007, AC-012, AC-014, AC-017, AC-019, DEC-003, DEC-005
- Inputs: TASK-001 presentation types; existing `extension.ts`, `tree.ts`, `dashboard.ts`, bootstrap controller and root resolver.
- Output: active/closed work grouping in TreeView and Dashboard selection; no implicit closed selection; human-readable multi-root QuickPick with managed status; honest snapshot metadata without timestamp freshness false warning; initialization/setup notices; workspaceState display mode wiring.
- Verification: unit tests for active/closed/no-active/multi-root selection and preference persistence seam; existing bootstrap/security tests; `npm run typecheck`.
- Dependencies: TASK-001.

## TASK-003: Implement overview/work/knowledge/verification information architecture
- Traces: REQ-001, REQ-002, REQ-004, REQ-008, REQ-009, REQ-012, REQ-013, NFR-003, NFR-004, AC-001, AC-002, AC-004, AC-008, AC-009, AC-012, AC-013, AC-018, AC-019, DEC-001, DEC-002, DEC-005
- Inputs: TASK-001 presentation seam and TASK-002 workspace selection behavior; existing `webview/main.ts` and `styles.css`.
- Output: concise default overview, four accessible sections, active/closed empty states, work summary, actionable task/evidence/Knowledge panels, localized status/gate/phase labels, responsive CSS, bounded Wiki filters/show-all and focus-preserving render state.
- Verification: red/green presentation/UI state tests for uninitialized, no-active, single-active, multiple-active, closed, blocker, stale evidence, Wiki recommendation and critical diagnostic fixtures; keyboard/ARIA/high-contrast/reduced-motion manual matrix; `npm run typecheck`.
- Dependencies: TASK-001, TASK-002.

## TASK-004: Add reviewer readiness, audit timeline and prompt handoff explanation
- Traces: REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, NFR-001, NFR-003, AC-008, AC-009, AC-010, AC-011, AC-012, AC-016, AC-018, DEC-002, DEC-003, DEC-004
- Inputs: TASK-001 presentation projections and TASK-003 section renderer; existing preview/copy/bootstrap result flow.
- Output: reviewer readiness checklist with current gate and non-authoritative wording; human-readable audit timeline with raw toggle; will-do/will-not-do/after-copy preview summary; approve/revise effects; bootstrap result next steps; busy/error/duplicate action guard and live status.
- Verification: unit tests for gate/evidence/blocker/approve/revise summary; prompt output regression for all nine intents; security tests confirm no raw log copy, process/network or machine command; `npm test`.
- Dependencies: TASK-001, TASK-003.

## TASK-005: Complete P2 display preference, multi-root and Wiki browsing behavior
- Traces: REQ-013, REQ-014, REQ-015, NFR-004, AC-013, AC-014, AC-015, AC-019, DEC-005
- Inputs: TASK-001 typed preference protocol, TASK-002 root labels, TASK-003 Knowledge section.
- Output: concise/advanced toggle persisted only in Extension context; managed/unmanaged multi-root choice copy; Wiki query/type filter/show-all behavior; no repository metadata writes or unbounded scan.
- Verification: protocol/preference/browser unit tests; security source inspection; narrow-window and keyboard manual checks; `npm run typecheck`.
- Dependencies: TASK-001, TASK-002, TASK-003.

## TASK-006: Localize Extension entry points and update user-facing documentation
- Traces: REQ-003, REQ-007, REQ-011, REQ-012, NFR-001, AC-003, AC-007, AC-011, AC-012, AC-016, DEC-004, DEC-006
- Inputs: completed UI command catalog and actual bootstrap/prompt behavior.
- Output: Traditional Chinese Activity Bar/View/Command Palette labels, accurate package description distinguishing bootstrap write from prompt copy, updated `vscode-extension/README.md` onboarding/handoff/setup guidance; no public command ID or text contract change.
- Verification: package metadata/readme contract tests; `npm run package`; `npm run test:smoke`.
- Dependencies: TASK-003, TASK-004.

## TASK-007: Full regression, acceptance evidence and handoff
- Traces: NFR-001, NFR-002, NFR-003, NFR-004, AC-016, AC-017, AC-018, AC-019, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006
- Inputs: TASK-001 through TASK-006; current G2 approval; existing Python/Extension verification commands.
- Output: current acceptance matrix, targeted Extension evidence, full package/smoke/typecheck/npm/Python regression results, scope/diff review, baseline no-update rationale and G3-ready Knowledge Review inputs.
- Verification: `npm run typecheck`; `npm test`; `npm run package`; `npm run test:smoke`; `python -B -m unittest discover -s tests -v`; `git diff --check`; inspect no engine/schema/Wiki product changes before verification.
- Dependencies: TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006.

## 驗證策略

- Targeted first: presentation/protocol/selection tests at the extension-local seams, following red → green vertical slices; no tests reach private DOM implementation.
- Regression: existing prompt, parser, snapshot, bootstrap, security and protocol tests remain green; public `$devweave` output is compared against known literal commands.
- Build/runtime: typecheck, production package and VS Code Extension Host smoke.
- Repository: full Python suite and diff/scope check; existing dirty VSIX remains untouched.
- Manual acceptance: four-section navigation, no-active/closed history, bootstrap versus prompt copy wording, reviewer readiness, keyboard/focus, ARIA/live status, high contrast, reduced motion, narrow Webview and multi-root QuickPick.
- Knowledge: after verification, run current `knowledge status`; record `knowledge review promote` if source-overlapping Wiki pages require durable refresh, otherwise use valid `no-update` only when no affected page/Wiki diff remains. Keep Wiki read-only until verification.

## 基線更新計畫

- `.devweave/baseline/product.md`、`.devweave/baseline/architecture.md`、`.devweave/baseline/quality.md`：不更新；本 work 是既有 Extension capability 的 presentation refinement，沒有 engine/governance contract 變更，於 `acceptance.md` 記錄 rationale。
- Root Wiki：implementation 期間唯讀。G3 依 Knowledge Review 的 affected-page result refresh/promote 必要頁面，並同步 index/log；不在 G2 或 implementation 直接寫入。

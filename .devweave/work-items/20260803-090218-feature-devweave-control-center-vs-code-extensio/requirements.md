# 需求與驗收條件：建立 DevWeave Control Center VS Code Extension

<!-- DEVWEAVE:artifact=requirements version=1 work=20260803-090218-feature-devweave-control-center-vs-code-extensio -->

## 假設與限制

- Extension 以 VS Code Desktop 為第一目標，使用 workspace file API 讀取 repository；不要求 Extension 啟動 Python 或 shell process。
- Python DevWeave engine、JSON/JSONL schema、public command surface、Codex hook、人工 gate 與 Wiki safety policy 是 authoritative contract。
- Extension 只產生 Traditional Chinese Codex Chat prompt 與 machine command preview；使用者必須自行貼入並送出。
- 所有 snapshot 都必須標示來源與時間；Extension 不把本地推導的 phase/gate/fingerprint 當成 engine approval。
- 第一版不處理 Git workflow、DevWeave release/version management、remote coordination、agent runtime 或新資料庫。

## REQ-001: Repository discovery and initialization state

- Priority: must
- Acceptance: AC-001
- Description: Extension MUST discover the active workspace repository and distinguish missing `.devweave/project.json`、`managed: false`、`managed: true`、invalid project configuration、missing hook、Wiki warning 與 unsupported schema。對未初始化或未 managed repository，Extension MUST 提供初始化/明確啟用所需的 Codex prompt preview，且不得自行初始化或修改檔案。

## REQ-002: Work item dashboard and selection

- Priority: must
- Acceptance: AC-002
- Description: Extension MUST 唯讀呈現 active/closed work items、kind、title、risk、phase、G1/G2/G3 gate status、task/evidence progress、blocker、stale evidence、knowledge health 與 updated time；沒有 work item 或有多個 eligible work item 時 MUST 顯示對應 empty/selection state，不得自行猜選。

## REQ-003: Phase and gate guidance

- Priority: must
- Acceptance: AC-003
- Description: Extension MUST 將八個 phase 映射到 G1 scope、G2 build、implementation、G3 acceptance 的視覺流程，呈現 engine `instructions` 對應的 next action、pending gate、reference 與 warning，並把 approval/validate/next-step action 轉為可審閱 prompt。

## REQ-004: Complete DevWeave action coverage

- Priority: must
- Acceptance: AC-004
- Description: Extension MUST expose prompt-generation entry points for project、lifecycle、governance、knowledge、task、evidence、verification、waiver、approve、revise 與 close 等既有 CLI capability；UI action MUST route through a single typed action composer，不得散落拼接 CLI 字串。

## REQ-005: Codex Chat action preview and clipboard flow

- Priority: must
- Acceptance: AC-005
- Description: Every mutation action MUST show an action preview containing intent、work ID、phase/gate、target paths、expected state change、Traditional Chinese chat text、optional machine command、warnings 與「Extension 不會執行」notice；確認後只可寫入 clipboard，並以 toast/accessible status 回報已複製。

## REQ-006: Contract projection and read-only safety

- Priority: must
- Acceptance: AC-006
- Description: Extension MUST 透過 workspace file API projection `.devweave/project.json`、state/artifacts/evidence/events、baseline、Wiki、hook 與 skill files；MUST NOT 使用 child process、shell automation、Codex execution API 或任何 file write API，且 malformed/unsupported content MUST fail closed to read-only diagnostic state。

## REQ-007: Requirements, design and implementation views

- Priority: must
- Acceptance: AC-007
- Description: Work item detail MUST provide read-only views for brief/requirements、REQ/NFR→AC trace、design DEC trace、plan TASK dependency、task statuses、evidence links、blocker 與 artifact open actions；開啟檔案不得等同 Extension 修改檔案。

## REQ-008: Wiki-first workspace and G3 knowledge status

- Priority: must
- Acceptance: AC-008
- Description: Extension MUST 顯示 Wiki page categories、frontmatter health、placeholder/stale/orphan/critical findings、G1 index-first read order、最多五個 related pages、recorded gaps、G3 affected/pending/planned/sealed pages、coupled index/log 與 promotion warnings，並只能產生 knowledge context/plan/seal prompts。

## REQ-009: Verification, baseline and acceptance review

- Priority: must
- Acceptance: AC-009
- Description: Extension MUST 顯示 configured verification commands/profiles、evidence status、command/exit code/raw log path、source-bound/stale state、baseline targets、AC/TASK/evidence coverage、waivers 與 residual warnings；G1/G2/G3 approval 與 close action 必須先顯示 governance warning，再產生 prompt，不能直接執行。

## REQ-010: Snapshot provenance and refresh guidance

- Priority: must
- Acceptance: AC-010
- Description: Extension MUST 顯示 filesystem snapshot、last engine-observed state、captured time 與需在 Codex 執行 status/validate 後重新整理的提示；偵測到 state/artifact/source 變更時 MUST 顯示 stale/refresh warning，不得自行重建 DevWeave fingerprint 或 approval。

## NFR-001: Existing contract compatibility

- Priority: must
- Acceptance: AC-011
- Description: Extension MUST preserve existing DevWeave engine behavior、schema version 1、JSON envelope、public verbs、state/event/evidence ledgers、Wiki contract、hook boundaries 與 current Python test suite；不新增第二個 lifecycle、router、agent 或 database。

## NFR-002: Theme and visual adaptability

- Priority: must
- Acceptance: AC-012
- Description: UI MUST 使用 VS Code theme tokens，支援 light、dark、high-contrast、font scaling、keyboard focus、ARIA label 與 reduced motion；Apple-inspired hierarchy、grouped cards、spacing、rounded surfaces 與 semantic status 不得以硬編碼 Apple assets 或只依賴色彩實現。

## NFR-003: Deterministic prompt safety

- Priority: must
- Acceptance: AC-013
- Description: 相同 workspace snapshot、work item 與 ActionIntent MUST 產生相同 prompt；prompt MUST 使用 repo-relative paths、正確 work ID/gate、不得包含 raw verification logs、credential-like secrets 或絕對本機路徑。

## NFR-004: Testability and bounded dependencies

- Priority: must
- Acceptance: AC-014
- Description: Extension MUST 以 TypeScript、vanilla Webview 與明確的 SnapshotReader/PromptComposer/ClipboardAdapter seam 實作；不得引入不必要 UI framework，並提供 typecheck、unit tests、VS Code activation smoke test 與 production package verification。

## AC-001: Repository state is safely classified

- Requirement: REQ-001
- Scenario: Given workspace 分別缺少 project、managed false、managed true 或 project/Wiki 不相容，When Extension refreshes，Then 顯示正確 onboarding/diagnostic state、可複製 prompt 與不可直接執行 notice，且 repository bytes 不變。

## AC-002: Work items are browsable without implicit selection

- Requirement: REQ-002
- Scenario: Given zero、one、多個 active work items 或 closed work item，When user opens the Control Center，Then sidebar/dashboard 顯示 empty、selected、selection-required 或 read-only closed state，且不會自動選擇多個 eligible work item。

## AC-003: Current phase has an understandable next action

- Requirement: REQ-003
- Scenario: Given each supported phase/gate status，When user opens a work item，Then gate track、phase label、pending gate、next action、reference/warning 與對應 prompt action 均與 engine projection 一致。

## AC-004: Every engine capability has a UI prompt entry

- Requirement: REQ-004
- Scenario: Given each ActionIntent category，When user invokes its UI action，Then PromptComposer returns the correct public verb or machine CLI preview with required arguments and no UI-specific ad hoc command construction。

## AC-005: Mutation actions are copy-only and reviewable

- Requirement: REQ-005
- Scenario: Given risk/scope/knowledge/task/evidence/verify/approve/revise/close inputs，When user confirms action preview，Then only clipboard content changes、UI reports copied status、preview shows warnings，且 Extension does not execute command or write repository files。

## AC-006: Unsafe or malformed source fails closed

- Requirement: REQ-006
- Scenario: Given malformed JSON、unsupported schema、missing artifact、invalid Wiki frontmatter 或 unavailable hook，When snapshot is read，Then UI shows diagnostic warning/read-only fallback and never attempts repair or mutation。

## AC-007: Artifact traceability is visible

- Requirement: REQ-007
- Scenario: Given a work item with requirements/design/plan/tasks/evidence，When user opens each detail section，Then artifacts、trace links、dependency state、evidence links and open-file actions are visible without modifying content。

## AC-008: Wiki-first and G3 promotion rules are visible

- Requirement: REQ-008
- Scenario: Given placeholder/stale/affected/planned/sealed Wiki pages，When user opens G1 or G3 knowledge view，Then index-first order、gap requirement、affected page status、coupled index/log and seal requirements are shown and only the corresponding prompts are generated。

## AC-009: Verification and human gates remain explicit

- Requirement: REQ-009
- Scenario: Given validation, evidence, baseline, waiver and approval states，When user opens verification/acceptance view，Then required evidence/command/coverage gaps are visible and approve/close actions require a governance confirmation preview before copy。

## AC-010: Snapshot freshness is honest

- Requirement: REQ-010
- Scenario: Given disk state/artifact/source changes after an engine observation，When the file watcher refreshes，Then UI marks the snapshot as changed or potentially stale and instructs the user to run status/validate in Codex before trusting approval state。

## AC-011: Existing repository behavior remains green

- Requirement: NFR-001
- Scenario: Given the existing repository test suite and contract fixtures，When the Extension work is verified，Then existing Python tests, guard tests and DevWeave contracts remain passing and no existing JSON/JSONL contract is rewritten。

## AC-012: Apple-inspired UI remains VS Code accessible

- Requirement: NFR-002
- Scenario: Given light/dark/high-contrast themes, keyboard-only navigation, increased font size and reduced-motion preference，When user operates the dashboard and preview，Then content remains legible, focusable, semantically labelled and motion-safe。

## AC-013: Prompt output is stable and sanitized

- Requirement: NFR-003
- Scenario: Given identical projection input twice，When PromptComposer composes the same action，Then outputs are byte-equivalent and contain no absolute paths, raw logs or secret-like values。

## AC-014: Extension seams are independently testable

- Requirement: NFR-004
- Scenario: Given mocked workspace files and clipboard adapter，When unit tests exercise projection and prompt composition，Then tests do not require Python, a running Codex session, a Git mutation or a real repository write。

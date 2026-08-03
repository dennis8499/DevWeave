# 執行計畫：收斂 VS Code Extension 至初始化與公開 Codex 命令

<!-- DEVWEAVE:artifact=plan version=1 work=20260803-144614-feature-vs-code-extension-codex -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 public command model/protocol/composer seam
- Traces: REQ-001, REQ-003, REQ-006, NFR-001, NFR-002, AC-001, AC-003, AC-006, AC-008, AC-009, DEC-001, DEC-002
- Inputs: approved `requirements.md`/`design.md`；既有 `ActionIntent`、`PromptBundle`、Webview message envelope 與 sanitization behavior。
- Output: `PublicCommandIntent`/public parser；narrowed `PromptBundle`；八個 deterministic `$devweave` mappings；mutation diagnostic handling；更新 `DashboardCallbacks`/controller-facing types。
- Verification: targeted `core.test.ts` public intent/parser/composer tests；typecheck；security source assertions。
- Dependencies: none

## TASK-002: 將 Host/Panel 接到 public intent 並保留初始化
- Traces: REQ-003, REQ-004, REQ-005, REQ-006, AC-003, AC-004, AC-005, AC-006, DEC-002, DEC-003
- Inputs: TASK-001 public interface；既有 `DashboardPanel` message switch、`ExtensionController` preview/copy/initialize。
- Output: host callback 使用 public intent；copyNextAction 產生 `$devweave next [work-id]`；移除 host 對 machine command/target/gate 的依賴；bootstrap code 行為保持不變。
- Verification: core/security tests；bootstrap regression suite；typecheck。
- Dependencies: TASK-001

## TASK-003: 重建 Webview public command form 並清除內部操作入口
- Traces: REQ-001, REQ-002, REQ-005, AC-001, AC-002, AC-005, AC-006, DEC-003
- Inputs: TASK-001 public intent/parser；既有 snapshot/work selection/render sections/styles。
- Output: 八個命令欄位表單、current work/optional work handling、required-field feedback、preview/copy rendering；移除 JSON composer、quick machine action buttons 與 gate/knowledge/task operation controls；保留 readonly projection/Refresh/open/select/initialize。
- Verification: security source assertions；typecheck/package build；manual smoke review of zero/single/multiple work states。
- Dependencies: TASK-001, TASK-002

## TASK-004: 更新 regression/security tests
- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, NFR-001, NFR-002, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-008, AC-009, DEC-001, DEC-002, DEC-003
- Inputs: completed model/protocol/composer/host/Webview behavior。
- Output: tests for all public command mappings, work selection/optionality, parser rejection of machine intents, no machine CLI output, redaction, critical mutation block, initialization/security regressions.
- Verification: configured `extension-tests`; targeted package/typecheck/smoke as applicable.
- Dependencies: TASK-001, TASK-002, TASK-003

## TASK-005: 更新 Extension documentation and command metadata
- Traces: REQ-007, AC-007, AC-009, DEC-003
- Inputs: final public form behavior and existing README/package manifest.
- Output: README usage/design text describing initialization, eight public commands, preview/copy and Refresh; `copyNextAction` command title clarified as public `$devweave next` copy while retaining command ID.
- Verification: README/source review; `extension-package`; `git diff --check`.
- Dependencies: TASK-003

## 驗證策略

- Targeted: `node.exe --import tsx --test --test-reporter=tap test/unit/core.test.ts test/unit/security.test.ts` from `vscode-extension`.
- Regression/build: `npm.cmd run typecheck`, `npm.cmd run package`, `npm.cmd run test:smoke` from `vscode-extension`.
- Repository regression: `python -B -m unittest discover -s tests -v` from root.
- Manual acceptance: inspect the Webview with zero/single/multiple work items; verify command fields, optional work handling, disabled revise/approve, preview-only public command text, unchanged initialization confirmation/result and readonly sections.
- Scope/security review: inspect complete diff, `git diff --check`, ensure no new process/shell/network/direct Codex path and no Wiki changes during implementation.

## 基線更新計畫

本 work 不預期更新 `.devweave/baseline/`：既有 architecture baseline 的 `PromptComposer` seam、preview/copy boundary、bootstrap boundary 與 readonly Dashboard boundary 仍成立，`ActionIntent` 以 public-only alias 保持命名相容；public verbs 已在 product baseline 明確接受。G3 會以 `knowledge status` 判斷 `wiki/` 是否有真正受 source diff 影響的 page；若無 affected page 且無 Wiki diff，不建立空 promotion plan。

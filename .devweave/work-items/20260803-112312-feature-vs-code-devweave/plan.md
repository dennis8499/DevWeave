# 執行計畫：空白 VS Code 專案初始化產生 DevWeave 流程內容

<!-- DEVWEAVE:artifact=plan version=1 work=20260803-112312-feature-vs-code-devweave -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 source-derived bootstrap bundle

- Traces: REQ-002, NFR-002, NFR-003, AC-002, AC-005, AC-006, DEC-002
- Inputs: 目前 `.agents/skills/devweave/`、`.codex/hooks.json` 與 engine starter templates。
- Output: build 產生 `dist/bootstrap/`、完整 manifest、project defaults、baseline/Wiki
  templates；production bundle 可被 resource adapter 讀取。
- Verification: `npm run package`；manifest completeness/hash test；確認無 node_modules、
  workspace state 或 secrets 被包入。
- Dependencies: none

## TASK-002: 實作 BootstrapInstaller 與 filesystem adapters

- Traces: REQ-002, REQ-004, NFR-001, NFR-002, AC-002, AC-004, AC-005, DEC-001, DEC-003
- Inputs: TASK-001 的 manifest/resource seam、既有 `normalizeRelativePath` 與 VS Code
  workspace.fs API。
- Output: deep `BootstrapInstaller` module、VS Code write adapter、memory adapter seam、
  preflight/hash/conflict/rollback report 與 unit/security regression tests。
- Verification: targeted bootstrap unit tests、`npm run typecheck`、extension security tests；
  驗證相容、conflict、symlink/path、hash failure、I/O rollback 與冪等案例。
- Dependencies: TASK-001

## TASK-003: 整合 controller、command、host protocol 與 dashboard UI

- Traces: REQ-001, REQ-003, REQ-005, AC-001, AC-003, AC-007, DEC-004
- Inputs: TASK-002 的 installer interface/report。
- Output: `devweave.initialize` command、native modal confirmation、Webview initialize message、
  未初始化 CTA/content summary、成功/失敗 report、snapshot refresh；保留 managed workspace
  的唯讀與 prompt composer 行為。
- Verification: protocol/core regression tests、extension host smoke test、manual acceptance
  in an empty workspace and a managed fixture。
- Dependencies: TASK-002

## TASK-004: 完成文件、package contract 與 high-risk review preparation

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, NFR-001, NFR-002, NFR-003,
  AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, DEC-001, DEC-002, DEC-003, DEC-004
- Inputs: TASK-001 至 TASK-003 的 delivered behavior。
- Output: Extension README、package/verification metadata、完整 regression/security/smoke
  coverage、acceptance evidence 所需的 manual checklist；不在 implementation 階段直接
  修改 Wiki 或 accepted baseline。
- Verification: all configured high-risk commands、`git diff --check`、independent review
  checklist；建立 acceptance/regression/review evidence。
- Dependencies: TASK-003

## 驗證策略

- Targeted：bootstrap module memory-filesystem tests，涵蓋 blank install、same-byte adopt、
  idempotent rerun、conflict fail-closed、manifest hash/duplicate/path checks、symlink/ancestor
  rejection、write failure rollback 與 no external process。
- Regression：既有 snapshot reader、prompt composer、protocol/security unit tests；managed
  fixture 必須保持 project/work/gate/Wiki projection 與 mutation blocking 行為。
- Build/package：`extension-typecheck`、`extension-tests`、`extension-package`、
  `extension-smoke`。
- Repository：`unit-tests`、`git diff --check`；不將 `wiki/` 納入 product verification。
- Manual acceptance：在空白 workspace 點擊 Initialize、取消 modal、完成 bootstrap、重新
  開啟 dashboard；再以既有 managed fixture 驗證不會自動寫入。
- High-risk review：由獨立 checklist 檢閱 source-derived manifest、destination/source
  containment、hash、symlink、preflight/rollback、confirmation、no-process 與 compatibility。

## 基線更新計畫

verification 依完整 diff 宣告並更新受影響的 accepted living truth：

- `.devweave/baseline/architecture.md`：記錄 Extension bootstrap write adapter、installer
  seam、bundle provenance、managed/read-only compatibility 與 rollback invariant。
- `.devweave/baseline/product.md`：記錄 Extension 可在空白 workspace 完成 DevWeave bootstrap
  的 accepted capability。
- `.devweave/baseline/quality.md`：記錄 path safety、asset hash/provenance、explicit
  confirmation、idempotence、rollback 與新增 verification coverage。

以上 baseline 只在 verification 依 DevWeave knowledge/baseline policy 更新與宣告；G2/implementation
保持 Wiki 與 accepted baseline 唯讀。

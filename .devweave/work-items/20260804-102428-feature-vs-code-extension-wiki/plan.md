# 執行計畫：修正 VS Code Extension 效能、Wiki 搜尋與完整初始化

<!-- DEVWEAVE:artifact=plan version=1 work=20260804-102428-feature-vs-code-extension-wiki -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: Wiki 搜尋穩定輸入、局部 render 與嵌入式說明
- Traces: REQ-001, REQ-002, REQ-007, NFR-001, AC-001, AC-002, AC-003, AC-013, DEC-001, DEC-008
- Inputs: 現有 `webview/main.ts`、`DashboardSection`、WikiPageProjection 與使用手冊來源。
- Output: `WikiSearchModel`、render scheduler／stable results seam、help section 與相關 model/protocol fixtures；input DOM 不因 query event 重建。
- Verification: WikiSearchModel unit tests（包含式、大小寫、Enter、draft、type、show-all）、Webview source/render seam test、help content/package static check。
- Dependencies: none

## TASK-002: Refresh coordinator 與 deterministic parallel snapshot
- Traces: REQ-003, REQ-004, NFR-001, AC-004, AC-005, AC-006, DEC-002, DEC-005
- Inputs: 現有 watcher debounce、`ExtensionController.refresh()` 與 `WorkspaceSnapshotReader` filesystem adapter。
- Output: `RefreshCoordinator` single-flight/latest-pending implementation；snapshot independent reads 的平行化與 deterministic projection／diagnostic merge。
- Verification: coordinator burst、不可重疊、latest result、error recovery tests；instrumented filesystem 測試 max concurrency、固定排序與 projection regression。
- Dependencies: none

## TASK-003: 完整 0.2.0 bootstrap bundle 與 manifest contract
- Traces: REQ-005, REQ-008, NFR-002, AC-007, AC-008, AC-014, DEC-004, DEC-007
- Inputs: `esbuild.mjs`、root `skills-lock.json`、五個核准 companion skills、通用 `AGENTS.md`、既有 templates/hooks/Wiki starter。
- Output: allowlisted six-skill control bundle、AGENTS、skills lock、hook/project/baseline/Wiki starter、必要目錄、0.2.0 manifest/package metadata；排除非控制內容。
- Verification: manifest source/destination/byteLength/SHA-256 allowlist test；空 workspace bundle content test；package build 與 VSIX entry/version/integrity inspection；確認既有 0.1.0 artifact 未被覆寫。
- Dependencies: none

## TASK-004: Bootstrap inspection、partial repair 與 Dashboard completeness
- Traces: REQ-006, REQ-007, NFR-002, AC-009, AC-010, AC-011, AC-012, DEC-003, DEC-006
- Inputs: TASK-003 的 bundle manifest、現有 `BootstrapInstaller`、`WorkspaceSnapshot` 與 `initialize()` flow。
- Output: read-only inspection、complete/missing/conflict report、non-overwrite partial repair、write rollback、初始化／補齊 CTA 與 completeness projection。
- Verification: empty initialization、partial repair、conflict preservation、idempotent rerun、write failure rollback、dashboard missing paths tests；critical diagnostic 仍 fail-closed。
- Dependencies: TASK-003

## TASK-005: 回歸整合、文件與 release-level verification
- Traces: REQ-001, REQ-003, REQ-005, REQ-006, REQ-007, REQ-008, NFR-001, NFR-002, AC-014, AC-015, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008
- Inputs: TASK-001 至 TASK-004 的 source、fixtures、tests 與 package output；既有 typecheck/39 Extension tests/84 Repository tests 基線。
- Output: 更新 Extension test command／必要 README package 說明與 smoke fixtures；可重現的 full verification evidence 與 high-risk independent package／security review。
- Verification: `npm.cmd run typecheck`、Extension unit/security tests、`npm.cmd run package`、VSIX smoke/inspection、Repository unittest；手動大型 Wiki、快速 watcher、partial repair、help tab acceptance。
- Dependencies: TASK-001, TASK-002, TASK-003, TASK-004

## 驗證策略

1. Targeted：先執行 model/coordinator/bootstrap installer/snapshot contract tests；驗證 query DOM target、single-flight call count、parallel max concurrency、manifest allowlist、conflict bytes 與 rollback list。
2. Regression：保留既有 core/security/presentation/selection/bootstrap tests，補齊所有 `WorkspaceSnapshot`／`BootstrapReport` fixture；確認 legacy public commands、CSP、path safety、no process/network/write boundary。
3. Build/package：typecheck、Extension tests、bundle build、manifest inspection、0.2.0 VSIX build；將新 artifact 寫到不同名稱，先記錄 dirty 0.1.0 artifact 存在與 hash，不覆寫它。
4. Repository：執行 work item 宣告的 Extension smoke 與 Python unittest commands；evidence 綁定 TASK/AC，失敗不得宣稱 G2/G3 完成。
5. Manual acceptance：大型 Wiki 搜尋連續輸入與 Enter、分類／show-all、快速檔案變更 burst、空 workspace 初始化、部分 workspace 補齊/conflict、說明分頁首次載入；確認 target workspace 沒有 README/docs/source/tests/history/help 落地。
6. High-risk：package manifest 與 VSIX content 由獨立 inspection path 再檢查；bootstrap security regression 確認 path normalization、hash validation、non-overwrite、rollback、CSP/no network/no process。

## 基線更新計畫

本工作不改變產品架構、品質門檻或能力基線，不更新 `.devweave/baseline/**`。`vscode-extension` package／bundle 的變更以本 work 的 artifacts、verification evidence 與 G3 Knowledge Review 留存；G3 只在核准的 knowledge plan 中更新最多五頁：

- `wiki/overview.md`：Extension control center、bootstrap 與 snapshot projection 概覽。
- `wiki/architecture/devweave-knowledge-workflow.md`：Extension 只讀 projection、Wiki-first 與 G3 promote 邊界。
- `wiki/modules/knowledge-engine.md`：以 current source fingerprint 更新現有 stale page，補充 Extension integration boundary。
- `wiki/modules/vscode-extension.md`：新增 Extension module page，記錄 WikiSearchModel、RefreshCoordinator、bootstrap contract、help 與安全邊界。
- `wiki/index.md`：同步新 module page 與導覽連結。

這些 Wiki write 僅在 verification 完成 Knowledge Review `promote`、依 hook 宣告的 exact plan 執行；G2 與 implementation 期間保持 read-only。

# 執行計畫：DevWeave 0.2.1 Windows 公開版發布強化

<!-- DEVWEAVE:artifact=plan version=1 work=20260804-205655-feature-devweave-0-2-1-windows -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 PreviewGate 與 host protocol enforcement
- Traces: REQ-001, REQ-002, REQ-003, NFR-001, NFR-002, AC-001, AC-002, AC-003, AC-004, AC-005, DEC-001, DEC-002, DEC-003
- Inputs: `src/model.ts`、`src/protocol.ts`、`src/dashboard.ts`、`src/prompt.ts`、approved PreviewGate interface。
- Output: 純 `PreviewGate` module；Dashboard panel-local panelId/revision；staged bundle copy callback；additive snapshot/bootstrap/actionPreview revision/intent；matching preview、one-shot consume、safe restore 與拒絕訊息。
- Verification: PreviewGate unit tests、protocol parser/security tests、Dashboard handler assertions、typecheck；確認未預覽、錯 intent/panel/revision 不會呼叫 clipboard。
- Dependencies: none

## TASK-002: 修正 legacy copyNextAction 與 host controller flow
- Traces: REQ-004, REQ-006, NFR-001, NFR-002, AC-006, AC-008, DEC-004, DEC-008
- Inputs: TASK-001、`src/extension.ts`、`src/work-selection.ts`、existing command registrations、README/engine explicit work selection contract。
- Output: 保留 `devweave.copyNextAction` ID；單一 active work 開啟 Dashboard 並 host-stage next preview；零/多 work 要求 UI 明確選取；closed work 不成為 next target；controller copy 使用 staged bundle，不直接 compose/clipboard bypass。
- Verification: legacy command tests、multi-work/closed selection tests、Extension Host activation contract、full Extension test suite；確認 command path 不直接呼叫 clipboard。
- Dependencies: TASK-001

## TASK-003: 完成 Webview DOM、multi-work、ARIA/keyboard 與繁中 UI
- Traces: REQ-005, REQ-006, REQ-007, NFR-002, AC-007, AC-008, AC-009, AC-010, DEC-005, DEC-006, DEC-008
- Inputs: TASK-001 protocol metadata、`webview/main.ts`、`webview/styles.css`、`src/presentation.ts`、`wiki-search.ts`、existing focus/CSP/theme seams。
- Output: `#wiki-results` 真實 mount；revision/host-preview stale invalidation；五個 tab/tabpanel ARIA、roving tabindex、方向鍵/Home/End/focus restore；next/status multi-work form guard；empty-state CTA 修正；主要 CTA、native-facing status 與 readiness labels 繁中化；窄視窗/forced-colors CSS。
- Verification: fake-document Wiki mount test、Webview static/interaction tests、presentation/multi-work tests、ARIA/keyboard assertions、typecheck；確認 input focus 與 Enter/type/show-all contract 保持。
- Dependencies: TASK-001

## TASK-004: 建立跨功能 regression test surface
- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-010, NFR-001, NFR-002, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-014, DEC-001, DEC-005, DEC-006, DEC-008
- Inputs: TASK-001 至 TASK-003 的 interfaces/behavior、existing Extension 60-test baseline、Python 94-test baseline、router/CLI/engine contract tests。
- Output: 新增 PreviewGate、protocol、legacy command、stale preview、Wiki DOM mount、ARIA/keyboard、multi-work、bootstrap cancel/failure no-partial-state 與 public command/schema regression；未改名/未改寫既有 Python lifecycle。
- Verification: `npm.cmd run test`、`npm.cmd run typecheck`、`python -B -m unittest discover -s tests -v`；新增測試與 AC/TASK trace 可由 evidence 覆蓋。
- Dependencies: TASK-002, TASK-003

## TASK-005: 產出 0.2.1 bundle 並保留 rollback artifacts
- Traces: REQ-008, NFR-002, NFR-005, AC-011, AC-012, DEC-007
- Inputs: TASK-001 至 TASK-004 的 stable source、`package.json`/lock、`esbuild.mjs`、package-vsix/verifier scripts、既有 0.1.0/0.2.0 VSIX。
- Output: package/lock/bundle metadata/verifier/test fixtures 升至 0.2.1；bundle version 由 package version 產生；`devweave-control-center-0.2.1.vsix` 可驗證，舊 artifacts bytes 保留且 verifier 明確檢查。
- Verification: `npm.cmd run package`、`node scripts/verify-package.mjs`、artifact listing/hash/VSIX entry check；failure 時確認舊 artifact untouched。
- Dependencies: TASK-004

## TASK-006: 完成終端使用者發布文件
- Traces: REQ-009, NFR-002, AC-013, DEC-004, DEC-007
- Inputs: TASK-002、TASK-003、TASK-005 的 final behavior；root README、`vscode-extension/README.md`、`docs/使用手冊.md`、embedded help content。
- Output: Windows/VS Code/Python/Git/Codex support boundary、VSIX 安裝、首次初始化、evolved/conflict fail-closed、Refresh、Codex handoff、legacy command、rollback artifacts 與正確測試數字/0.2.1 版本說明。
- Verification: repository documentation contract/static scans、README/help review、`git diff --check`；文件不得宣稱 Marketplace 或跨平台支援。
- Dependencies: TASK-005

## TASK-007: 完成 high-risk release verification、Knowledge Review 與 G3 artifacts
- Traces: REQ-009, REQ-010, NFR-003, NFR-004, NFR-005, AC-013, AC-014, AC-015, AC-016, DEC-001, DEC-004, DEC-007, DEC-008
- Inputs: TASK-001 至 TASK-006、完整 diff、accepted baselines、四條 disposable Windows walkthrough、current verification evidence。
- Output: doctor/full high profile evidence、fresh/evolved/conflict/multi-active walkthrough record、必要 `.devweave/baseline` updates、Knowledge Review `promote` and plan/seal for up to four content pages plus index/log、完整 acceptance matrix；final artifacts 穩定後 exactly one isolated read-only Independent Review record。
- Verification: `doctor`、`verify` high profile、Extension Host smoke、`git diff --check`、`knowledge status/review/plan/seal`、G3 acceptance validation；review 必須 current `passed` 且無未處理 advisory。
- Dependencies: TASK-005, TASK-006

## 驗證策略

### Targeted

- PreviewGate: stage/take/restore/invalidate、canonical intent match、one-shot consume、panel/revision mismatch。
- Protocol/Dashboard: additive actionPreview intent/revision、host rejects direct copy、clipboard failure restore、selection/refresh/bootstrap invalidation。
- Webview/presentation: Wiki fake-document mount、Enter/type/show-all、snapshot stale clear、five tab ARIA/keyboard/focus、multi-work next/status、繁中 labels。
- Release: package version derivation、verifier retention of 0.1.0/0.2.0、VSIX entry/version/integrity。

### Full profile commands

- `python -B .agents/skills/devweave/scripts/devweave.py doctor`
- `npm.cmd run test`、`npm.cmd run typecheck`、`npm.cmd run package`、`npm.cmd run test:smoke`（cwd `vscode-extension`）
- `python -B -m unittest discover -s tests -v`
- `node scripts/verify-package.mjs`（cwd `vscode-extension`）與 `git diff --check`
- 透過 DevWeave `verify` 以 high profile 登錄五個 current evidence，不以手動命令取代 CLI evidence。

### Manual/high-risk acceptance

- disposable Windows workspace walkthrough：首次安裝/初始化、合法 evolved workspace adoption、reserved conflict fail-closed、multiple active work。
- 每條 walkthrough 驗證取消/失敗無 partial state、未確認不會 copy、Refresh/selection 後舊 preview 必須重新預覽；另檢查窄視窗、forced-colors/high-contrast、Tab/方向鍵/Home/End/focus restore。
- 完成 product source、baseline、Wiki、scope、evidence 穩定後，high-risk 只由唯一 router 啟動 exactly one isolated read-only Independent Review；`passed` 且無 unresolved advisory 才可進 G3。
- `knowledge status` → `knowledge review promote` → `knowledge plan`/必要 scaffold → content/index/log 更新與 seal；verification 前 Wiki 保持唯讀。

## 基線更新計畫

本工作預計在 verification 依實際 diff 透過 DevWeave CLI 宣告並更新：

- `.devweave/baseline/product.md`：0.2.1 Windows release support boundary、preview-first copy safety、legacy command 與首次使用者公開能力。
- `.devweave/baseline/architecture.md`：PreviewGate/Dashboard revision protocol、host copy adapter、Wiki DOM mount/accessibility seam、package version derivation。
- `.devweave/baseline/quality.md`：PreviewGate fail-closed/retry tests、0.2.1/rollback artifact verifier、Windows walkthrough、high-risk review bar 與實際 test/package/smoke counts。

Wiki 只在 verification promote 四個既有 source-bound content pages（`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`），並由 engine coupled 更新 `wiki/index.md`、`wiki/log.md`；不在 G2 或 implementation 直接寫入 Wiki。

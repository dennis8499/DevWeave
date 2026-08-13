# 執行計畫：強化 DevWeave VS Code Extension 治理、驗證與效率

<!-- DEVWEAVE:artifact=plan version=1 work=20260813-142228-feature-devweave-vs-code-extension -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 typed path inspection 與 bootstrap path-kind regression

- Traces: REQ-001, REQ-002, NFR-001, NFR-002, AC-001, AC-002, DEC-001
- Inputs: `vscode-extension/src/filesystem.ts`、VS Code filesystem adapter、bootstrap completeness reader、現有 test adapters。
- Output: `FileSystemPort.inspectPath()` 及 `missing/file/directory/symlink/other` projection；expected file/directory conflict reasons；所有 fake adapter 與 path-kind regression tests 更新。
- Verification: Extension unit tests 覆蓋 missing、file、directory、symlink/other、stat error 與不得覆寫衝突；TypeScript typecheck 通過。
- Dependencies: none

## TASK-002: Snapshot summary/detail、Wiki provenance 與 projection authority

- Traces: REQ-002, REQ-003, REQ-004, REQ-009, NFR-003, AC-002, AC-003, AC-004, AC-009, DEC-002
- Inputs: TASK-001、`WorkspaceSnapshot` model/reader、presentation readiness、Webview knowledge/verification rendering、Wiki parser。
- Output: summary-first refresh 與 bounded selected-detail seam；bounded Wiki body/source hash/truncation/parse diagnostics；`authoritative=false` 與 `engineGateStatus` 明確呈現；移除以 work-item timestamp 假造 engine observation 的路徑。
- Verification: summary/detail latency/read-count tests、malformed Wiki tests、readiness authority tests、security tests、presentation/Webview tests。
- Dependencies: TASK-001

## TASK-003: Clean build provenance、candidate verification 與 pinned smoke baseline

- Traces: REQ-005, REQ-006, NFR-001, NFR-002, AC-005, AC-006, AC-011, AC-012, DEC-003, DEC-007
- Inputs: Extension esbuild/package/smoke scripts、accepted baseline、VSIX builder/verifier、既有 package tests。
- Output: clean dist build；包含 package version/source Git HEAD/bootstrap count/canonical manifest hash 的 manifest；`package-vsix.mjs --output` candidate builder；`verify-package.mjs --artifact` fail-closed verifier；獨立 ReleaseOrchestrator 的 candidate→verify→same-directory atomic promotion transaction；verifier/promotion failure 保留 current/retained artifact；smoke 固定 accepted VS Code `1.131.0` 與 cache-only 行為。
- Verification: transaction seam tests 覆蓋 verify failure、promotion failure、success promotion、candidate cleanup；package contract tests 驗證 script wiring、required args 與 no-argument fail closed；npm typecheck、production package、candidate verifier、current artifact hash/retained artifact preservation、manifest/provenance regression、pinned smoke command；若 accepted runtime 不可用，保留明確 fail evidence。
- Dependencies: none

## TASK-004: Command metadata schema 與 affected-path selective verification

- Traces: REQ-007, NFR-003, AC-007, AC-013, DEC-004
- Inputs: `.agents/skills/devweave/scripts/devweave.py`、`devweave_core.py`、project command/profile schema、既有 Python CLI tests。
- Output: optional `affected_paths`/`writes`/`outputs`/`release_only` metadata；CLI command set 與 project validation；`verify --profile --path` selection、dependency closure、skipped reasons 與 high profile full-set policy。
- Verification: Python unit/CLI/guard/knowledge/contract tests；metadata invalid fail-closed；legacy project compatibility；selected/skipped/dependency/high-profile assertions。
- Dependencies: none

## TASK-005: Evidence metrics、tool/usage bounded payload 與 cross-layer safeguards

- Traces: REQ-008, NFR-001, NFR-003, AC-008, AC-011, AC-013, DEC-005
- Inputs: TASK-002、TASK-004、既有 evidence writer/reader、Extension evidence projection、security/compatibility tests。
- Output: verification selection/skipped/cache metrics 與 optional context/tool/usage metrics 進入既有 evidence；unknown token/cost 為 unavailable；不新增 ledger、不保存 prompt secret；舊 evidence payload 相容。
- Verification: evidence schema regression、metrics redaction/bounds tests、old payload compatibility、guard boundary tests、serialization/readiness projection assertions。
- Dependencies: TASK-002, TASK-004

## TASK-006: 文件、baseline、release rollback 與 G3 knowledge/review 收尾

- Traces: REQ-010, NFR-002, AC-010, AC-012, DEC-006, DEC-007
- Inputs: TASK-001 至 TASK-005 的 diff、README、Extension README、使用手冊、`.devweave/baseline/quality.md`、既有 Wiki context 與 knowledge plan。
- Output: 使用流程、profile/path selection、metrics limits、candidate package/verifier/promotion/rollback 與 retained artifact 文件；完成 current Knowledge Review；只依 declared promote plan 更新受影響 Wiki content、index、log 並 seal；產生 acceptance/evidence 與高風險 isolated review readiness。
- Verification: baseline/README/使用手冊 checks、完整 diff/scope/source fingerprint review、candidate failure evidence 與 current/retained hash reconciliation、knowledge validation、G3 acceptance gate 與 review record readiness。
- Dependencies: TASK-001, TASK-002, TASK-003, TASK-004, TASK-005

## 驗證策略

- Targeted：每個 TASK 先執行其列出的 unit/CLI/contract/security check，並以最小 affected path 驗證 selective profile 的 selected/skipped/dependency closure。
- Regression：完整 Extension unit suite、Python core/guard/knowledge/contract suite、TypeScript typecheck；覆蓋 legacy project、舊 evidence、missing/conflicting bootstrap、malformed Wiki 與無 engine observation。
- Build/package：在乾淨 dist 上執行 production package；確認 builder 只寫同目錄 candidate，verifier 以 `--artifact` 驗證 candidate，成功後 current 才由 atomic promotion 更新；package artifact 必須可由 source Git HEAD 與 file list 重建，verify/promotion failure 必須以 regression evidence 證明 current/retained hash 不變。
- Runtime：只使用 accepted VS Code `1.131.0` cache 執行 smoke；cache 不存在時記錄阻塞 evidence，不以 current 或網路 fallback 取得不相容 runtime。
- High-risk：完成完整 high profile、scope/diff/source fingerprint stability check、security boundary check、migration/rollback/compatibility/performance review，並由 router 取得單一 isolated read-only reviewer 結果後再申請 G3。
- Manual acceptance：確認 Extension 顯示 projection-only、path conflicts、Wiki hash/truncation/parse diagnostics、selection metrics 與 unavailable usage；確認任何 approve/refresh 都回到 engine/CLI 真相。

## 基線更新計畫

- 更新 `.devweave/baseline/quality.md`：記錄 accepted VS Code runtime、candidate-first clean package/provenance verifier、atomic promotion/retained artifact failure contract、profile/path selection、metrics availability/limits 與執行命令。
- 若目前 baseline 已涵蓋上述契約，先以最小 diff 補充缺漏；不修改其他 baseline、state、event 或 evidence ledger。
- TASK-006 的 acceptance 必須列出 baseline 變更與 source Git HEAD；若無需額外頁面，需在 acceptance 明確記錄 no-change rationale。

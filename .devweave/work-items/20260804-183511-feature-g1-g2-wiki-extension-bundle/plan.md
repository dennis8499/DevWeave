# 執行計畫：修正 G1/G2 問答、Wiki 初始化與 Extension bundle 相容性

<!-- DEVWEAVE:artifact=plan version=1 work=20260804-183511-feature-g1-g2-wiki-extension-bundle -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 G1/G2 host-native decision contract

- Traces: REQ-001, REQ-002, REQ-003, AC-001, AC-002, AC-003, DEC-001
- Inputs: approved brief/requirements、現行 router/phase guidance、`grilling` precedence、既有 Gate/artifact contract。
- Output: 更新 DevWeave SKILL、root/target AGENTS、requirements/design references、README/使用手冊與 repository contract tests；明確定義 native-first、structured fallback、推薦/Other、逐題等待與 Gate 不變。
- Verification: `tests/test_repository_contract.py`、repository contract suite、static scan 確認無 pending-question schema/ledger/second router；人工檢查 G1/G2 host capability fallback wording。
- Dependencies: none。

## TASK-002: 修正 Python Wiki compatibility 與 init preflight

- Traces: REQ-004, REQ-005, REQ-006, AC-004, AC-005, AC-006, DEC-002
- Inputs: `knowledge_core.inspect_wiki/bootstrap_wiki`、`devweave_core.init_project/bootstrap_knowledge_work`、accepted Wiki lifecycle contract。
- Output: 讓非保留 custom Wiki 可採用；reserved starter files/directories 先做 type/frontmatter/path preflight；`init_project()` 在 control write 前及 lock 內 recheck，保留 `knowledge_conflict`、no-overwrite 與獨立 `knowledge bootstrap` lifecycle。
- Verification: Python knowledge/core tests 覆蓋 notes-only、reserved invalid、no-partial-init、idempotence、bootstrap create/resume/advisory；`python -B -m unittest discover -s tests -v`。
- Dependencies: none。

## TASK-003: 建立 Extension shared compatibility validator 與 manifest contract

- Traces: REQ-007, REQ-008, NFR-001, AC-007, AC-008, AC-009, DEC-003, DEC-004, DEC-005
- Inputs: `BootstrapBundleFile`、manifest build mappings、現行 exact integrity/path/type/rollback tests。
- Output: 新增小介面的 shared validator module；加入 `existingPolicy`/`compatibility` type 與 normalization；實作 project、三 baseline、三 Wiki starter validator；esbuild manifest 明確宣告七個 compatible kinds；舊 manifest 欄位缺少時安全預設 exact；package verifier 驗證 declarations。
- Verification: bootstrap unit tests、manifest normalization/unknown-kind/integrity tests、package verifier；確認 validator 只接受規定 identity/structure，未知或 malformed policy 在寫入前 fail。
- Dependencies: none。

## TASK-004: 接上 installer、snapshot 與 Extension projection

- Traces: REQ-007, REQ-008, NFR-002, AC-007, AC-008, AC-009, AC-010, DEC-004, DEC-005
- Inputs: TASK-003 shared validator interface、`BootstrapInstaller` write/rollback seam、`WorkspaceSnapshotReader` completeness projection、Extension dashboard messaging。
- Output: installer 與 snapshot 共用 normalized contract/validator；合法 evolved bytes 列 adopted、missing-only write；invalid exact/compatible targets 保留 conflict；UI 只顯示真正 missing/conflict，report/output 保留 created/adopted/rollback observability；不增加 process/network/engine seam。
- Verification: `bootstrap.test.ts`、`bootstrap-projection.test.ts`、snapshot/core/presentation/security tests；Memory adapter 驗證既有 bytes 不變、partial repair、invalid fail-closed、rollback；typecheck/package/smoke。
- Dependencies: TASK-003。

## TASK-005: 完成 profile guidance、regression integration 與 G3 artifacts

- Traces: REQ-006, NFR-002, AC-006, AC-010, DEC-001, DEC-002, DEC-005
- Inputs: TASK-001 至 TASK-004 的 current diff/evidence、baseline targets、stale Wiki gaps。
- Output: 整合 `new`/`feature` prompt-only guidance；更新 `acceptance.md` 與必要 evidence；verification 階段依 knowledge plan 更新最多五個 source-bound content pages、coupled index/log、三份 baseline，完成 Knowledge Review 與 high-risk Independent Review readiness。
- Verification: full high profile、`git diff --check`、G3 scope/baseline/Wiki reconciliation、current review evidence；不在 G2/implementation 直接寫 Wiki。
- Dependencies: TASK-001, TASK-002, TASK-003, TASK-004。

## 驗證策略

### Targeted checks

- Python：knowledge/core/init focused tests，包含 reserved path semantics、preflight no-partial-state、idempotence 與 bootstrap lifecycle。
- TypeScript：BootstrapInstaller、shared validator、snapshot projection、manifest normalization、Extension security/protocol tests。
- Contract：router/phase guidance、native/fallback wording、no-new-state/no-second-router、`new`/`feature` prompt-only guidance。

### Full verification

- `npm.cmd run package`：build、VSIX、manifest/source integrity/package verifier。
- `npm.cmd run test:smoke`：Extension Host activation、views、commands 與 bundle loading。
- `npm.cmd run test`：全部 Extension unit/security/projection/prompt tests。
- `npm.cmd run typecheck`：TypeScript compile contract。
- `python -B -m unittest discover -s tests -v`：Python engine/CLI/guard/repository contract regression。
- `git diff --check`：whitespace safety。

### Manual/high-risk acceptance

- 使用 memory/filesystem fixtures 比對 evolved valid project/baseline/Wiki 與 malformed/invalid/exact drift；確認 installer 與 snapshot 結果一致。
- 確認 Wiki conflict 前不留下 project/baseline/cache/work-item durable state，既有 custom bytes 不變。
- 完成 high-risk current evidence 後，由既有 router 啟動 exactly one isolated read-only Independent Review；reviewer 不寫 source/Wiki/ledger，human G3 approval 仍必要。

## 基線更新計畫

完成前依實際 diff 更新或記錄已涵蓋：

- `.devweave/baseline/product.md`：G1/G2 native-first decision contract、profile guidance 與 evolved bootstrap adoption 能力。
- `.devweave/baseline/architecture.md`：router host seam、Python Wiki preflight、Extension manifest/validator seam 與 data flow。
- `.devweave/baseline/quality.md`：semantic adoption 的 fail-closed/rollback、shared validator、full high verification 與 no-process/no-network contract。

Wiki 只在 verification 依 Knowledge Review/plan promotion 更新 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`（最多四個 content pages），並同步 `wiki/index.md`、`wiki/log.md`；不在 G2 或 implementation 直接寫入。

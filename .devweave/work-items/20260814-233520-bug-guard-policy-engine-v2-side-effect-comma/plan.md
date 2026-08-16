# 執行計畫：建立 Guard Policy Engine v2 並修正 Side-effect Command Policy

<!-- DEVWEAVE:artifact=plan version=1 work=20260814-233520-bug-guard-policy-engine-v2-side-effect-comma -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: CommandPolicy v2 model 與 trusted executable registry

- Traces: REQ-001, REQ-002, NFR-001, AC-001, AC-002, AC-003, AC-004, AC-008, DEC-001, DEC-004
- Inputs: 已核准 requirements、現有 `.devweave/project.json` command/profile、Windows executable paths/hash 與 current phase/risk contract。
- Output: `command_policy.py` 的 typed model/canonicalization/admission helpers、policy/command definition digest 與 mutation impact calculation；project `command_policy_version: 2`、trusted registry 與所有 configured command 的完整 v2 entries；`load_project`/command CLI 的 strict validation。
- Verification: policy schema malformed/legacy/missing-field tests、real path/hash/cwd/symlink/junction/PATH shadow tests、G2 writes denial test、command digest drift test、CLI command-list/set/remove contract tests 與 policy mutation stale test。
- Dependencies: none

## TASK-002: Typed read-only grammar 與 Guard category boundary

- Traces: REQ-002, REQ-004, REQ-005, NFR-001, AC-008, AC-009, AC-010, AC-011, AC-012, DEC-002, DEC-006
- Inputs: TASK-001 policy registry、現有 `guard.py` hook payload seam、git/rg/PowerShell read surface 與 adversarial matrix。
- Output: 移除 `READ_ONLY_PREFIXES`；strict shell argv parser、Git/rg/必要 PowerShell grammar、environment/config/helper restrictions；Guard 與 CLI 都經同一 evaluator，對 read-only、registered、ad-hoc、configured direct Bash 與 typed artifact mutation 分類 fail closed。
- Verification: guard/evaluator unit/integration matrix 覆蓋 `--output`、`--ext-diff`、`-c diff.external`、`--pre`、`--pre-glob`、unknown flag、operators、substitution、redirection、newline/Unicode whitespace、quoted/relative executable、wrapper、symlink、nested cwd、unbound session 與 Windows/POSIX/PowerShell equivalence。
- Dependencies: TASK-001

## TASK-003: Controlled executor、sandbox、snapshot 與 postcondition

- Traces: REQ-003, NFR-002, AC-005, AC-006, AC-007, AC-008, AC-012, DEC-003, DEC-005
- Inputs: TASK-001 policy model、Work Item scope、existing Git snapshot/evidence writer、temporary directory and atomic file APIs。
- Output: temporary full-tree sandbox adapter、pre/post filesystem/Git snapshot diff、declared output/work-scope validator、writes:none violation、dependency/stage barrier、writer candidate fingerprint freeze、postcondition、atomic promotion/rollback 與 bounded observation model。
- Verification: fake-runner synthetic tree tests、writes:none file/tracked-state mutation、undeclared output、shared output exclusivity、writer/read-only ordering、valid tracked-artifact promotion、postcondition/promotion failure preservation、timeout/OSError/snapshot exception fail-closed tests。
- Dependencies: TASK-001

## TASK-004: Verification CLI、release context、profile selection 與 evidence/waiver integration

- Traces: REQ-001, REQ-002, REQ-003, REQ-005, NFR-002, AC-001, AC-002, AC-005, AC-007, AC-008, AC-011, AC-012, DEC-004, DEC-005, DEC-006
- Inputs: TASK-001/003 interfaces、current `verify --command/--profile` and evidence model、explicit user release context contract。
- Output: `ExecutionContext` wiring、`--release-context` typed CLI input、controlled verification path、exit class 2/4 projection、frozen Effective Verification Plan embedded in state、digest-bound observation/eligibility fields、typed one-shot side-effect waiver validation；Runner 與 G3 只讀同一 plan，profile 不再推斷 release authority。
- Verification: direct command denial, release context absence/presence, phase/risk/env/network/timeout tests, G2 plan construction/freeze/parity tests, profile dependency/selection/not-applicable regression, `expect=nonzero/any` ineligibility, waiver exact-match/expiry/digest tests, policy mutation stale tests 與 machine JSON envelope tests。
- Dependencies: TASK-001, TASK-003

## TASK-005: Regression、adversarial 與 deterministic test surface

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, NFR-001, NFR-002, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-011, AC-012, AC-013, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007
- Inputs: TASK-001～004 implementation、existing Python test harness、current Windows Git/Node/Python environment。
- Output: 遷移 `tests/devweave_test_support.py` 與 existing core/CLI/guard/contract tests，新增 policy/executor tests、real wrapper/symlink/nested-repo cases、三次 clean-run comparator；更新 acceptance artifact inputs。
- Verification: targeted policy/guard/core/CLI/contract suites、BUG-01～BUG-07 regression cases、full Python suite、Extension typecheck/tests/package/smoke through controlled executor、G3 plan/evidence eligibility parity、完整 adversarial matrix 連續三次結果相同。
- Dependencies: TASK-002, TASK-003, TASK-004

## TASK-006: Documentation、baseline preparation 與 operational contract

- Traces: REQ-001, REQ-004, REQ-005, NFR-002, AC-009, AC-011, AC-012, AC-013, DEC-001, DEC-002, DEC-006, DEC-007
- Inputs: TASK-001～005 的 final interfaces/evidence、current README/docs、accepted architecture/quality baseline 與 G3 Knowledge Review contract。
- Output: README、`docs/使用手冊.md`、repository contract assertions、baseline update patches；明確記錄 single evaluator、frozen plan、digest/eligibility、controlled executor、mutation stale 與 writer barrier；verification 階段的 Wiki promote plan（overview、workflow、knowledge-engine、command-policy page、index/log）與 acceptance report。
- Verification: docs/contract lint、`git diff --check`、knowledge plan/coverage/seal validation、G3 complete diff/scope/evidence reconciliation。
- Dependencies: TASK-005

## 驗證策略

### Targeted

- `python -B -m unittest discover -s tests -p test_command_policy.py -v`（新增 pure policy、grammar、canonicalization、snapshot seam）。
- `python -B -m unittest discover -s tests -p test_guard.py -v`（hook category/deny matrix）。
- `python -B -m unittest discover -s tests -p test_command_policy.py -v`（single evaluator、plan digest、eligibility、stage/effect seam）。
- CLI/core/contract targeted suites，確認 v2 schema、release context、typed waiver、exit class 與 selection closure。

### Regression/build

- `python -B -m unittest discover -s tests -v`，包含既有 Wiki/ledger/review/gate contract。
- `npm.cmd run typecheck`、`npm.cmd run test`、`npm.cmd run package`、`npm.cmd run test:smoke:current` 一律經 DevWeave registered controlled executor；package 需 explicit release context，並只 promotion declared VSIX/dist outputs。
- `git diff --check`、doctor/hook launcher contract 與 root/nested cwd process checks。

### Manual/adversarial acceptance

- 逐項執行 AC-001～AC-032 的 deny/violation/evidence/postcondition/plan/mutation cases，檢查沒有 process start、actual changed paths、declared outputs、work scope、promotion 與 rollback。
- 對 command definition 的 argv、cwd、writes、outputs、depends_on、timeout、release policy 逐項 mutation，確認 plan/gate/evidence digest 與 currentness 一起 stale。
- 對 `expect=nonzero`、`expect=any`、reproduction、diagnostic、failed、timeout、undeclared writes 與 source/policy drift 確認 `gate_eligible=false`，並確認 G3 只重用 Effective Verification Plan。
- 對 writer/read-only stage、shared output boundary 與 selective profile 比較 Runner 與 G3 的 selected/skipped/not-applicable 集合與 plan digest。
- 對同一 clean fixture 執行完整 policy suite 三次；以 canonical JSON 比較 decision、exit class、changed paths、outputs、snapshot digest 與 evidence summary。
- 以 isolated temporary fixture 測試 PATH shadow、`.cmd`/`.bat` wrapper、POSIX symlink（可用時）、junction/nested repository、環境變數與 Git/rg config injection；權限不足時保存清楚 skipped evidence，不轉成通過。

### High-risk gate

- G2 build validation 必須確認 design/plan trace、command policy version 與 task ledger current。
- G3 前重新 reconcile 完整 Git/filesystem diff、scope、evidence、baseline 與 Wiki diff；high-risk router 啟動 exactly one isolated read-only independent review，critical finding 需 narrow waiver。

## 基線更新計畫

本 Work Item 需要在 verification/G3 依 declared knowledge plan 更新：

- `.devweave/baseline/architecture.md`：新增 CommandPolicy deep module、controlled executor、sandbox/promotion、guard/CLI boundary 與 no-Git-worktree decision。
- `.devweave/baseline/quality.md`：新增 fail-closed grammar、canonical executable/cwd、snapshot/output scope、violation exit class、determinism 與 adversarial verification contract。
- Root Wiki 只在 verification 更新：refresh `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`，新增 `wiki/modules/command-policy-engine.md`，並同步 `wiki/index.md`、`wiki/log.md`；最多五個 content upsert，所有受影響頁面需 source fingerprint、content hash 與 seal。

Implementation/G2 期間 Wiki、baseline 與 machine ledgers 保持唯讀；所有 Work Item artifacts 與 ledger 只經 DevWeave typed path/CLI 修改。

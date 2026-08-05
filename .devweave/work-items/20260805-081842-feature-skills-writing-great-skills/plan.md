# 執行計畫：優化專案 Skills 可預測性（排除 writing-great-skills）

<!-- DEVWEAVE:artifact=plan version=1 work=20260805-081842-feature-skills-writing-great-skills -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 固定 upstream baseline 與 exclusion scope
- Traces: REQ-001, REQ-004, NFR-001, AC-001, AC-004, DEC-001, DEC-004
- Inputs: G1 approved brief/requirements、`skills-lock.json`、五個 upstream source/path、六個目標 Skill 與 `writing-great-skills`。
- Output: 完成 upstream/local instruction diff 審查、記錄目標 Skill 與 writer 的 pre-change hashes，確認 lock/source/path/hash 與 Extension explicit six-Skill bundle 不需變更。
- Verification: source/lock inspection、relative-link inventory、scope check；任何 writer 或 lock diff 都使 task failed。
- Dependencies: none

## TASK-002: 優化 DevWeave router 與 phase references
- Traces: REQ-002, REQ-003, NFR-002, AC-002, AC-003, AC-004, DEC-002, DEC-003
- Inputs: TASK-001 baseline、approved `devweave/SKILL.md`、`references/requirements-phase.md`、`design-phase.md`、`implementation-phase.md`、`verification-phase.md`、`profiles.md` 與 `contracts.md`。
- Output: `devweave` 保留唯一 router、machine contract、Wiki-first、Gate、binding、review 與 human approval；SKILL.md 與 phase references 具有清楚 branch pointers、completion criteria、正向指令與無重複的 source of truth。
- Verification: frontmatter/link validation、DevWeave contract token inspection、read-only G1/G2/G3 routing scenario；不修改 Python engine、templates 或 runtime scripts。
- Dependencies: TASK-001

## TASK-003: 優化五個 companion Skill 套件
- Traces: REQ-001, REQ-002, REQ-003, NFR-001, AC-002, AC-003, DEC-002, DEC-003
- Inputs: TASK-001 baseline、`codebase-design` references、`diagnosing-bugs`、`grill-me`、`grilling`、`tdd` references 與 approved phase boundaries。
- Output: 六個目標 Skill 的 descriptions、SKILL.md、必要 Markdown references 與 UI metadata 一致；補 completion criteria、native-first question contract、seam/TDD boundary、red-capable diagnosis；移除不存在 Skill 與未授權 side-effect 指示。
- Verification: per-skill UTF-8 validation、relative-link checks、metadata/invocation contract、isolated read-only forward scenarios；`writing-great-skills` 不得被讀寫或納入 diff。
- Dependencies: TASK-001, TASK-002

## TASK-004: 同步必要 root policy 與 repository contract
- Traces: REQ-001, REQ-003, REQ-004, NFR-001, NFR-002, AC-001, AC-004, AC-005, DEC-004, DEC-005
- Inputs: TASK-002/003 optimized Skill content、既有 `AGENTS.md`、`tests/test_repository_contract.py`、accepted architecture/quality baseline。
- Output: root policy 明確標記 maintenance-only exclusion；repository contract 驗證 exact companion set、frontmatter、metadata、relative links、invocation policy 與 writer exclusion；baseline 變更留到 verification 宣告。
- Verification: targeted repository contract tests、scope/diff inspection、public CLI/schema/Hook and bundle manifest comparison。
- Dependencies: TASK-002, TASK-003

## TASK-005: 執行 deterministic forward/regression/build verification
- Traces: REQ-001, REQ-002, REQ-003, NFR-001, NFR-002, AC-002, AC-003, AC-004, AC-005, DEC-005
- Inputs: TASK-004 complete source、current G2 task ledger、project verification profiles。
- Output: current evidence 覆蓋每個 AC/TASK；包含 UTF-8 skill checks、isolated read-only forward scenarios、Python full suite、Extension tests/typecheck/package/smoke、lock/exclusion hash 與 `git diff --check`。
- Verification: 以 DevWeave `verify`/evidence CLI 記錄所有 required commands；失敗時停留 verification 並依原因 revise，不使用寬泛 waiver。
- Dependencies: TASK-004

## TASK-006: 完成 baseline、Wiki promotion 與 G3 acceptance
- Traces: REQ-003, REQ-004, NFR-001, NFR-002, AC-001, AC-004, AC-005, DEC-004, DEC-006
- Inputs: TASK-005 current evidence、完整 diff、`knowledge status`、affected-page report、accepted baseline。
- Output: 更新並宣告 `.devweave/baseline/architecture.md`、`.devweave/baseline/quality.md`；以 `knowledge review promote`、最多兩個 content upsert、coupled index/log、seal 與 Traditional Chinese `acceptance.md` 完成 G3。
- Verification: full diff/scope reconciliation、Knowledge Review currentness、affected pages refreshed/sealed、baseline targets declared/changed、`validate --gate acceptance` 與 explicit human G3 approval。
- Dependencies: TASK-005

## 驗證策略

- Static: UTF-8 `quick_validate.py`、repository frontmatter/metadata/link contract、stale reference scan、lock/writer hash comparison。
- Behavior: fresh isolated read-only scenarios for DevWeave feature routing, G1 grilling, G2 codebase design, bug diagnosis and post-G2 TDD; no delegated workspace writes。
- Regression/build: `unit-tests`、`extension-tests`、`extension-typecheck`、`extension-package`、`extension-smoke` 與 `git diff --check`。
- Manual acceptance: new session discovery、exact six-Skill bootstrap manifest、explicit Gate stop behavior、writer untouched、lock unchanged、no public interface drift。
- Evidence: 每個 EVID 必須綁定 current source fingerprint、Git HEAD、AC/TASK IDs；G3 前重新執行 `knowledge status`、Knowledge Review、完整 diff 與 scope reconciliation。

## 基線更新計畫

- 更新 `.devweave/baseline/architecture.md`：記錄 local Skill optimization overlay、maintenance-only exclusion、唯一 router/companion boundary 與 upstream lock provenance。
- 更新 `.devweave/baseline/quality.md`：記錄 completion-criteria/reference/link/metadata contract、writer exclusion、lock preservation 與 deterministic forward/package verification。
- 不更新 `.devweave/baseline/product.md`，因產品能力、使用者目標與公開 lifecycle 不變。
- G3 promote `wiki/overview.md` 與 `wiki/architecture/devweave-knowledge-workflow.md`，自動同步 `wiki/index.md`/`wiki/log.md`；G2/implementation 期間 Wiki 保持 read-only。

# 執行計畫：整合 Wiki-first 探索與知識提升

<!-- DEVWEAVE:artifact=plan version=1 work=20260802-200224-feature-wiki-first -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 knowledge core、page schema 與 starter assets

- Traces: REQ-001, REQ-005, REQ-006, REQ-007, REQ-011, NFR-001, NFR-002, AC-001, AC-005, AC-006, AC-007, AC-011, AC-013, AC-014, DEC-001, DEC-002, DEC-003, DEC-007, DEC-008
- Inputs: 已核准的 Wiki root、page types、frontmatter、fingerprint、bootstrap/adoption 與 lint contract；授權來源 commit。
- Output: 標準函式庫-only `knowledge_core.py`、Wiki starter/page assets、非破壞 bootstrap、frontmatter parser/writer、source/tree fingerprint 與 deterministic health/lint primitives。
- Verification: Targeted unit tests涵蓋空白/相容/衝突 bootstrap、所有 page types、Windows/POSIX paths、file/directory/dirty/rename/delete fingerprints、links/index/log 與 atomic failure。
- Dependencies: none

## TASK-002: 整合 project/work state、G1/G3 lifecycle 與 fingerprints

- Traces: REQ-002, REQ-003, REQ-004, REQ-008, REQ-009, REQ-011, AC-002, AC-003, AC-004, AC-008, AC-009, AC-011, DEC-002, DEC-004, DEC-005, DEC-007, DEC-008
- Inputs: TASK-001 knowledge primitives；現有 project defaults、work creation、scope/build/acceptance fingerprints、sync、status、instructions 與 gate validator。
- Output: Additive project defaults、新 work knowledge state、legacy detection、Wiki-first context validation、affected-page calculation、G3 plan/diff/lint/new-overview rules、knowledge-aware status/instructions 與獨立 acceptance fingerprint。
- Verification: Core tests證明 G1 context門檻、unrelated stale warning、affected refresh/delete、new overview、Wiki-only evidence stability、post-G3 invalidation與 legacy active work相容。
- Dependencies: TASK-001

## TASK-003: 加入 machine CLI 與最小權限 guard

- Traces: REQ-008, REQ-010, NFR-002, AC-008, AC-010, AC-014, DEC-004, DEC-006
- Inputs: TASK-002 state transitions、phase rules、planned targets 與 current CLI/guard JSON contracts。
- Output: `knowledge status/context/plan/seal` argparse handlers、stable JSON diagnostics/events，以及 verification/acceptance exact-path Wiki allowlist；維持單一 Codex PreToolUse hook。
- Verification: CLI tests涵蓋 arguments、replace semantics、phase/gate errors與 exit codes；guard tests涵蓋 unbound、G2前、implementation、planned/coupled/undeclared/traversal paths。
- Dependencies: TASK-002

## TASK-004: 更新單一 skill、phase contracts 與使用文件

- Traces: REQ-002, REQ-003, REQ-007, REQ-012, NFR-003, AC-002, AC-003, AC-007, AC-012, AC-015, DEC-001, DEC-009
- Inputs: TASK-002、TASK-003 的實際 machine interface與行為；skill-creator metadata constraints。
- Output: 精簡更新 `SKILL.md`、requirements/verification references、contracts、`agents/openai.yaml`、AGENTS、README 與必要 fixtures；清楚說明 Wiki/baseline 分工、G1/G3 sequence、legacy/conflict recovery 與 hook限制。
- Verification: Repository contract tests、cross-reference/search audit 與 `quick_validate.py .agents/skills/devweave`；確認無第二 skill、無公開 chat verb 漂移、metadata strings 合規。
- Dependencies: TASK-002, TASK-003

## TASK-005: 完成回歸、E2E 與高風險驗證覆蓋

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, NFR-001, NFR-002, NFR-003, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-011, AC-012, AC-013, AC-014, AC-015, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008, DEC-009
- Inputs: TASK-001 至 TASK-004 的完成實作與既有 48-test baseline。
- Output: 擴充 unit/CLI/guard/repository tests與暫存 fixture E2E，修正所有 regression，產生 acceptance、regression、review evidence 所需的可重現結果。
- Verification: `python -B -m unittest discover -s tests -v` 全綠；skill quick validation 全綠；fixture 完成 `init → feature → G1/G2 → source change → blocked G3 → Wiki plan/seal/index/log → G3/close`。
- Dependencies: TASK-001, TASK-002, TASK-003, TASK-004

## 驗證策略

- Targeted：新增 knowledge core tests，直接覆蓋 bootstrap/adoption/conflict、frontmatter、source/tree hash、lint、append-only log 與 path safety。
- State/gate：擴充 core harness 建立 knowledge-aware與 legacy states，驗證 fingerprint domain、affected pages、new overview、G1/G3 invalidation與 warning/error分界。
- CLI/guard：以 JSON-first subprocess 與 hook payload fixtures驗證所有 machine operations、phase enforcement及 exact-path allowlist。
- Regression：由 DevWeave `unit-tests` configured command執行完整 suite，要求所有風險等級。
- Skill：執行 skill-creator `quick_validate.py`，並檢查 only-router與 metadata/public verbs contract。
- Manual acceptance：在 temp repository 執行完整 feature lifecycle，檢視 Wiki Markdown、index、log、state summary與 G3 diagnostics。
- High-risk review：對 migration、rollback、path security、legacy loading、fingerprint separation、guard bypass boundary與performance characteristics做獨立 code/diff review，登錄 current review evidence。

## 基線更新計畫

- 更新 `.devweave/baseline/product.md`：加入 Wiki-first exploration 與 verified knowledge promotion 的 accepted capability。
- 更新 `.devweave/baseline/architecture.md`：記錄 product/baseline/knowledge 三個 fingerprint domain、single router 與 phase authorization boundary。
- 更新 `.devweave/baseline/quality.md`：記錄 zero-dependency、path safety、append-only log、legacy compatibility、unit/skill/E2E verification policy。
- 本工作項不建立 framework root `wiki/`；baseline targets 會在 verification phase 透過 CLI 完整宣告。

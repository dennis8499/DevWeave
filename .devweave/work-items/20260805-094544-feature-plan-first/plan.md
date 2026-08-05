# 執行計畫：建立 Plan-first 原生問答流程

<!-- DEVWEAVE:artifact=plan version=1 work=20260805-094544-feature-plan-first -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立共用 native question contract 與 Plan-first router policy

- Traces: REQ-001, REQ-002, REQ-003, REQ-005, NFR-001, AC-001, AC-003, AC-005, AC-006, AC-008, AC-010, DEC-001, DEC-002, DEC-004, DEC-005
- Inputs: approved `brief.md`/`requirements.md`、目前 host tool observation、DevWeave router 與 G1/G2/G3 phase references。
- Output: `.agents/skills/devweave/references/native-question-contract.md`、`AGENTS.md`、`.agents/skills/devweave/SKILL.md` 與 phase references 明確定義 canonical `request_user_input`、Plan-first、ordinary pre-G2 return、structured fallback、Gate adapter 與 no-new-state boundary。
- Verification: targeted static scan 確認一題/2–3 options/recommended/Other、Plan-first、fallback、未回答停住、G2 write boundary、`approve`/`revise` 與 host capability wording。
- Dependencies: none。

## TASK-002: 同步 project-local Skills 與使用者文件

- Traces: REQ-006, NFR-001, NFR-002, AC-009, AC-010, AC-011, DEC-003, DEC-005
- Inputs: TASK-001 shared contract。
- Output: `grill-me`、`grilling`、`codebase-design`、`diagnosing-bugs`、`tdd` 及 `README.md`/`docs/使用手冊.md` 指向共用 contract；所有需要 user choice 的 Skill 使用同一 Plan-first/native/fallback rule，不建立第二 router/state。
- Verification: repository contract tests、Skill frontmatter/invocation/link/UTF-8 checks、documentation search 確認沒有與 Plan-first 或 single-router 衝突的舊說法。
- Dependencies: TASK-001。

## TASK-003: 擴充 policy contract tests 與 deterministic fallback checks

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, NFR-002, NFR-003, AC-001, AC-002, AC-003, AC-005, AC-006, AC-007, AC-008, AC-009, AC-011, AC-012, DEC-001, DEC-002, DEC-003, DEC-004
- Inputs: TASK-001/002 policy and reference files、既有 `tests/test_repository_contract.py`。
- Output: tests 驗證 Plan-first、native contract、ordinary pre-G2 stop/return、post-G2 implementation boundary、new-decision `revise`、Gate safety、no question state/CLI/Extension UI、existing fallback compatibility。
- Verification: targeted repository contract suite、root Python unit suite、`git diff --check`。
- Dependencies: TASK-001, TASK-002。

## TASK-004: 完成 host capability 與人工對話驗收 evidence

- Traces: REQ-001, REQ-003, REQ-004, REQ-005, NFR-001, NFR-003, AC-001, AC-002, AC-004, AC-005, AC-006, AC-007, AC-008, AC-010, AC-012, DEC-002, DEC-004, DEC-005
- Inputs: implemented policy、current Codex host tool list、managed work lifecycle、existing validation commands。
- Output: source-bound evidence 覆蓋 Plan Mode native round-trip、ordinary/Skill capability visibility、fallback、cancel/timeout/malformed、G1/G2/Gate、post-G2 ordinary task 與 implementation 中回到 Plan Mode。普通 host 未暴露工具時記錄 unavailable/compatibility，不宣稱 native pass。
- Verification: manual acceptance records linked to AC/TASK IDs；不得修改 product source/ledger outside CLI，不得把 user-facing conversation 內容整批持久化。
- Dependencies: TASK-001, TASK-003, current G2 approval。

## TASK-005: 完成 full verification、Knowledge Review 與交付整理

- Traces: NFR-002, NFR-003, AC-010, AC-011, AC-012, DEC-001, DEC-003, DEC-005
- Inputs: all implementation diff、test/manual evidence、current Wiki context、accepted baselines。
- Output: `acceptance.md`、current Knowledge Review；若確認 Plan-first/native host boundary 是 durable reusable knowledge，於 G3 以 promote 更新 overview/architecture/knowledge-engine content pages、coupled index/log 並 seal；若沒有 durable uncovered knowledge，使用有理由的 no-update。Baseline 不新增 migration；既有 accepted native-first/fallback baseline 保持相容。
- Verification: configured standard profile、complete diff/scope reconciliation、Wiki lint/context/review/plan/seal obligations、G3 acceptance summary。
- Dependencies: TASK-004。

## 驗證策略

- Targeted：`tests/test_repository_contract.py`、exact API scan、Skill/reference link and metadata checks、`git diff --check`。
- Root regression：`python -B -m unittest discover -s tests -v`。
- Extension regression：`npm.cmd run typecheck`、`npm.cmd run test`、`npm.cmd run package`、`npm.cmd run test:smoke`；確認 Extension 仍不呼叫 Codex API、不新增 question UI、不繞過 prompt handoff。
- Host/manual：Plan Mode native tool visibility/round-trip；ordinary mode tool visibility；Skill-triggered pre-G2 return；structured fallback；cancel/timeout/malformed；G1/G2/Gate；G2 後 ordinary TDD 與新 decision `revise`。
- Safety：工具不可用或 malformed 時不得猜答案、寫 artifact、approve Gate 或開始 implementation；existing VSIX dirty path 不得進入 scope diff。

## 基線更新計畫

- 不修改 product baseline 的既有治理語義或 version schema；native-first/fallback、single router、no-new-state 能力保持相容。
- G3 Knowledge Review 依實際 durable change 選擇 `promote` 或有理由的 `no-update`。若 promote，最多 upsert/delete 五個 content pages，優先更新 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`，同步 `wiki/index.md`/`wiki/log.md` 並 seal；Wiki 在 G2/implementation 期間唯讀。
- 不建立 host-side release artifact、普通模式 capability claim 或 production instrumentation；host ordinary support 只有在外部 host/manual evidence current 時才可標記通過。

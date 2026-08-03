# 執行計畫：整合 Codebase LLM Wiki 閉環

<!-- DEVWEAVE:artifact=plan version=1 work=20260803-161041-feature-codebase-llm-wiki -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 深化 Knowledge Model 與 Canonical Scaffold

- Traces: REQ-002, REQ-003, REQ-007, REQ-008, REQ-009, NFR-002, NFR-003, AC-002, AC-003, AC-007, AC-008, AC-009, AC-014, AC-015, DEC-001, DEC-005, DEC-006, DEC-008
- Inputs: 現有 `knowledge_core`、九種 templates、Wiki source/path/lint/seal 契約
- Output: Bootstrap assessment、context records、coverage、template renderer/exclusive scaffold 與 seal preflight；templates 產生 placeholder 且所有型別欄位可驗證
- Verification: `python -B -m unittest tests.test_knowledge -v` 覆蓋九種類型、Windows/POSIX path、invalid sources、no-overwrite、placeholder/token、critical lint、assessment 與 coverage
- Dependencies: none

## TASK-002: 實作 Bootstrap、Review 與 Additive Lifecycle State

- Traces: REQ-001, REQ-002, REQ-003, REQ-005, REQ-006, REQ-007, REQ-010, NFR-001, AC-001, AC-002, AC-003, AC-005, AC-006, AC-007, AC-010, AC-013, DEC-002, DEC-003, DEC-004, DEC-006
- Inputs: TASK-001 interfaces、現有 create/load/sync/status/context/plan/G3 validation
- Output: New-state marker/profile/review/plan fingerprint、idempotent bootstrap work selection、phase-aware context currentness、review invalidation、coverage/status/instructions與 bootstrap G3 checks
- Verification: `python -B -m unittest tests.test_devweave_core -v` 覆蓋 create/resume/complete、legacy/new state、context drift、review dispositions/source invalidation、plan cap、bootstrap product-diff/core-page條件
- Dependencies: TASK-001

## TASK-003: 擴充 Machine CLI、Guard 與完整 Workflow Contract

- Traces: REQ-001, REQ-004, REQ-005, REQ-008, REQ-009, REQ-010, REQ-012, NFR-002, AC-001, AC-004, AC-005, AC-008, AC-009, AC-010, AC-012, AC-014, DEC-001, DEC-002, DEC-003, DEC-005, DEC-008
- Inputs: TASK-002 lifecycle functions、既有 argparse JSON adapter、guard planned-path policy
- Output: `knowledge bootstrap/review/scaffold` parser與 JSON payload、single-router/phase instructions、guard/CLI fail-closed parity、temporary-repository end-to-end fixture
- Verification: `python -B -m unittest tests.test_cli tests.test_guard tests.test_repository_contract -v`，另驗證未知參數、錯 phase、未綁 plan、CLI exit/JSON 與 G1→G3 flow
- Dependencies: TASK-002

## TASK-004: 擴充 Extension Model、Snapshot、Protocol 與 Composer

- Traces: REQ-011, NFR-001, NFR-003, AC-011, AC-013, AC-015, DEC-007
- Inputs: TASK-002 additive state/status shapes、既有 filesystem-only snapshot 與 fail-closed protocol
- Output: `wikiBootstrap` intent、精確 prompt/mutation警告、bootstrap/coverage/review projections、verifiedBy與 legacy-safe snapshot parsing
- Verification: `npm.cmd test -- --test-name-pattern="snapshot|prompt|protocol|Wiki"` 或對應 unit test filter；確認 extra fields/unknown machine intents拒絕且不重算 Git fingerprint
- Dependencies: TASK-002

## TASK-005: 加入 Extension 三個 Wiki Bootstrap 入口

- Traces: REQ-011, REQ-012, NFR-002, AC-011, AC-012, AC-014, DEC-007
- Inputs: TASK-004 intent/composer/projection、既有 Dashboard preview/copy與 Command Palette registration
- Output: Dropdown option、Knowledge recommendation CTA、`devweave.wikiBootstrap` Command Palette modal preview/copy，以及 Knowledge UI 的 bootstrap/coverage/review呈現
- Verification: Extension core/security tests、package contribution assertion與 smoke activation；證明無 process/network/direct Wiki write，三入口產生相同 prompt
- Dependencies: TASK-004

## TASK-006: 同步 Router、Contracts 與使用文件

- Traces: REQ-004, REQ-012, NFR-003, AC-004, AC-012, AC-015, DEC-003, DEC-006, DEC-008
- Inputs: TASK-003 machine contract、TASK-005 Extension surface、已核准設計
- Output: SKILL、requirements/verification references、contracts、AGENTS、README、繁中手冊與 Extension README一致描述 Bootstrap→Query→Review→Promotion及 non-goals
- Verification: Repository contract tests、全文檢查 public命令/五頁上限/no-update語意，及 skill quick validation
- Dependencies: TASK-003, TASK-005

## TASK-007: 完成高風險 Lifecycle 與回歸驗證準備

- Traces: NFR-004, AC-016, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008
- Inputs: TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006
- Output: 補齊 bootstrap→G1/G2→review/plan/scaffold/seal→G3、一般 promote/no-update、legacy與 Extension security regression；整理驗收 matrix 所需 evidence mapping
- Verification: Root unit suite、Extension tests/typecheck/package/smoke 的 targeted dry run，且每個 AC 至少被一項 test/evidence覆蓋
- Dependencies: TASK-001, TASK-002, TASK-003, TASK-004, TASK-005, TASK-006

## 驗證策略

- TDD：implementation 先新增/調整 module-interface tests，觀察預期失敗，再完成最小實作；不測 private helper 狀態。
- Python targeted：`tests.test_knowledge`、`tests.test_devweave_core`、`tests.test_cli`、`tests.test_guard`、`tests.test_repository_contract`。
- Extension targeted：model/protocol/composer/snapshot unit tests、三入口 DOM/source contract、security regression與 Extension Host command registration。
- Full configured high-risk commands：`unit-tests`、`extension-tests`、`extension-typecheck`、`extension-package`、`extension-smoke`，全部透過 `devweave verify` 記錄 current source evidence。
- Skill validation：使用現有 skill-creator quick validator；結果以 evidence add 記錄。
- Manual acceptance：檢查 CLI JSON、status/instructions next action、Wiki 3–5頁 bootstrap完成、no-update不產生 Wiki diff，以及三個 Extension入口的精確 prompt。
- Independent review：G3 前檢視完整 product/Wiki/baseline diff，特別審查 legacy bypass、source invalidation、path containment、Extension no-execution與 gate不可繞過性，記錄 review evidence。

## 基線更新計畫

- `.devweave/baseline/product.md`：新增 `$devweave wiki bootstrap`、每個新式 Work Item knowledge review與持續 Wiki 累積能力，取代「公開 verbs 固定八個／無 no-update rationale」舊敘述。
- `.devweave/baseline/architecture.md`：記錄 knowledge model/workflow policy/CLI/Extension adapter seams、additive state與 bootstrap profile資料流。
- `.devweave/baseline/quality.md`：記錄五頁上限、scaffold/seal safety、legacy compatibility、Extension prompt-only及新增高風險 verification基線。
- Live Wiki 在 verification 依 `knowledge status/review/plan` 決定；預期 promote overview、knowledge engine module與 lifecycle architecture，最多五個內容 targets，並同步 index/log/seal。

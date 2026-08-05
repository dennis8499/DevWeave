# 需求與驗收條件：建立 Plan-first 原生問答流程

<!-- DEVWEAVE:artifact=requirements version=1 work=20260805-094544-feature-plan-first -->

## REQ-001: Plan-first G1/G2 問答入口

- Priority: must
- Acceptance: AC-001, AC-002
- Description: DevWeave 在 G1/G2 尚未取得 current approval 時，將 Plan Mode 定義為需要使用者 material decision 的正式入口；可由 host 觀察到原生工具時，router 必須使用 `request_user_input`，不能先用自由文字提問。

## REQ-002: Canonical native question contract

- Priority: must
- Acceptance: AC-003, AC-004
- Description: Router/Skills 使用 canonical host seam `request_user_input`，每次只提出一題，包含兩至三個互斥選項、第一個選項標記 `(Recommended)`、每項 trade-off/description 與 host-provided `Other`；answer 必須等待並正規化後才回流目前 artifact。

## REQ-003: 普通模式 pre-G2 stop/return 與相容 fallback

- Priority: must
- Acceptance: AC-005, AC-006
- Description: 普通模式在 G2 前觸發 material requirement/design decision 時，先要求回到 Plan Mode；若 host 不支援該模式或工具不可見，才顯示同一份 structured numbered fallback，並保留自訂答案入口，不猜答案、不推進 phase。

## REQ-004: G2 後 implementation boundary

- Priority: must
- Acceptance: AC-007
- Description: G2 current 且 approved 後，普通模式可執行已批准的 implementation/test task；若 implementation/Skill 發現新的 material requirement、design、scope 或 task decision，必須停止並透過 `revise` 回到最早受影響 phase。

## REQ-005: Gate answer safety

- Priority: must
- Acceptance: AC-008
- Description: G1/G2/G3 的 native answer 只收集 approve/revise/stop 意圖；router 仍須先完成對應 validation，並透過既有 `approve`/`revise` contract 執行，不因 tool response 直接繞過 Gate。

## REQ-006: 所有 project-local Skills 共用問答規則

- Priority: must
- Acceptance: AC-009
- Description: `devweave`、`grill-me`、`grilling`、`codebase-design`、`diagnosing-bugs` 與 `tdd` 在需要使用者選擇時遵循同一 native-first/Plan-first/fallback contract；不新增 parallel router、question state 或 ledger。

## NFR-001: Host capability boundary

- Priority: must
- Acceptance: AC-010
- Description: Repository 必須明確區分 host-provided tool availability 與 repository policy；普通模式的原生工具支援列為外部 prerequisite，未支援 host 不得被文件或測試誤標為 native-capable。

## NFR-002: Compatibility and determinism

- Priority: must
- Acceptance: AC-006, AC-011
- Description: 未提供原生工具的 host 維持 deterministic structured fallback；既有 CLI、artifacts、Gate names、state schema、Extension prompt handoff 與現有 user workflows 保持相容。

## NFR-003: Verification and traceability

- Priority: must
- Acceptance: AC-012
- Description: Policy/contract tests 必須驗證 Plan-first、單題 native contract、fallback、stop/return、Gate safety 與 no-new-state 邊界；host tool visibility、answer round-trip、取消、逾時與 malformed result 需以可追溯 manual/integration evidence 驗證。

## 假設與限制

- 本 work 不控制 Codex host 的 tool injection；目前可可靠保證 Plan Mode，普通/Skill context 的 native support 需外部 host 更新或 integration evidence。
- `request_user_input` 是本環境 canonical tool name；repository 不建立 `requestUserInput` alias 或 fake implementation。
- Facts 可由 Wiki/source 查出的不轉成使用者問題；只有 material decision、Gate choice 或確實需要使用者輸入的問題使用問答 contract。
- Fallback 不代表 approval；未回答、取消、逾時與 malformed answer 都保持 phase blocked 或回到明確 fallback，不得推定選項。
- G1/G2/G3 的 explicit human approval semantics、`revise` invalidation、G2 write boundary 與 Knowledge Review policy 不變。

## 需求與驗收條件

## AC-001: G1 在 Plan Mode 使用原生問答

- Requirement: REQ-001
- Scenario: Given managed work item 尚未取得 G1 approval 且存在 material requirement decision, When router 在 host 暴露 `request_user_input` 的 Plan Mode 提問, Then 使用者看到單題原生選項視窗，且下一題/下一個 artifact action 不會在回答前發生。

## AC-002: G2 在 Plan Mode 使用原生問答

- Requirement: REQ-001
- Scenario: Given current G1 且尚未取得 G2 approval, When `codebase-design` 需要確認 module/interface/seam/design trade-off, Then router 使用同一 native question contract，回答回流 `design.md`/`plan.md`，未回答不得開始 product implementation 或 tracked-test mutation。

## AC-003: Native payload contract

- Requirement: REQ-002
- Scenario: Given native tool visible, When router asks a material decision, Then exactly one question is sent with two or three mutually exclusive options, first option contains `(Recommended)`, every option has a description, and host `Other` remains available.

## AC-004: Native answer return

- Requirement: REQ-002
- Scenario: Given user selects an option, chooses `Other`, cancels, or submits malformed/empty input, When host returns the result, Then router preserves the question identity, records only a valid answer, and waits or reports a blocker for invalid/cancelled results without guessing.

## AC-005: Ordinary pre-G2 returns to Plan Mode

- Requirement: REQ-003
- Scenario: Given G1/G2 is incomplete and a user invokes a Skill in ordinary mode that needs a material decision, When native tool is not visible, Then the conversation explicitly requests Plan Mode and does not modify artifacts, approve a Gate, or start implementation.

## AC-006: Structured fallback compatibility

- Requirement: REQ-003, NFR-002
- Scenario: Given host cannot expose or switch to native question mode, When the user elects to continue, Then router renders the same one-question numbered options, recommendation, descriptions, and explicit custom-answer entry; it never emits an unbounded freeform question.

## AC-007: Post-G2 ordinary implementation

- Requirement: REQ-004
- Scenario: Given current approved G2 and pending implementation task, When ordinary mode invokes `tdd` or an implementation Skill, Then it can execute only the approved task loop; a newly discovered material decision stops work and routes through `revise` before further mutation.

## AC-008: Gate safety

- Requirement: REQ-005
- Scenario: Given a validated G1/G2/G3 summary, When native answer is approve, revise, stop, cancel, or ambiguous, Then only an explicit valid approve/revise action invokes the existing CLI contract; all other results leave the Gate pending.

## AC-009: Companion Skill consistency

- Requirement: REQ-006
- Scenario: Given any of the six governed local Skills needs user input, When its Skill guidance is loaded, Then it points to the same Plan-first/native/fallback rule and does not create another lifecycle, question state, or ledger.

## AC-010: Host capability is not overstated

- Requirement: NFR-001
- Scenario: Given host exposes the tool only in Plan Mode, When repository contract/manual verification runs ordinary-mode checks, Then evidence records ordinary native support as unavailable rather than treating policy text as proof of host capability.

## AC-011: Existing contract compatibility

- Requirement: NFR-002
- Scenario: Given existing CLI, work artifacts, Extension prompt handoff, and non-native host, When the new policy is applied, Then existing commands/artifacts/state schema remain valid and fallback remains deterministic.

## AC-012: Verification coverage

- Requirement: NFR-003
- Scenario: Given implementation is complete, When repository and host verification runs, Then contract tests, Python/Extension checks, Plan Mode native round-trip, ordinary-mode capability check, fallback, cancel/timeout/malformed and pre-G2/post-G2 manual flows produce current evidence linked to the requirements.

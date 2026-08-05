# 需求與驗收條件：初始 Plan Mode 導流

<!-- DEVWEAVE:artifact=requirements version=1 work=20260805-184040-feature-plan-mode -->

## 假設與限制

- 本工作是 `feature`、`standard` risk；既有 command catalog、Work Item lifecycle 與 G1/G2/G3 gate protocol 維持有效。
- `request_user_input` 的可見性是唯一可用的 host capability 證據。Repository、Router instruction、CLI 與 Extension 不讀取或切換 host mode。
- `new`、`feature`、`refactor`、`bug`、`wiki bootstrap` 與會回到 G1/G2 的 `revise` 必須在任何 Work Item 建立或修改前完成 preflight；未初始化 repository 的既有 `init` 啟動例外維持，但 `start` 前仍需 preflight。
- host capability 不可見時，Router 提示切換 Plan Mode 並停止；只有使用者明確選擇 compatibility 才進入一次一題、具推薦選項與 host Other 的 numbered fallback。取消、timeout、malformed 或 ambiguous result 不得猜測或通過 gate。
- Control Center 只在總覽、mutation preview 與 copy result 提供 handoff；不新增 checkbox、host command、fake adapter、question state 或 Help 專用內容，copy 仍可用。
- `PlanModeGuidance` 為 `PromptBundle` 與 `SnapshotGuidance` 的 optional additive metadata，至少有 `required` 與 `stage`；既有 `chatText`、CLI protocol、PreviewGate 與 post-G2 approved task 行為不可變。
- Wiki 在 verification 前 read-only；G3 使用 `promote`，最多更新五個 content pages，並同步 `index.md`、`log.md` 與 page seals。Extension 版本升至 0.2.2，既有 0.2.1 artifact 保留。

## 需求與驗收條件

## REQ-001: 所有 pre-G2 mutation 先完成 Plan Mode preflight

- Priority: must
- Acceptance: AC-001, AC-002
- Description: Router 必須在 `new`、`feature`、`refactor`、`bug`、`wiki bootstrap` 與回到 G1/G2 的 `revise` 執行任何 `start`、`bind`、`revise` 或 bootstrap Work Item mutation 前確認 Plan Mode host capability；不可見時提示切換並停止。

## REQ-002: Plan Mode 成功後延續既有 lifecycle

- Priority: must
- Acceptance: AC-002
- Description: host capability 可見後，Router 應沿用既有 G1 Wiki context、requirements、G1 approval 與後續 G2 流程；重新送出不得因 preflight 重複建立或修改工作項目。

## REQ-003: compatibility fallback 必須由使用者明確選擇

- Priority: must
- Acceptance: AC-003
- Description: host capability 不可見且使用者明確選擇 compatibility 時，才允許逐題、結構化 numbered fallback；fallback 仍需一題一問、推薦選項在前、提供 host Other，且不因無效或未回答而猜測。

## REQ-004: 以 additive metadata 表達導流需求

- Priority: must
- Acceptance: AC-004, AC-005
- Description: `PromptBundle` 與 `SnapshotGuidance` 可選地攜帶 `PlanModeGuidance`，至少包含 `required` 與 `stage`，並能按 command/phase 表達 initial、G1、G2 或非阻擋狀態。

## REQ-005: Control Center 顯示可操作的 Plan Mode handoff

- Priority: must
- Acceptance: AC-006, AC-007
- Description: 無 active work 或 current work 位於 pre-G2 時，總覽顯示 Plan Mode 下一步；mutation preview 與複製結果顯示「先切換 Plan Mode，再貼到 Codex Chat」的 handoff，且 copy action 仍可用。

## REQ-006: 治理與文件描述一致

- Priority: must
- Acceptance: AC-008
- Description: Router/contract、root `AGENTS.md`、使用手冊、Control Center README、bootstrap `AGENTS.md`、Wiki 與 accepted baseline 必須一致描述初始 preflight、明確 compatibility fallback 與 Extension 不切換 host mode。

## REQ-007: Extension release 與既有 artifact 相容

- Priority: must
- Acceptance: AC-008, AC-009
- Description: Extension 升至 0.2.2 並產生可驗證 VSIX；既有 0.2.1 artifact 保留，所有既有 configured command、chatText 與 package smoke contract 維持通過。

## NFR-001: Host 與 machine protocol 邊界

- Priority: must
- Acceptance: AC-003, AC-004, AC-009
- Description: 實作不得新增 fake host adapter、mode command、question state、CLI/schema/ledger 欄位或要求 Extension 取得 `request_user_input`；machine keys/protocol 維持 English 且 metadata optional。

## NFR-002: 可逆性、可及性與安全性

- Priority: must
- Acceptance: AC-006, AC-007, AC-009
- Description: handoff 必須可見、可讀、可複製且不阻止使用者複製 prompt；stale preview、multiple active work、post-G2 approved task 與一般 mutation safety 不得退化。

## AC-001: 普通模式初始 mutation 會停止在 mutation boundary

- Requirement: REQ-001
- Scenario: Given repository 已初始化且目前沒有 active Work Item，When 使用者在普通模式提出 `new`、`feature`、`refactor`、`bug` 或 `wiki bootstrap`，Then Router 先提示切換 Plan Mode，且不執行 `start`、`bind`、`revise`、bootstrap，不新增 Work Item 或 ledger mutation。

## AC-002: 切換後可無重複地進入 G1

- Requirement: REQ-001, REQ-002
- Scenario: Given AC-001 已停止，When 使用者切換至 Plan Mode 並重新提交相同意圖，Then Router 完成既有 start/bind/context 流程並進入 G1；若已有工作項目則只延續該工作，不重複建立，且 G1 Wiki context 仍完整記錄。

## AC-003: compatibility fallback 需明確選擇且不可猜測

- Requirement: REQ-003, NFR-001
- Scenario: Given host 不提供 `request_user_input`，When Router 告知切換 Plan Mode 並提供 compatibility 選擇，Then 只有使用者明確選擇 compatibility 才逐題顯示 numbered question；若取消、timeout、malformed 或 ambiguous，Then 停止且不建立/修改 Work Item、不批准 gate。

## AC-004: metadata 最小化且 chatText 完全相容

- Requirement: REQ-004, NFR-001
- Scenario: Given 各 configured command 與 snapshot phase，When Composer/Presentation 產生結果，Then `PlanModeGuidance` 依 intent/phase 正確標示 `required`/`stage`，既有 `chatText` byte-for-byte 不變；post-G2 approved task 不被錯誤標成 pre-G2 required。

## AC-005: metadata 對非 mutation 狀態不製造 blocker

- Requirement: REQ-004
- Scenario: Given read-only snapshot 或已完成 G2 approval 的 approved task，When產生 `PromptBundle` 或 `SnapshotGuidance`，Then metadata 可省略或標示非阻擋階段，且不改變既有 command、warnings、PreviewGate 與 task guidance。

## AC-006: 總覽對 no-active 與 pre-G2 提供下一步

- Requirement: REQ-005, NFR-002
- Scenario: Given no active work 或 selected current work 位於 pre-G2，When 使用者開啟 Control Center overview，Then 看見明確 Plan Mode 下一步與 handoff；Given work 已 G2 approved，Then overview 不顯示錯誤的 pre-G2 blocker，既有 task guidance 維持。

## AC-007: preview/copy 都保留 handoff 與 copy

- Requirement: REQ-005, NFR-002
- Scenario: Given mutation prompt preview 或 stale/multiple-work safety state，When 使用者查看或複製 prompt，Then 顯示「先切換 Plan Mode，再貼到 Codex Chat」handoff、原始 `$devweave ...` chatText 與既有 warnings，且 copy action 成功可用。

## AC-008: 文件、Wiki、baseline 與 release 一致

- Requirement: REQ-006, REQ-007
- Scenario: Given implementation and verification complete，When repository contract、documentation/Wiki/baseline checks 與 package verifier 執行，Then 所有文件宣稱一致、promote 不超過五個 content pages 並同步 index/log，0.2.2 VSIX 可驗證且 0.2.1 artifact 仍存在。

## AC-009: 全套既有與新增驗證通過

- Requirement: REQ-007, NFR-001, NFR-002
- Scenario: Given final diff，When 執行 Python full suite、Extension unit tests、typecheck、package、smoke test 與 `git diff --check`，Then commands exit successfully，且 evidence 對應本需求的所有 required contracts。

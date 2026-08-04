# 需求與驗收條件：修正 G1/G2 問答、Wiki 初始化與 Extension bundle 相容性

<!-- DEVWEAVE:artifact=requirements version=1 work=20260804-183511-feature-g1-g2-wiki-extension-bundle -->
## 假設與限制

- 原生 question facility 的可用性由 Codex host 決定；repository 不依賴未記錄的統一 API。
- 原生問答只涵蓋 G1/G2 material decisions；Gate 仍須透過現有 explicit `$devweave approve`。
- 使用者已選擇：native-first＋structured fallback、Wiki reserved starter compatibility、`new`/`feature` 保留但只提示。
- Extension 的 semantic adoption 只適用於明確列出的 governance/Wiki starter contract；其他 bundle controls 維持 exact。
- Wiki 在 verification 前 read-only；Wiki promotion 受既有最多五個 content targets、coupled index/log、source provenance 與 seal 規則限制。

## 需求與驗收條件

## REQ-001: G1/G2 優先使用結構化原生問答

- Priority: must
- Acceptance: AC-001
- Description: G1/G2 對 material requirements/design decision 必須一次只提出一題；host 提供原生 question facility 時，題目使用互斥選項、第一項為推薦、每項包含 trade-off 說明，並提供 host-native Other/freeform。

## REQ-002: 無原生能力時保持同等互動契約

- Priority: must
- Acceptance: AC-002
- Description: Codex CLI 或其他 host 沒有可用原生 question facility 時，router 必須輸出單題 structured fallback，保留相同選項順序、推薦標記、選項說明與明確自訂答案入口；不得退回沒有選項邊界的自由問句。

## REQ-003: 問答結果回流既有 artifacts 且不新增 lifecycle state

- Priority: must
- Acceptance: AC-003
- Description: G1 回答寫入 `brief.md`/`requirements.md`，G2 回答寫入 `design.md`/`plan.md`；不得建立 pending-question state、question CLI、JSON schema 或第二套 ledger，且 `$devweave approve` Gate contract 不變。

## REQ-004: Wiki 初始化採用 reserved starter compatibility

- Priority: must
- Acceptance: AC-004
- Description: `wiki/` 不存在、為空或只有非保留自訂內容時，初始化應建立缺少的 starter；既有非保留內容不得覆寫。只有 `index.md`、`overview.md`、`log.md` 與必要 starter directories 的錯誤 filesystem type、frontmatter 或 reserved path 才能回報 `knowledge_conflict`。

## REQ-005: Wiki conflict 初始化不得留下 partial control state

- Priority: must
- Acceptance: AC-005
- Description: `init_project()` 必須在任何 `.devweave` project、baseline、cache、work-item 控制檔建立前完成 Wiki preflight；保留 path conflict 時維持使用者 Wiki bytes，且不建立本次 init 的 partial DevWeave control bundle。

## REQ-006: Wiki bootstrap 與一般工作流程邊界保持清楚

- Priority: must
- Acceptance: AC-006
- Description: `knowledge bootstrap` 仍是 repository-wide assessment、create/resume/already-complete 的一般 feature-profile lifecycle；缺少 bootstrap 只能提出 advisory，不能阻擋一般 `new`/`feature`。`new` 適合第一個 vertical slice、`feature` 適合既有產品，但選錯只提示不拒絕。

## REQ-007: Extension 可採用合法演進內容

- Priority: must
- Acceptance: AC-007
- Description: bootstrap manifest 對 `.devweave/project.json`、三份 baseline 與三份 Wiki starter 宣告 destination-specific compatible policy；符合現行 project/schema/frontmatter/baseline identity 的既有不同 bytes 必須列為 adopted，不得列 conflict，也不得被覆寫。

## REQ-008: Extension 對真正不相容內容維持 fail-closed

- Priority: must
- Acceptance: AC-008
- Description: malformed/managed:false project、錯誤 baseline headings、錯誤 Wiki type、manifest integrity/path/type/symlink conflict 與 exact control file byte mismatch 仍須列 conflict/error；只建立 missing paths，寫入失敗只 rollback 本輪建立內容。

## NFR-001: Compatibility validator deterministic and bounded

- Priority: must
- Acceptance: AC-009
- Description: Installer 與 snapshot 使用同一套 deterministic、dependency-free、destination-specific validator；manifest 舊欄位缺少 compatibility policy 時向後相容地視為 exact，未知 policy/compatibility kind 在寫入前拒絕。

## NFR-002: Existing Extension safety boundaries remain unchanged

- Priority: must
- Acceptance: AC-010
- Description: Extension 仍只透過 VS Code filesystem adapter 執行使用者確認後的 allowlisted bootstrap write，不執行 engine、CLI、shell、Git、network、Codex Agent 或 live Wiki mutation；所有 high-risk verification commands 必須通過。

## AC-001: Native decision presentation

- Requirement: REQ-001
- Scenario: Given G1/G2 有 material decision 且 host 暴露原生 question facility, When router 提問, Then 使用者看到單題、互斥選項、推薦第一項、trade-off 說明與 Other/freeform，回答後才進入下一題。

## AC-002: Structured fallback presentation

- Requirement: REQ-002
- Scenario: Given host 沒有原生 question facility, When router 需要 material decision, Then 顯示單題 structured fallback，使用者可選編號或輸入自訂答案，且下一題不會在答案前出現。

## AC-003: Artifact and Gate continuity

- Requirement: REQ-003
- Scenario: Given 使用者完成 G1/G2 decision, When artifacts 被更新並執行 validate, Then decision trace 出現在既有 phase artifacts，沒有 pending-question ledger，且 Gate 仍需明確 `$devweave approve`。

## AC-004: Compatible Wiki initialization

- Requirement: REQ-004
- Scenario: Given `wiki/` 只有 `notes.md` 或缺少 starter files, When 執行 init, Then starter 缺檔被建立、`notes.md` bytes 不變，且不因缺少 index 將整個 Wiki 判為 conflict。

## AC-005: Wiki conflict preflight

- Requirement: REQ-005
- Scenario: Given `wiki/index.md`/`overview.md`/`log.md` 的 reserved path type 或 frontmatter 不相容, When 執行 init, Then 回報 `knowledge_conflict`、保留所有既有 Wiki bytes，且 `.devweave/project.json`、baseline、cache、work-item 不因本次呼叫而被建立。

## AC-006: Bootstrap lifecycle and profile guidance

- Requirement: REQ-006
- Scenario: Given control bundle 已初始化但 Wiki 尚未達 bootstrap readiness, When 執行 `knowledge bootstrap` 或建立一般 work, Then bootstrap 回傳 create/resume/advisory 行為，普通 `new`/`feature` 不被硬阻擋，且 guidance 會提示適合的 profile。

## AC-007: Evolved bundle adoption

- Requirement: REQ-007
- Scenario: Given project/baseline/Wiki starter 內容符合 semantic contract 但 bytes 與最小 bundle template 不同, When Extension 執行 inspect/initialize, Then paths 出現在 adopted、snapshot 不列 conflict、既有 bytes 完全不變，且 missing paths 才會被建立。

## AC-008: Invalid bundle/workspace remains blocked

- Requirement: REQ-008
- Scenario: Given compatible policy target 為 malformed/invalid 或 exact control file bytes 不符, When Extension 執行 inspect/install, Then report 保留 conflict/error、complete 為 false、不得覆寫既有檔案，並維持 traversal/symlink/integrity/rollback 防護。

## AC-009: Shared deterministic contract

- Requirement: NFR-001
- Scenario: Given installer 與 snapshot 讀取同一 manifest/workspace fixture, When 分別執行 inspect, Then compatible/conflict 結果一致；舊 manifest 無 policy 欄位仍按 exact 行為處理，未知欄位值在寫入前 fail。

## AC-010: Full high-risk verification

- Requirement: NFR-002
- Scenario: Given implementation、tests、package 與 G3 artifacts 完成, When 執行 high verification profile, Then `npm run package`、`npm run test:smoke`、`npm test`、`npm run typecheck` 與 root Python unittest 全數 current passing，並保留 Extension no-process/no-network contract。

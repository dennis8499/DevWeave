# 需求與驗收條件：整合 Codebase LLM Wiki 閉環

<!-- DEVWEAVE:artifact=requirements version=1 work=20260803-161041-feature-codebase-llm-wiki -->
## 假設與限制

- Repository 維持 schema version 1、Python 3.11+、Git 與 Python standard library runtime；所有新增 state 採 additive compatibility。
- Live knowledge 固定在 configured root `wiki/`；`.agents/skills/devweave/assets/wiki/` 是 engine-owned canonical inputs，不是 live Wiki。
- Bootstrap 以整個 repository 為範圍、自動選擇 3–5 個高價值內容頁；不提供 path scope。
- G1 每次最多讀五個內容頁，`wiki/index.md` 不計入；source 與已核准 artifacts 優先於 Wiki。
- 新公開 intent 只有 `$devweave wiki bootstrap`；其餘 query/review/scaffold 是既有 single router 下的 machine workflow。
- Extension 三個入口沿用 preview/copy seam，不直接執行 mutation。
- Token 降低只作為質性成果，不蒐集精確 metric。

## 需求與驗收條件

## REQ-001: 冪等 Wiki Bootstrap 路由

- Priority: must
- Acceptance: AC-001
- Description: Public `$devweave wiki bootstrap` 必須路由至無 scope 參數的 machine `knowledge bootstrap`；核心 Wiki 已完成時回傳 `already_complete`，有 active bootstrap Work Item 時回傳 `resume`，否則建立 `kind: feature` 且 `knowledge_profile: bootstrap` 的 Work Item 並回傳 `created`。

## REQ-002: Bootstrap Gate 與完成條件

- Priority: must
- Acceptance: AC-002
- Description: Bootstrap 必須沿用 G1/G2/G3、保持 G2 與 implementation Wiki 唯讀、禁止產品 source diff，並在 G3 以 3–5 個 planned content targets 建立或修復 active/sourced/current/sealed 的 overview、至少一個 architecture 與至少一個 module，且同步 index 與 promote log；未完成 bootstrap 只提供非阻擋建議。

## REQ-003: 可重現的 Wiki-first Context

- Priority: must
- Acceptance: AC-003
- Description: `knowledge context` 必須固定以 index 開頭並限制最多五個唯一內容頁，且保存每個實際頁面的 path、status、content hash 與 source fingerprint；任何 context page 或其 source currentness 改變時，先前 G1 或相依 gate 必須 stale。

## REQ-004: Gap 後最小 Raw-source Fallback

- Priority: must
- Acceptance: AC-004
- Description: G1 instructions 與 phase policy 必須要求 missing、placeholder、stale、invalid、insufficient 或 contradictory Wiki knowledge 先記錄 gap，再讀最小必要 raw-source slice，並在輸出中區分 Wiki 事實、source-backed 事實、推論與 gap。

## REQ-005: 每個新式 Work Item 的 Knowledge Review

- Priority: must
- Acceptance: AC-005
- Description: Machine CLI 必須提供 `knowledge review --disposition promote|no-update --rationale`，把 disposition、rationale、affected pages、uncovered paths、change fingerprint 與 recorded time 存入 state；新 Work Item 在 G3 前必須有 current review，source diff 改變時 review 與 plan 必須失效。

## REQ-006: Promote 與 No-update 約束

- Priority: must
- Acceptance: AC-006
- Description: `promote` 必須先於非空 knowledge plan；`no-update` 只允許非-bootstrap、沒有 affected page、沒有 Wiki diff 且 rationale 非空的 Work Item，並不得把 no-update 寫入 Wiki log 或偽裝成 waiver。

## REQ-007: Coverage 與五頁 Knowledge Plan

- Priority: must
- Acceptance: AC-007
- Description: `knowledge status` 必須以現有 source overlap 語意回報 affected pages、covered changed paths、uncovered changed paths、bootstrap recommendation/reasons 與 review currentness；每個 plan 的 content upsert/delete 合計不得超過五個，index/log 不計入且仍自動 coupling。

## REQ-008: 九種 Canonical Template Scaffold

- Priority: must
- Acceptance: AC-008
- Description: `knowledge scaffold` 必須支援 overview、architecture、module、entity、pattern、dependency、decision、guide、synthesis，接受 work/page/type/title/repeatable source；dependency 強制 package-name/version，decision 強制合法 date 與 proposed/accepted/deprecated/superseded status，且不得接受任意未知 metadata。

## REQ-009: Scaffold、Seal 與 Guard 邊界

- Priority: must
- Acceptance: AC-009
- Description: Scaffold 只可在 current G2 後的 verification/acceptance、current promote review、planned new upsert、合法 type directory/source 且 target 不存在時原子建立 placeholder；seal 必須拒絕 placeholder、未替換 token、critical lint 或 invalid sources，guard 只允許 planned targets 與 coupled index/log。

## REQ-010: G3 持續知識累積

- Priority: must
- Acceptance: AC-010
- Description: G3 必須要求所有既有 affected pages refresh/seal 或 delete；對未覆蓋但具 durable value 的 product change，promote plan 可用一個或多個新頁涵蓋變更範圍，不要求逐檔建頁，並維持 append-only、work-attributed promote log 與同步 index。

## REQ-011: VS Code Extension 三個安全入口

- Priority: must
- Acceptance: AC-011
- Description: Extension 必須在 public command 下拉、Knowledge 面板情境按鈕與 Command Palette 提供相同 `wikiBootstrap` intent，三者都只預覽/複製精確的 `$devweave wiki bootstrap`，並在 snapshot/projected Knowledge 顯示 bootstrap、coverage 與 review 狀態。

## REQ-012: Single-router 文件與公共契約

- Priority: must
- Acceptance: AC-012
- Description: SKILL、requirements/verification references、contracts、root AGENTS、README、繁體中文手冊與 Extension README 必須一致描述 Bootstrap→Query→Review→Promotion 閉環；不得新增第二個 Wiki skill、平行 work lifecycle 或 Extension direct-execution seam。

## NFR-001: Schema v1 與 Legacy 相容

- Priority: must
- Acceptance: AC-013
- Description: 新 state 與 JSON payload 欄位必須 additive；只有新建立 Work Item 預設 `knowledge_review_required: true`，缺少該欄位的既有 Work Item 不追溯阻擋，既有 public verbs、gate names、exit code 與 JSON envelope 保持相容。

## NFR-002: 決定性、安全與零新增 Runtime 依賴

- Priority: must
- Acceptance: AC-014
- Description: Bootstrap detection、coverage、context records、template rendering 與 seal 必須使用 Python standard library、normalized repo-relative paths、deterministic ordering 與原子寫入；path traversal、Wiki/.devweave/.git source、symlink escape、existing target 或 malformed template 必須 fail closed。

## NFR-003: 有界探索與狀態輸出

- Priority: must
- Acceptance: AC-015
- Description: Query 不得加入向量/全文檢索或 Token instrumentation；context 固定 index 加最多五頁，status 的 page/path/finding collections 維持既有 bounded projection，Extension 不讀取 raw source 或自行重建 authoritative fingerprint。

## NFR-004: 回歸與可驗證性

- Priority: must
- Acceptance: AC-016
- Description: 完整 Python suite、CLI/guard/repository contract、Extension unit/typecheck/package/smoke 與 skill validation 必須通過；高風險 G3 必須具有 current acceptance、regression 與 independent review evidence。

## AC-001: Bootstrap create/resume/idempotence

- Requirement: REQ-001
- Scenario: Given complete、partial-with-active-bootstrap 與未 bootstrap 的 managed repositories，When 執行 `knowledge bootstrap`，Then 分別輸出 `already_complete`、`resume`、`created`，只在第三種情況新增 feature-profile Work Item，且重跑不重複建立。

## AC-002: Bootstrap lifecycle

- Requirement: REQ-002
- Scenario: Given bootstrap-profile Work Item，When 驗證各 gate，Then G2 前 Wiki write、產品 source diff、少於三或多於五個 target、缺 overview/architecture/module、未 sourced/current/sealed 或未同步 index/log 都會失敗；合法完整流程通過並移除 recommendation。

## AC-003: Context snapshot 與 stale

- Requirement: REQ-003
- Scenario: Given 合法 index-first context，When 記錄一至五個內容頁，Then state 保存 deterministic records；When 任一頁內容、status 或 source fingerprint 改變，Then G1 fingerprint/currentness 改變且 validate 回報 stale。

## AC-004: Query fallback discipline

- Requirement: REQ-004
- Scenario: Given fresh 與 nonfresh Wiki pages，When G1 形成探索上下文，Then fresh facts 不要求 raw source，nonfresh/insufficient/contradictory facts 未記錄 gap 時 validation/instructions 阻止 fallback，合法 gap 則允許最小 source follow-up 並保留知識類別。

## AC-005: Review state 與 invalidation

- Requirement: REQ-005
- Scenario: Given 新式 normal Work Item，When 進入 G3，Then缺少 review 或 stale change fingerprint 會阻擋；合法 promote/no-update 保存完整 state/event，產品 diff 再變更後 review 與 plan 不再 current。

## AC-006: Review disposition rules

- Requirement: REQ-006
- Scenario: Given bootstrap、affected-page、Wiki-diff、empty-rationale 與無 durable knowledge fixtures，When 記錄 no-update/promote，Then所有非法組合 fail closed；合法 no-update 不建立 plan、不改 index/log 且可通過 knowledge duty。

## AC-007: Coverage 與 plan cap

- Requirement: REQ-007
- Scenario: Given changed product paths 與 active page sources，When 執行 status/plan，Then overlap paths 分入 covered、其餘分入 uncovered、affected pages 維持既有語意；第六個 content target 被拒絕而 index/log coupling 不計入上限。

## AC-008: Scaffold type contract

- Requirement: REQ-008
- Scenario: Given九種合法 type 與缺少/錯誤型別欄位、未知 type/metadata fixtures，When 執行 scaffold，Then合法頁由對應 canonical template 建立且 frontmatter 正規化，非法輸入產生穩定 JSON diagnostic。

## AC-009: Scaffold 與 seal safety

- Requirement: REQ-009
- Scenario: Given G2 前、implementation、no-update、undeclared、existing、wrong-directory、bad-source、placeholder/token 與合法 verification fixtures，When scaffold/edit/seal，Then只有合法 planned new upsert 可建立並在完成 active content 後 seal，其餘不留下半寫檔案且 guard/engine 一致拒絕。

## AC-010: G3 promotion

- Requirement: REQ-010
- Scenario: Given affected existing page 與 durable uncovered change，When 驗證 G3，Then未 refresh/delete affected page 或 promote plan 未涵蓋 durable knowledge 會失敗；合法 upsert/delete、index、append-only log、seal 與 source provenance 通過。

## AC-011: Extension parity 與安全

- Requirement: REQ-011
- Scenario: Given dropdown、情境按鈕與 Command Palette，When 啟動 Wiki Bootstrap，Then三者經同一 composer 產生精確 mutation prompt 與警告；protocol 對 extra fields fail closed，且 security tests 證明沒有 direct process/network/repository write。

## AC-012: 文件與單一路由

- Requirement: REQ-012
- Scenario: Given 完成後 repository，When 執行 contract/skill tests 並比對所有公開文件，Then只有單一 devweave router、命令與 gate 用語一致、Bootstrap 與 per-Work-Item review 可由文件完整操作。

## AC-013: Legacy compatibility

- Requirement: NFR-001
- Scenario: Given缺少新欄位的 schema-v1 active/closed fixtures 與新 Work Item，When load/status/validate，Then舊資料保持可讀且不新增 review blocker，新資料啟用完整 contract，既有 public command payload 不破壞。

## AC-014: Deterministic fail-closed behavior

- Requirement: NFR-002
- Scenario: Given Windows/POSIX 等價 paths、symlink/path traversal、existing content、invalid source 與 template conflict，When bootstrap/status/scaffold/seal，Then合法結果排序與 hash 穩定，非法情況無部分寫入且不需新增 dependency。

## AC-015: Bounded query/projection

- Requirement: NFR-003
- Scenario: Given大型 Wiki 與大量 changed paths，When執行 context/status/Extension snapshot，Then context 最多 index 加五頁、payload collections 有界、Extension 只投影 Wiki/state，且 repository 不出現 vector/FTS/token measurement runtime。

## AC-016: 完整高風險回歸

- Requirement: NFR-004
- Scenario: Given實作完成的 source，When執行 configured high-risk commands、targeted lifecycle/security tests、skill quick validation 與 independent review，Then全部 current passing 並可追溯到需求與 implementation tasks。

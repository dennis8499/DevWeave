# 需求與驗收條件：整合 Wiki-first 探索與知識提升

<!-- DEVWEAVE:artifact=requirements version=1 work=20260802-200224-feature-wiki-first -->

## 假設與限制

- 整合來源固定為 `code-base-llm-wiki` main commit `5391fd0fca2eff9ebb9c8d242c4d3cf4bedc11e3`，且使用者已確認程式碼與模板重用權利。
- 只支援 Codex；對外仍只有單一 `$devweave` router 與既有 chat verbs。
- 目標知識位置固定為 repository 根目錄 `wiki/`；framework repository 本次只交付能力與 assets，不自我初始化 Wiki。
- Machine keys、CLI、state 與程式碼使用英文；人類可讀 Wiki 與 gate artifact 依 project locale，預設繁體中文。
- Python 3.11+、Git 與標準函式庫仍是唯一 runtime 需求。

## 需求與驗收條件

## REQ-001: 非破壞性 Wiki 初始化

- Priority: must
- Acceptance: AC-001
- Description: `init` 與建立新 work item 前必須確保根目錄 `wiki/` 具有 index、overview placeholder、append-only log 與 typed directories；重跑必須冪等，既有相容內容不得覆寫，不相容內容必須回報 conflict。

## REQ-002: G1 Wiki-first 探索脈絡

- Priority: must
- Acceptance: AC-002
- Description: 新 work item 的 G1 必須先記錄 `wiki/index.md`，可再記錄最多五個相關頁面；stale、placeholder、缺失或矛盾資訊必須形成 gap 並回溯 raw sources，而不是當成已驗證事實。

## REQ-003: G3 知識提升與受影響頁面刷新

- Priority: must
- Acceptance: AC-003
- Description: Wiki 在 G1/G2 維持唯讀；verification/acceptance 才能 plan、修改與 seal。若本 work item 的 source diff 命中既有頁面 sources，該頁必須刷新為 current active page 或明確刪除；無受影響頁面時不強迫填寫無更新理由。

## REQ-004: New profile 的 overview 提升

- Priority: must
- Acceptance: AC-004
- Description: `new` work item 在 G3 前必須將 `wiki/overview.md` 從 placeholder 提升為具有實際 sources、current fingerprint 與 work provenance 的 active page。

## REQ-005: 可追溯 Wiki 頁面模型

- Priority: must
- Acceptance: AC-005
- Description: 系統必須支援 overview、architecture、module、entity、pattern、decision、dependency、guide、synthesis、index 與 log，並驗證共同 frontmatter、status、repo-relative sources、`source_fingerprint` 與 `verified_by`。

## REQ-006: 精確來源內容指紋

- Priority: must
- Acceptance: AC-006
- Description: sources fingerprint 必須對目前 working tree 計算；檔案使用內容或 symlink target，目錄使用排序後的 Git tracked 與 non-ignored untracked files，且能偵測 dirty、rename、delete 與 directory 內容變更。

## REQ-007: Wiki 健康度、索引與日誌契約

- Priority: must
- Acceptance: AC-007
- Description: deterministic lint 必須檢查 frontmatter、來源存在與指紋、唯一 wikilink、broken link、orphan 與 index 完整性；內容變更必須同步 index 並只在 log body 追加包含 work ID 的 promote entry。

## REQ-008: Engine CLI 與 work state

- Priority: must
- Acceptance: AC-008
- Description: engine 必須提供 machine-only `knowledge status/context/plan/seal` JSON commands，並在新 work state 保存 `base_knowledge`、`knowledge_context` 與 `knowledge_updates`；context 與 plan 採完整取代語意。

## REQ-009: Fingerprint 與 gate 整合

- Priority: must
- Acceptance: AC-009
- Description: `wiki/` 必須排除於 product source fingerprint 並納入獨立 knowledge snapshot 與 G3 acceptance fingerprint；Wiki promotion 不得使 current source-bound evidence stale，但 G3 核准後的 Wiki 變更必須使 G3 stale。

## REQ-010: Guard 最小授權

- Priority: must
- Acceptance: AC-010
- Description: 合併後的單一 DevWeave PreToolUse guard 必須在 G2 前拒絕 Wiki edits，並只在 verification/acceptance 允許 knowledge plan 已宣告的 upsert/delete 及自動 coupling 的 index/log 路徑。

## REQ-011: Schema v1 向後相容

- Priority: must
- Acceptance: AC-011
- Description: 新欄位必須為 additive；缺少 knowledge config 的既有 project 在下一次 `init/start` 補齊，缺少 knowledge state 的舊 active work item 不承受追溯 blocker，相容舊 Wiki 頁面以 unsealed warning 漸進採用。

## REQ-012: 單一路由與文件一致性

- Priority: must
- Acceptance: AC-012
- Description: repository 仍只能包含 `devweave` skill；SKILL、phase references、contracts、assets、openai metadata、AGENTS 與 README 必須一致描述 Wiki-first lifecycle，且不新增公開命令。

## NFR-001: 決定性與零第三方依賴

- Priority: must
- Acceptance: AC-013
- Description: knowledge engine、parser、hashing 與 lint 只能使用 Python 標準函式庫，在 Windows、macOS 與 Linux 對同一內容產生一致的 normalized result。

## NFR-002: 安全與資料完整性

- Priority: must
- Acceptance: AC-014
- Description: 所有 knowledge paths 必須保持在 configured Wiki root；不得直接編輯 machine ledgers；page seal、state/event 更新與 bootstrap 必須採原子或可復原寫入，衝突時 fail closed。

## NFR-003: 回歸與可驗證性

- Priority: must
- Acceptance: AC-015
- Description: 既有 48 項 DevWeave tests 必須保持通過，新增 bootstrap、fingerprint、lint、gate、guard、legacy 與完整 feature lifecycle 測試，並通過 skill quick validation。

## AC-001: Bootstrap 與 adoption

- Requirement: REQ-001
- Scenario: Given 空白、已初始化及具有相容或衝突 Wiki 的暫存 repositories，When 執行 `init` 或 `start`，Then 只在安全時建立缺失骨架、重跑無差異、保留既有頁面，並對衝突輸出穩定 JSON diagnostic。

## AC-002: G1 context

- Requirement: REQ-002
- Scenario: Given 新式 work state，When 驗證 G1，Then 未記錄 index、記錄超過五個相關頁面或未揭露非 fresh page gap 會失敗；合法 context 會進入 scope fingerprint 與 status/instructions。

## AC-003: Affected page promotion

- Requirement: REQ-003
- Scenario: Given G2 後的 source change 命中既有 Wiki page sources，When 驗證 G3，Then 未 plan、未刷新或未刪除該頁會失敗；合法 seal/delete 與 coupling 完成後通過，無命中時不要求 knowledge rationale。

## AC-004: New overview

- Requirement: REQ-004
- Scenario: Given `new` profile，When 驗證 G3，Then placeholder、空 sources、非 current fingerprint 或缺少 current work provenance 的 overview 會失敗，完整 active overview 才通過。

## AC-005: Page schema

- Requirement: REQ-005
- Scenario: Given 每種合法 page type 與錯誤欄位、status、path 或 source 樣例，When 執行 knowledge validation，Then 合法頁面通過且每個不合法樣例產生可定位的 diagnostic。

## AC-006: Source fingerprint

- Requirement: REQ-006
- Scenario: Given tracked、untracked non-ignored、dirty、symlink、directory、rename 與 delete fixtures，When 計算與重算 fingerprint，Then 未變內容穩定且每個實質 source 變化都改變 fingerprint。

## AC-007: Lint、index 與 append-only log

- Requirement: REQ-007
- Scenario: Given broken links、重複 stem、orphan、index 遺漏、source mismatch 與 rewritten log fixtures，When 執行 lint/G3 validation，Then Critical 阻擋、Warning 僅回報，且合法 index 與追加 log 通過。

## AC-008: Machine CLI contract

- Requirement: REQ-008
- Scenario: Given knowledge commands 的合法與非法 arguments，When 從 CLI 執行，Then stdout 永遠是一份 UTF-8 JSON、exit code 沿用 DevWeave 契約，且 state/event 只能經 engine 更新。

## AC-009: 獨立 knowledge fingerprint

- Requirement: REQ-009
- Scenario: Given current passing source-bound evidence，When 只修改已授權 Wiki，Then source fingerprint 與 evidence 保持 current；When G3 已核准後 Wiki 再變更，Then acceptance gate 變 stale。

## AC-010: Guard boundary

- Requirement: REQ-010
- Scenario: Given unbound、G2 前、implementation、verification 與 acceptance sessions，When 嘗試修改 planned、coupled、undeclared Wiki path 或 raw source，Then guard 只允許符合 phase、binding、scope 與 plan 的最小集合。

## AC-011: Legacy compatibility

- Requirement: REQ-011
- Scenario: Given schema v1 project/state 與缺少新 frontmatter 的相容 Wiki，When 載入、status、start 與 G3 validation，Then 舊 active work 不新增 blocker、新 work 啟用完整 contract、舊頁顯示 unsealed 且不被覆寫。

## AC-012: Router 與文件契約

- Requirement: REQ-012
- Scenario: Given 完成後 repository，When 執行 repository contract tests 與 skill validation，Then 只有 `devweave` skill、metadata 與 references 一致、公開 chat verbs 未增加。

## AC-013: 跨平台決定性

- Requirement: NFR-001
- Scenario: Given 等價 Windows 與 POSIX path fixtures，When 執行 parser、normalization、fingerprint 與 lint，Then 結果不依 shell 解譯且不需第三方套件。

## AC-014: 安全失敗與原子性

- Requirement: NFR-002
- Scenario: Given path traversal、Wiki root 外目標、部分失敗與既有衝突，When 執行 bootstrap/plan/seal，Then 操作 fail closed、不留下半寫 state/temp files，既有使用者內容保持可復原。

## AC-015: 完整回歸

- Requirement: NFR-003
- Scenario: Given 實作後程式，When 執行完整 unit suite、skill quick validation 與暫存 fixture E2E，Then 所有 checks 通過並產生可追溯 acceptance/regression/review evidence。

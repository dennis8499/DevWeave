# 需求與驗收條件：優化專案 Skills 可預測性（排除 writing-great-skills）

<!-- DEVWEAVE:artifact=requirements version=1 work=20260805-081842-feature-skills-writing-great-skills -->

## 假設與限制

- 本次優化的內容依使用者已確認的「完整 Skill 套件、保守相容、只同步必要契約、可預測性優先」執行。
- 目標 Skill 內容維持英文；DevWeave artifacts、Gate 摘要與使用者訊息維持繁體中文。
- `writing-great-skills` 是 maintenance-only exclusion；它的 bytes、hash 與內容不可被本工作修改。
- `skills-lock.json` 保存上游 provenance/hash；local optimization 不被視為 upstream release。
- `quick_validate.py` 以 UTF-8 模式執行；`grill-me` 的 `disable-model-invocation` 由 repository contract 驗證，因現有 validator 不接受此受支援欄位。

## 需求與驗收條件

## REQ-001: 六個目標 Skill 可被正確發現與使用
- Priority: must
- Acceptance: AC-001, AC-002
- Description: Repository 必須保留 `devweave`、`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling` 與 `tdd` 六個既有 Skill；每個目標 Skill 的 name、主要觸發分支、相對 references 與 invocation policy 必須清楚且可驗證。

## REQ-002: Skill instruction 必須提升可預測性
- Priority: must
- Acceptance: AC-002, AC-003
- Description: 每個目標 Skill 必須以 single source of truth、progressive disclosure、positive steering 與可檢查 completion criteria 組織；步驟、分支、參考入口與停止條件不得互相矛盾或依賴不存在的 Skill。

## REQ-003: DevWeave 與 companion phase 邊界必須保持相容
- Priority: must
- Acceptance: AC-003, AC-004
- Description: `devweave` 必須繼續是唯一 SDLC router；G1/G2/G3、Wiki-first、human approval、G2 前 tracked-write 限制、G3 Knowledge Review、high-risk review、CLI、JSON schema、Hook 與 Git/remote side-effect 邊界不得改變。

## REQ-004: Maintenance-only exclusion 與 upstream provenance 必須可追溯
- Priority: must
- Acceptance: AC-001, AC-004
- Description: `writing-great-skills` 必須完全排除於本次內容變更、五個 companion allowlist、skills-lock 與 Extension bootstrap；`skills-lock.json` 的五個 upstream source/path/hash 必須保持不變。

## NFR-001: 變更必須可逆且不擴張副作用
- Priority: must
- Acceptance: AC-004, AC-005
- Description: 變更只能落在宣告 scope；不得新增 router、state、schema、runtime dependency、Git 操作、production instrumentation 或未授權的 issue/PR/deployment 行為。

## NFR-002: 套件與驗證必須維持 deterministic contract
- Priority: must
- Acceptance: AC-001, AC-005
- Description: frontmatter、metadata、relative links、repository contract、Python unit tests、Extension tests/typecheck/package/smoke 與 `git diff --check` 必須通過；bootstrap bundle 必須仍包含精確六個受治理 Skill。

## AC-001: 精確 Skill 集合與排除內容保持正確
- Requirement: REQ-001, REQ-004, NFR-002
- Scenario: Given repository 同時存在六個目標 Skill 與 `writing-great-skills`，When 執行 repository contract 與 package verification，Then companion allowlist/Bootstrap 只包含 `devweave` 加五個 companions，`writing-great-skills` 不列入且其內容未變。

## AC-002: Metadata、觸發分支與參考連結完整
- Requirement: REQ-001, REQ-002
- Scenario: Given 六個目標 Skill 的 frontmatter、`agents/openai.yaml` 與 Markdown references，When 執行 UTF-8 skill validation 與 relative-link checks，Then name、description、invocation policy、UI metadata 與所有 repository-relative links 均有效，且 `grill-me` 保留 user-only invocation。

## AC-003: Phase 行為與完成條件不越權
- Requirement: REQ-002, REQ-003
- Scenario: Given feature、G1 grilling、G2 design、bug diagnosis 與 post-G2 TDD 情境，When 使用目標 Skill，Then agent 能依序選擇正確 phase 方法、一次處理一個 material decision、在 completion criterion 未滿足前停留，且不在 G2 前建立 tracked product/test change、不呼叫不存在的 Skill。

## AC-004: 公開介面與 provenance 不變
- Requirement: REQ-003, REQ-004, NFR-001
- Scenario: Given optimized Skill package，When 比對 public chat verbs、CLI/schema/Hook、`skills-lock.json`、scope diff 與 Extension bootstrap manifest，Then 不新增或改變公開介面，lock source/path/hash 不變，且沒有 `writing-great-skills` 或其他額外 Skill 被打包。

## AC-005: 完整驗證通過
- Requirement: NFR-001, NFR-002
- Scenario: Given G2-approved implementation，When 執行 repository unit tests、repository contract、Extension tests/typecheck/package/smoke、forward-test 與 `git diff --check`，Then 所有 required commands 以 current source fingerprint 通過，且 G3 acceptance 能覆蓋每個 AC/TASK。

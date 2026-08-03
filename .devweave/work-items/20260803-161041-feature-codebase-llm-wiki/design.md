# 系統設計：整合 Codebase LLM Wiki 閉環

<!-- DEVWEAVE:artifact=design version=1 work=20260803-161041-feature-codebase-llm-wiki -->

## 設計摘要

採用「純知識模型 + Work Item policy + 薄 adapter」三層設計，深化現有 module 而不新增平行 runtime：

- `knowledge_core` 是 source/file-local module，透過少量 interface 擁有 bootstrap assessment、context record、coverage、canonical template scaffold、lint preflight 與 seal；它不載入或寫入 Work Item ledger。
- `devweave_core` 是 lifecycle module，擁有 bootstrap profile、additive state、review/plan currentness、G1/G3 validation、WorkLock 與 event ledger；所有 phase/gate policy 只在此實作。
- `devweave.py` 僅把 machine arguments 轉交 core 並輸出單一 JSON envelope；SKILL/references 把 `$devweave wiki bootstrap` 翻譯成 machine flow。
- VS Code Extension 維持非權威 filesystem projection 與 prompt-only adapter；不呼叫 Python，也不自行實作 engine gate。

關鍵不變量：live Wiki 固定在 configured root、每頁 sources 最多五個、G1 index 加最多五頁、G2/implementation Wiki 唯讀、G3 content targets 最多五個、所有 mutation 經 WorkLock/原子寫入、source 與 accepted artifacts 優先於 Wiki、舊 schema-v1 state 不追溯阻擋。

## 選項比較

### Work Item 完成後的更新策略

- 選定：每個新式 Work Item 強制 `promote|no-update` review。這保留可追溯性，也避免沒有 durable knowledge 時製造低價值 Wiki diff。
- 拒絕：每個 Work Item 強制改頁。會造成 churn、空洞 log 與 agent 為通過 gate 而編造內容。
- 拒絕：背景 watcher/自動 ingest。它繞過 G2/G3、難以判斷語意價值，也會新增 runtime 與不可觀察 mutation。

### Bootstrap lifecycle

- 選定：`kind: feature` 加 `knowledge_profile: bootstrap`，沿用 G1/G2/G3 與既有 artifact grammar。
- 拒絕：新增第五種 WorkKind。會擴大 fixtures、profile、public start interface 與 gate state machine。
- 拒絕：在 `init` 直接掃描並產生完整 Wiki。`init` 應保持非破壞 skeleton，且缺少人工 requirements/design/acceptance。

### Template 使用方式

- 選定：engine-owned scaffold 解析 canonical template body，再由 validated frontmatter renderer 填入資料；頁面先是 placeholder，完成內容後才 active/seal。
- 拒絕：agent 手動複製 template。無法保證 type directory、metadata、no-overwrite 與 event provenance。
- 拒絕：為九種類型建立九組 CLI verbs。這是淺 interface，會重複相同 policy；單一 conditional scaffold interface 更有 leverage。

### Extension 入口

- 選定：dropdown、Knowledge CTA、Command Palette 都使用同一 `wikiBootstrap` intent 與 `DevWeavePromptComposer`，只預覽/複製 prompt。
- 拒絕：Extension 執行 Python CLI。會破壞既有 no-process/no-network security seam 與 engine authority。

## 介面與資料流

### Machine CLI

```text
knowledge bootstrap
knowledge review --work ID --disposition promote|no-update --rationale TEXT
knowledge scaffold --work ID --page PATH --type TYPE --title TITLE --source PATH...
                   [--package-name NAME --version VERSION]
                   [--decision-date YYYY-MM-DD --decision-status STATUS]
```

- `knowledge bootstrap` 不接受 `--work` 或 scope。輸出 `action: already_complete|resume|created`、`bootstrap` assessment 與 nullable work summary。若多個 active bootstrap profiles 存在則 fail closed，不自行挑選。
- `knowledge review` 只在 current G2 後的 verification/acceptance 接受；`promote` 清空舊 plan 後允許建立新 plan，`no-update` 在條件合法時本身完成 knowledge duty。
- `knowledge scaffold` 的 TYPE 限九種內容類型；通用欄位之外只暴露 dependency/decision 的必要欄位。CLI argparse 拒絕未知欄位，core 再做 conditional validation。
- 既有 `knowledge plan` 增加 content target 合計最多五個及 current promote review 前置條件；legacy Work Item 保留舊行為以相容未完成流程。

### Additive Work State

新 Work Item 由 `create_work()` 預設加入：

```json
{
  "knowledge_review_required": true,
  "knowledge_context": {
    "pages": ["wiki/index.md"],
    "records": [{
      "path": "wiki/index.md",
      "present": true,
      "status": "active",
      "content_hash": "<sha256-or-null>",
      "source_fingerprint": "none",
      "computed_source_fingerprint": "none"
    }],
    "gaps": [],
    "recorded_at": "<UTC>"
  },
  "knowledge_review": {
    "disposition": null,
    "rationale": "",
    "affected_pages": [],
    "covered_changed_paths": [],
    "uncovered_changed_paths": [],
    "change_fingerprint": null,
    "recorded_at": null,
    "invalidated_at": null
  }
}
```

- Bootstrap Work Item 額外具有 `knowledge_profile: "bootstrap"`；一般 Work Item 不寫此 optional key。
- `knowledge_updates` additive 加入 `change_fingerprint`，用來證明 plan 與 current promote review 綁定同一 product snapshot。
- 缺少 `knowledge_review_required` 的 state 視為 legacy；`records`、review 與 plan fingerprint 都不追溯要求。舊 engine 會忽略新 keys，因此不做 tracked state migration。

### Context Currentness

`knowledge_core.context_records(snapshot, pages)` 對每個 requested path 產生一筆 deterministic record，缺頁也以 `present: false`/null 欄位保留。G1 validation 比對 captured 與 live records；design/build-review 中任一頁內容、status、stored/computed source fingerprint 漂移會使 G1 stale。G2 核准後，產品 source 變更是 implementation 的預期輸入，不回捲 G1，而改由 affected-page、review 與 G3 接手；implementation 中未規劃的 Wiki page edit 仍由 guard/knowledge fingerprint 偵測，verification 的合法 Wiki edit則進入 acceptance fingerprint。

### Bootstrap Assessment 與流程

`knowledge_core.bootstrap_assessment()` 對 current snapshot/lint 回傳 `complete`、`recommended`、stable reason codes 與符合條件的核心頁。完成條件是：無 critical lint，且 active overview、至少一個 architecture、至少一個 module 都有非空 sources、非 `none` current fingerprint 與 `verified_by`。

`devweave_core.bootstrap_knowledge_work()` 在 project lock 下先 assessment，再檢查 active bootstrap profile，最後才建立固定標題「建立初始 Codebase Wiki」、standard-risk 的 feature Work Item，避免重複建立。Bootstrap 的 G3 validation 強制 current promote review、3–5 個 upserts、零 deletes、零 product diff、targets 含 overview/architecture/module，並在一般 promotion validation 後再次確認 assessment complete。

### Review、Coverage 與 Promotion

進入 verification 後，以 `changed_paths_since(base_source)` 作為 review snapshot：

1. `affected_pages` 使用 base Wiki sources，保留既有 refresh obligation。
2. `coverage_paths` 使用 current active/parse-valid pages；changed path 與任一 page source overlap 即 covered，否則 uncovered。
3. Review 保存目前 `git_snapshot.fingerprint`。後續 product fingerprint 改變時，review 標記 invalidated、knowledge plan 回復空集合並追加一次 invalidation event；Wiki-only/baseline-only edits不影響此 fingerprint。
4. `promote` 要求 1–5 個 content targets；G3 沿用 affected refresh/delete、index/log coupling、append-only promote heading、current seal 與 source provenance。
5. `no-update` 僅在 non-bootstrap、affected 為空、base→current Wiki diff 為空時接受；不建立 plan、不更新 index/log，也不是 waiver。

`knowledge status` 在既有 bounded collections 上增加 `bootstrap`、`covered_changed_paths`、`uncovered_changed_paths` 與含 `current` 的 review projection。`instructions` 依 phase 回傳 query read order、nonblocking bootstrap recommendation 或下一個 review/plan/scaffold/seal action。

### Scaffold 與 Seal

`knowledge_core.scaffold_page(repo, assets, ...)` 接受已由 workflow core 授權的資料：

- 先 normalize page/sources，檢查 type directory、1–5 sources、source existence、conditional fields、target absent 與 canonical asset 可解析。
- 使用 template body 與 renderer 建立 `status: placeholder`、`source_fingerprint: none`、`verified_by: work-id`、current date 的 page；exclusive create 失敗時刪除本次殘留，不覆寫既有檔。
- agent 只能在 planned path 填入 evidence-backed body 並改為 active。
- `seal_pages()` 在任何 write 前對候選與 current Wiki 執行 parse/source/type/location/placeholder-token/critical-lint preflight；全部通過才更新 fingerprint/date/provenance。G3 仍 reconcile 完整 Wiki diff。

### Extension Projection 與 Prompt

- `PublicCommandName/Intent` 增加無參數 `{type: "wikiBootstrap"}`，composer 精確輸出 `$devweave wiki bootstrap` 並標為 mutation。
- `KnowledgeProjection` 增加 `bootstrapComplete`、`bootstrapRecommended`、`bootstrapReasons`、covered/uncovered paths 與 typed review；`WikiPageProjection` 增加 `verifiedBy`。
- Filesystem reader 只做 non-authoritative syntactic bootstrap assessment；work-level coverage/review 取自 ledger fields，不重算 Git/source fingerprint。
- Webview dropdown 與 recommendation CTA 送出同一 intent；Command Palette `devweave.wikiBootstrap` 先用 composer 顯示 modal preview，明確確認後才複製，不執行 engine。

## 失敗模式與回復

- Bootstrap 已完整：回傳成功 `already_complete`，不建立 state。多個 active bootstrap：回傳 selection/validation error，由人類處理，不隱式關閉任何 Work Item。
- Context 漂移：G2 前使 scope gate stale並回 requirements；G2 後產品變更改由 review/G3，不形成無限 gate loop。
- Review 後 source 再變：保留舊 review audit、設定 `invalidated_at`、清空 plan/seals；status/instructions 指向重新 review。
- Scaffold 參數、asset、path、source 或 target 衝突：在 write 前 fail closed；exclusive create 發生 I/O 失敗時移除本次 target/temporary file。
- Seal preflight 失敗：任何 page 都不寫；agent 修正 placeholder/token/index/link/source 後重跑。多檔 seal 保留現有 per-file atomic replace，G3 會偵測不完整集合。
- Extension malformed state：維持 read-only diagnostic；mutation prompt composer 拒絕。Command Palette preview 取消時 clipboard 不變。
- Rollback：程式與文件可由一般 source rollback 回復；additive state keys 與新 Wiki frontmatter 對舊 engine 無害。已建立 bootstrap Work Item 不自動刪除，依既有 revise/close 流程處理；不修改或重寫 machine ledger。
- 觀測：每個 bootstrap/review/scaffold/invalidation/seal action 追加 stable event，CLI JSON 與 status reasons 可直接定位，不新增 telemetry。

## 高風險分析

- Migration：不提高 schema version、不批次重寫既有 state；new-state marker 決定是否啟用 review contract。fixtures 必須同時覆蓋 legacy/new。
- Rollback：沒有 database、remote state 或不可逆 migration；source rollback 後舊 engine 忽略 additive keys。Wiki page 仍是標準現有 schema。
- Security：所有 source/page 保持 repo-relative，沿用 symlink containment與禁止 Wiki/`.devweave`/`.git` sources；scaffold 無 arbitrary metadata，Extension 無 process/network/write path。
- Compatibility：既有八個 public verbs、start kinds、gate/phase、exit codes、JSON top-level `ok` 與 legacy knowledge plan 維持；新增欄位與第九個 public intent不改舊 caller payload。
- Performance：bootstrap assessment 是 O(pages)，coverage 是 bounded changed paths × page sources；不新增 index/database。輸出沿用 50-item caps，context 固定六筆（index+五頁），source page 仍最多五個 sources。
- Residual risk：semantic durable-value 判斷無法由 machine 證明，仍由 review rationale 與 G3 人工核准承擔；Extension 的 bootstrap recommendation 是 non-authoritative projection，engine output 才是最終判定。

## 設計決策

## DEC-001: 決策名稱
- Requirements: REQ-003, REQ-007, REQ-008, REQ-009, NFR-002, NFR-003
- Decision: 以 `knowledge_core` 作為知識運算/檔案的深 module，`devweave_core` 作為 lifecycle/policy 深 module；CLI、guard、Extension 僅為 adapter。
- Rationale: 複雜規則集中在兩個既有 seam，可由相同 interface 驗證，避免 caller 複製 policy。
- Consequences: 需要新增少量 core functions，但不新增抽象 port；測試以 module interface 的 observable result 為主。

## DEC-002: Bootstrap 使用 Feature Profile

- Requirements: REQ-001, REQ-002, NFR-001
- Decision: 使用 optional `knowledge_profile: bootstrap`，不新增 WorkKind；machine command在 project lock 下採 already-complete/resume/create。
- Rationale: 重用既有 gates/artifacts/evidence，保持 public start kind 與 fixtures 相容。
- Consequences: Bootstrap-specific G3 checks 必須 conditional；同一時間多個 bootstrap profile 會 fail closed。

## DEC-003: Review 取代每次強制 Wiki Diff

- Requirements: REQ-005, REQ-006, REQ-010
- Decision: 新式 Work Item 必須保存 current `promote|no-update` review；只有 promote 能建立非空 plan。
- Rationale: 同時取得 traceability 與內容品質，避免編造更新。
- Consequences: G3 多一個明確 machine step；legacy Work Item不追溯要求。

## DEC-004: Product Fingerprint 綁定 Review 與 Plan

- Requirements: REQ-003, REQ-005, REQ-007, NFR-001
- Decision: review/plan 保存 current git source fingerprint，source 改變就 invalidated/清 plan；G2 後的預期 source 變更不回捲 G1 context。
- Rationale: 避免以過期 changed-path 判斷 promotion，同時避免 implementation 因 Wiki source drift 無限回到 G1。
- Consequences: phase-aware context currentness 必須有 lifecycle tests；Wiki-only edits不會誤殺 product evidence。

## DEC-005: Canonical Template Exclusive Scaffold

- Requirements: REQ-008, REQ-009, NFR-002
- Decision: 單一 conditional scaffold 解析 canonical template body、以 renderer 產生 placeholder frontmatter，並採 no-overwrite exclusive create。
- Rationale: 九種類型共享深 interface，保留 template 資產價值與 path/source safety。
- Consequences: dependency/decision 有 conditional args；seal 前需人工完成 body/status。

## DEC-006: Coverage 是決策輸入，不是逐檔配額

- Requirements: REQ-007, REQ-010, NFR-003
- Decision: status 分類 covered/uncovered paths，但 G3 只強制 affected existing pages；uncovered durable value 由 review rationale 與 planned pages語意處理。
- Rationale: machine 可可靠判定 path overlap，不能可靠判定何者值得長期保存。
- Consequences: 高價值判斷留在人工 G3；不會產生一檔一頁爆炸。

## DEC-007: Extension 維持 Prompt-only Adapter

- Requirements: REQ-011, REQ-012, NFR-002, NFR-003
- Decision: 三入口使用同一無參數 intent/composer；Command Palette 以 modal preview 後複製，永不執行 CLI。
- Rationale: 維持既有安全 seam與 engine authority。
- Consequences: Extension recommendation 是 non-authoritative，使用者仍需在 Codex Chat 執行 workflow。

## DEC-008: 有界 Markdown Query，不新增 Retrieval Runtime

- Requirements: REQ-004, NFR-003
- Decision: query 固定 index 加最多五頁、gap 後最小 source follow-up，不加入 FTS/vector/token measurement。
- Rationale: 直接利用 source-bound Markdown 與 agent 語意判斷，降低操作面與 runtime 成本。
- Consequences: 大型 repository 的 page selection 品質依賴 index 與持續 promotion；bootstrap/review 閉環負責改善。

# 系統設計：高風險 G3 獨立 Review Agent

<!-- DEVWEAVE:artifact=design version=1 work=20260804-122803-feature-g3-review-agent -->

## 設計摘要

本變更維持 DevWeave 單一 lifecycle router。當且僅當 high-risk Work Item 到達 G3 (`verification`／`acceptance_review`) 且產品、Wiki、baseline、diff、scope 與既有 evidence 已穩定後，router 在 G3 summary 前以隔離、唯讀 context 啟動 1 個 Review Agent。Python engine 不 spawn Agent，也不接收主 Agent 的推理；它只透過 machine-only `review record` 介面驗證、保存與投影 reviewer 結果。

Review Agent 只能讀取核准 artifacts、完整 diff、risk analysis、scope、baseline、Wiki 與現有 evidence，不得修改 source、Wiki、ledger，不得執行 approve、revise 或 close。結果以固定 UTF-8 JSON envelope 交給 engine。engine 會產生 `kind: review` 的 evidence、當前 source fingerprint、Git HEAD、report SHA-256、provenance 與 bounded raw report；raw report 只保存於 `.devweave/cache/logs/<work-id>/`。

G3 對 review 的判定是明確分層：`passed` 正常通過；`unavailable`、timeout、malformed output 或 advisory findings 形成可追蹤 warning，不阻擋人工核准；`critical` security、data-loss、不可回復性或 scope finding 阻擋 G3，只有針對具名 finding ID 的窄幅 `review-critical` waiver 能解除。human G3 approval 仍是最後關卡。

## 選項比較

| 選項 | 作法 | 結論 |
| --- | --- | --- |
| A. 擴充一般 `evidence add` | 以多個自由參數模擬 reviewer 結果，raw report 由呼叫端自行管理 | 不採用；容易遺漏 reviewer provenance、固定輸出驗證與報告 containment，也會讓一般 evidence 與 review gate 語意混在一起。 |
| B. 新增 machine-only `review record` | engine 解析固定 report envelope，產生唯一 review evidence、hash、provenance 與 bounded cache log | 採用；維持 ledger 單一寫入者，將安全邊界與 review-specific gate 規則集中在 engine。 |

| 設計問題 | 選項 | 結論 |
| --- | --- | --- |
| Agent 由誰啟動 | Python engine spawn；或既有 DevWeave router 呼叫一次 Agent | 採用 router；engine 維持 deterministic、可測試且不新增第二套 orchestrator。 |
| raw report 如何傳入 | shell argument 字串；或 repo-relative bounded report file | 採用 report file；支援多行報告，避免 shell escaping／命令列洩漏，且能做 path containment、size limit、redaction 與 hash。 |
| reviewer 失敗如何處理 | 一律 block；或 unavailable/advisory warning、critical block | 採用分層；Agent availability 不取代人類核准，實質不可接受風險仍必須阻擋。 |
| source 更新後如何處理 | 沿用舊 review；或以 source-bound evidence 失效並要求重審 | 採用失效；review 必須針對目前 source fingerprint，避免 stale assurance。 |

## 介面與資料流

### Router invocation contract

verification phase 會在 G3 summary 前、且只在 high-risk 與 final artifacts 穩定後，呼叫一次 reviewer，使用隔離 context（工具層的 `fork_context: false` 或等價的獨立 context 設定，不帶入主 Agent 推理）。router 將下列唯讀輸入列入 reviewer prompt：核准 brief／requirements／design／plan、完整 Git diff、risk analysis、scope、accepted baseline、Wiki context 與既有 evidence。prompt 明確禁止 workspace mutation、ledger mutation、approval、revise、close 與額外 Agent delegation。

Reviewer 回傳固定 JSON envelope，router 將其寫入 `.devweave/cache/incoming/<work-id>/` 的暫存 report file，再呼叫 machine-only CLI：

```text
python -B .agents/skills/devweave/scripts/devweave.py --repo . review record \
  --work <work-id> \
  --reviewer-id <opaque-agent-id> \
  --report-file .devweave/cache/incoming/<work-id>/<attempt>.json
```

`reviewer-id` 只是不透明識別值；不得用它推導權限或使用者身份。engine 不提供新的公開 `$devweave` chat verb；`review record` 是 machine-only CLI surface，且不取代既有 lifecycle router。

### Fixed report envelope

Report 必須是 UTF-8 JSON object，欄位與限制如下：

```json
{
  "result": "passed | unavailable | critical",
  "severity": "none | advisory | critical",
  "summary": "bounded reviewer summary",
  "source_fingerprint": "current source fingerprint",
  "covers": ["AC-001"],
  "tasks": ["TASK-001"],
  "findings": [
    {
      "id": "F-001",
      "severity": "advisory | critical",
      "title": "bounded finding title",
      "evidence": "bounded supporting observation",
      "recommendation": "bounded recommendation"
    }
  ]
}
```

Engine 僅接受 machine keys、有限 enum、非空合法 AC/TASK ID 與具名 finding ID；`passed` 不得帶 critical finding，`critical` 必須至少有一個 `critical` finding，`unavailable` 不得被偽裝成 passed。Malformed output 不進入 ledger；router 應將 timeout、無輸出或格式錯誤轉成 `unavailable` envelope 後再記錄，讓 warning 仍有 provenance。

### Evidence record

engine 以既有 `_next_evidence_id` 與 ledger writer 建立一筆 `kind: review` evidence，沿用 schema version 1 的 additive model，不改既有 evidence kind 的必填欄位。新增 review-specific metadata：

```json
{
  "kind": "review",
  "status": "passed | failed",
  "summary": "redacted summary",
  "source_fingerprint": "current fingerprint",
  "git_head": "current HEAD",
  "binds_current_source": true,
  "stale": false,
  "raw_log": ".devweave/cache/logs/<work-id>/<EVID>.log",
  "review": {
    "result": "passed | unavailable | critical",
    "severity": "none | advisory | critical",
    "reviewer_id": "opaque id",
    "context_mode": "isolated_read_only",
    "report_sha256": "sha256 of redacted stored report",
    "findings": [],
    "covers": ["AC-001"],
    "tasks": ["TASK-001"]
  }
}
```

完整原始報告（先做 secret redaction，再依 project evidence limit bounded）寫入 cache log，不能由 Agent 直接編輯 JSON／JSONL evidence ledger。`report_sha256` 對 redacted、實際保存 bytes 計算；`log_truncated` 與原有 raw-log semantics 一致。provenance 同時保留 EVID ID、current fingerprint、Git HEAD、reviewer ID、context mode、created timestamp 與 report hash。

### G3 validation and state flow

在 acceptance validation 中，`review` 不再以一般 required evidence kind 的缺失錯誤處理，而由獨立規則處理：

1. 只取 `kind: review`、`binds_current_source: true`、`stale: false`、fingerprint 等於目前 source 的 evidence。
2. high-risk 缺少 current review 或結果為 `unavailable` 時加入 warning，不阻擋 acceptance；一般／低風險不產生 reviewer requirement。
3. `passed` 通過；advisory finding 加 warning；`critical` finding 對每個 finding ID 檢查 exact `review-critical` waiver，沒有具名 waiver 就加入 error。
4. accepted `review-critical` waiver 只能以 `gate=acceptance`、具名 finding ID、明確理由與 approver 解鎖；wildcard、空 target 或 broad waiver 不接受。
5. high-risk `acceptance.md` 必須列出 reviewer result、warning／findings、review evidence ID／report evidence 與 waiver（如有），讓 machine validation 與人工核准可追溯。

review evidence 綁定目前 source fingerprint；既有 source-change synchronization 將它標記 stale 並使 acceptance gate 回到 verification。任何 stale review 都不能滿足 G3。legacy evidence 沒有 `review` metadata 時保持可讀，但不能被誤認為 current independent review。

### Control Center projection

Extension `snapshot` 只讀取、驗證並投影 nested review metadata；legacy evidence 缺少該 metadata 時安全降級。acceptance readiness 對 high-risk 增加 `Independent Review` check：missing、unavailable、advisory 是 attention／warning；critical 是 `not-ready`／blocking；current passed 才是 ready。Projection 不啟動 Agent、不執行 CLI／shell／Git／network，也不自行 approve 或判定 lifecycle gate。

## 失敗模式與回復

| 情境 | Engine／router 行為 | G3 結果與回復 |
| --- | --- | --- |
| Agent timeout、不可用或無輸出 | router 產生 `unavailable` envelope，保留 reason 與 attempt provenance；engine 寫 review evidence | warning；人類仍可核准。必要時由 router 在 source 未變時重新發起下一次明確 review。 |
| JSON malformed、enum／ID／source fingerprint 不合法 | engine 拒絕 malformed report；router 以目前 fingerprint 建立 unavailable report，記錄 warning | 不以 malformed 結果假冒 passed；warning，不阻擋人工核准。 |
| report path 越界、過大或包含 secret | engine 僅讀取 incoming containment 內檔案，做 bounded read、redaction、hash；越界拒絕 | 不寫入 product source 或 ledger；產生可追蹤 warning，保留最小錯誤摘要。 |
| advisory finding | evidence 保留 finding 與 report | attention warning，不阻擋 G3。 |
| critical finding | evidence 保留具名 finding | 無 exact `review-critical` waiver 時 blocker；有窄幅 waiver 時 warning 並要求 acceptance 明列 waiver。 |
| source fingerprint 改變 | engine 既有 synchronization 標記 review stale，清除 current verification | 必須重新 review；舊 report 不可使用。 |
| router 重複觸發 | router 以單次 G3 attempt guard／session state 避免同一次 G3 多於 1 個 reviewer；engine evidence ID 仍唯一 | 不建立第二 lifecycle；若需重審，須在 source／phase 狀態允許下建立新 attempt。 |
| cache 寫入失敗 | engine 不直接修改 evidence ledger，操作失敗可重試 | 不產生虛假 passed evidence；G3 顯示 unavailable／warning。 |

不修改 product source、Wiki 或 accepted baseline 的 review failure 不需 rollback。若已產生暫存 incoming report，router／engine 僅在確認 path containment 後清理；final cache log 保留供 audit。任何重新審查都必須重新產生 report hash 與 evidence，不覆寫既有 EVID。

## 高風險分析

- Migration：採 schema v1 additive nested `review` metadata 與既有 `kind`／field compatibility；legacy evidence 仍可讀，只有 high-risk current G3 要求新的 review check。需要更新 accepted product／architecture／quality baseline 與 contracts，但不回溯 reopen 已 closed Work Item。
- Rollback：可回退 router prompt、engine code、Extension projection 與文件；既有 review evidence 保留為歷史資料，legacy reader 對缺少 nested metadata 安全降級。不可用 stale review 當作回退後的 current assurance。
- Security：reviewer isolated/read-only；不傳主 Agent reasoning；input path containment、size bound、secret redaction、opaque reviewer ID、raw report hash 與 no-direct-ledger-write 減少 prompt／artifact injection 與資料外洩面。reviewer 不具有 approve／revise／close 權限。
- Compatibility：不新增公開 `$devweave` verb、不建立第二 router／orchestrator；standard／low risk 不啟動 reviewer；G2 `Design It Twice` 的條件式 3+ sub-agents 不變；Extension 保持 projection-only。
- Performance：每個 high-risk G3 最多一次 reviewer；engine 只做一次 bounded report read、hash 與 JSON validation，報告寫入既有 cache，不掃描額外 workspace。高風險檢查增加的 latency 是預期 gate 成本；不適用於 standard／low risk。
- Operational observability：review EVID、raw report path、report hash、source fingerprint、Git HEAD、warning／finding、waiver 與 event 形成追蹤鏈；malformed／unavailable 也不得靜默。

## 設計決策

## DEC-001: Router 單一入口、Engine 純記錄驗證
- Requirements: REQ-001, REQ-002, NFR-003
- Decision: 由既有 DevWeave router 在 G3 啟動一次 reviewer；Python engine 不 spawn Agent，只提供 machine-only `review record`。
- Rationale: 維持單一 lifecycle、降低 engine 與模型 runtime 耦合，讓 gate 判定可 deterministic 測試。
- Consequences: router 必須保證 isolated context 與 exactly-once invocation；engine 可獨立測試 malformed、stale、waiver 與 evidence。

## DEC-002: 固定 JSON report envelope 與 repo-relative report file
- Requirements: REQ-003, NFR-002, NFR-003
- Decision: reviewer 以固定 JSON 回傳，router 以 incoming containment 內 report file 傳給 `review record`；engine 負責 schema、ID、source、size、redaction、hash 驗證。
- Rationale: 多行報告可追溯且避免 shell argument；單一 deep module 集中安全規則。
- Consequences: malformed output 需轉 unavailable；router 需建立暫存檔，不能直接編輯 evidence ledger。

## DEC-003: Review 是 source-bound additive evidence
- Requirements: REQ-003, REQ-005, NFR-001
- Decision: 沿用 schema v1 evidence ledger，新增 `kind: review` 與 nested `review` metadata，綁定 source fingerprint、Git HEAD、report hash。
- Rationale: 不引進平行 ledger，並可沿用既有 stale synchronization 與 acceptance fingerprint。
- Consequences: source 改變後舊 review 必須重新產生；legacy evidence 可讀但不滿足新的 high-risk review check。

## DEC-004: Availability warning、實質 critical blocker
- Requirements: REQ-004, REQ-006
- Decision: unavailable／advisory 只產生 warning；critical finding 只有 exact named `review-critical` waiver（acceptance gate）能解除。
- Rationale: reviewer runtime failure 不應取代 human approval，但 security、data-loss、不可回復性與 scope 風險不可被 advisory 流程掩蓋。
- Consequences: acceptance.md 必須列出 result、warnings、findings、report evidence 與 waiver；waiver validation 必須拒絕 wildcard／broad target。

## DEC-005: Extension 只投影 readiness
- Requirements: REQ-007, NFR-001
- Decision: snapshot 解析 review evidence，presentation 增加 Independent Review check；Extension 不啟動 Agent、呼叫 engine 或修改 gate。
- Rationale: 延續既有 read-only Control Center 邊界，避免第二套 workflow 判定。
- Consequences: UI 只能提供 snapshot guidance；真正的 record、validation 與 human approval 仍由 DevWeave CLI／router／人類完成。

## DEC-006: G2 multi-agent design 與 G3 single reviewer 分離
- Requirements: REQ-001, REQ-002, NFR-001
- Decision: 保留 G2 `Design It Twice` 的條件式 3+ sub-agents；新增功能只限定 high-risk G3 固定 1 個獨立 reviewer。
- Rationale: alternative design comparison 與 final risk review 目的、時機、權限不同，不能互相取代。
- Consequences: contracts、README、使用手冊與 AGENTS 必須明確說明兩者差異，且不得新增第二 lifecycle。

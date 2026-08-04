# 執行計畫：高風險 G3 獨立 Review Agent

<!-- DEVWEAVE:artifact=plan version=1 work=20260804-122803-feature-g3-review-agent -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 engine review record 與 evidence provenance
- Traces: REQ-003, REQ-005, NFR-001, NFR-002, AC-005, AC-006, AC-009, AC-014, DEC-001, DEC-002, DEC-003
- Inputs: 現有 `devweave_core.py` evidence writer、source fingerprint、Git HEAD、cache log policy、固定 report envelope
- Output: machine-only review record deep module；`kind: review` additive evidence；bounded/redacted raw report；report hash、reviewer ID、context mode、findings、coverage 與 provenance；source freshness／legacy compatibility validation
- Verification: passed／unavailable／critical／malformed／timeout-shaped report、path containment、size limit、redaction、hash、provenance、source mutation regression tests
- Dependencies: none

## TASK-002: 接上 CLI 與 narrow review-critical waiver contract
- Traces: REQ-004, REQ-005, REQ-006, NFR-003, AC-007, AC-008, AC-009, AC-010, AC-015, DEC-003, DEC-004
- Inputs: TASK-001、既有 `evidence`／`waiver` parser、acceptance validation、acceptance artifact headings
- Output: `review record` machine-only subcommand；不新增公開 chat verb；critical finding exact-ID waiver；warning／blocker deterministic messages；high-risk acceptance review section與 report evidence requirement
- Verification: critical blocks；具名窄幅 waiver 解鎖；wildcard／broad／錯誤 gate 拒絕；unavailable／advisory warning；stale review invalidation；acceptance.md trace validation
- Dependencies: TASK-001

## TASK-003: 更新 G3 router protocol 與 reviewer isolation instructions
- Traces: REQ-001, REQ-002, REQ-006, NFR-001, AC-001, AC-002, AC-003, AC-004, AC-010, AC-013, DEC-001, DEC-004, DEC-006
- Inputs: TASK-001／TASK-002 contract、既有 verification phase、SKILL.md、G2 Design It Twice policy、AGENTS／contracts 文件
- Output: verification phase 固定一次 high-risk reviewer invocation；isolated read-only prompt／fixed JSON protocol；timeout／malformed fallback；G2/G3 distinction；不新增 lifecycle/router/orchestrator 的同步文件
- Verification: repository contract checks for exactly-one/high-risk-only/router-owned spawn/read-only/no-approval language；manual high-risk invocation and workspace immutability check
- Dependencies: TASK-002

## TASK-004: 更新 VS Code Control Center review readiness projection
- Traces: REQ-007, NFR-001, AC-011, AC-012, AC-013, DEC-003, DEC-005
- Inputs: TASK-001／TASK-002 evidence shape、既有 snapshot model、presentation readiness checks、legacy evidence projection
- Output: high-risk acceptance `Independent Review` check；passed ready；missing／unavailable／advisory attention；critical not-ready；raw evidence／guidance projection；Extension 維持 read-only
- Verification: Extension unit／typecheck／package／smoke tests，覆蓋 high-risk missing/passed/advisory/unavailable/critical 與 legacy evidence、keyboard/raw expansion regression
- Dependencies: TASK-001, TASK-002

## TASK-005: 建立 engine／CLI／contract regression suite
- Traces: NFR-001, NFR-002, NFR-003, AC-001, AC-002, AC-005, AC-006, AC-007, AC-008, AC-009, AC-013, AC-014, AC-015, DEC-001, DEC-002, DEC-003, DEC-004, DEC-006
- Inputs: TASK-001 至 TASK-004 的 public machine contracts、既有 83 Python tests、repository contract test harness
- Output: targeted Python tests、CLI tests、repository policy／contract tests；保護 no-second-router、no-direct-ledger-write、G2 multi-agent compatibility
- Verification: targeted tests、full Python suite、contract suite、`git diff --check`、configured high-risk verification command set
- Dependencies: TASK-001, TASK-002, TASK-003, TASK-004

## TASK-006: 同步文件、accepted baseline 與 Wiki knowledge review
- Traces: REQ-006, REQ-007, NFR-001, AC-010, AC-011, AC-012, AC-013, DEC-004, DEC-005, DEC-006
- Inputs: 已驗證 implementation、既有 baseline product／architecture／quality、Wiki context gap、README／使用手冊／AGENTS／contracts／Extension guidance
- Output: 明確區分 G2 optional 3+ design agents 與 high-risk G3 one independent reviewer；更新治理與使用文件；在 verification 依 knowledge plan 更新不超過五頁 Wiki content、index、log 並 seal affected pages
- Verification: baseline validation、Wiki diff／placeholder／index／promote log／seal checks、README／使用手冊／AGENTS／contracts consistency search
- Dependencies: TASK-003, TASK-004, TASK-005

## 驗證策略

- Targeted engine／CLI：固定 report schema；high-risk passed、unavailable、timeout-shaped、malformed、advisory、critical、exact waiver、stale source、legacy evidence；report size/path containment、redaction、hash 與 provenance。
- Regression／contract：standard／low risk 不產生 reviewer requirement；G2 `Design It Twice` 仍是條件式 3+ sub-agents；沒有新增公開 `$devweave` verb、第二 lifecycle、平行 ledger；Extension 不啟動 Agent 或 workflow mutation。
- Full build：沿用 `.devweave/project.json` 已核准 command set，至少執行 Python unit tests、Extension typecheck／unit tests／package／smoke、repository quick validation 與 high-risk acceptance validation。
- Manual acceptance：high-risk G3 實際只啟動一次隔離 reviewer；reviewer 不修改 workspace；timeout／unavailable 可帶 warning 進入人工 G3；critical 阻擋；source 變更要求重新 review；human approve 仍是最後關卡。
- Risk-specific checks：檢查 report raw bytes 不超過 configured limit、final path 位於 `.devweave/cache/logs/<work-id>/`、secrets 已 redacted、hash 對應保存內容、evidence provenance 可由 EVID 對回 report 與 Git/source fingerprint。

## 基線更新計畫

- `.devweave/baseline/product.md`：補充 high-risk G3 one independent reviewer、unavailable/advisory warning、critical finding blocker、human approval，以及 G2 optional design comparison 的差異。
- `.devweave/baseline/architecture.md`：補充 router-owned isolated invocation、engine-owned review record、schema-v1 additive evidence、cache provenance、Extension projection-only 邊界。
- `.devweave/baseline/quality.md`：補充 review record／stale／waiver／report safety 與 high-risk verification commands；記錄實際驗證結果。
- `README.md`、`docs/使用手冊.md`、`AGENTS.md`、相關 contracts 與 `.agents/skills/devweave/` references：同步 machine protocol 與 user-facing Traditional Chinese guidance。
- Wiki verification knowledge plan：針對 G1 已記錄 gap，預計只更新 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`，必要時新增一頁高風險 review contract；上限五頁，並同步 `wiki/index.md` 與 promote log，完成後 seal。若實際 diff 顯示部分頁面無 durable change，依 DevWeave `no-update`／promote 規則處理。

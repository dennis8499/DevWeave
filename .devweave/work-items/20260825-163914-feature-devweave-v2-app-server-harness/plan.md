# 執行計畫：DevWeave V2 app-server harness

<!-- DEVWEAVE:artifact=plan version=1 work=20260825-163914-feature-devweave-v2-app-server-harness -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 V2 contract 與 package 骨架
- Traces: REQ-011, REQ-015, NFR-004, NFR-006, AC-011, AC-015, AC-019, AC-021, DEC-002, DEC-010
- Inputs: Approved brief/requirements/design、現有Python launcher/tests、Extension package/build與official app-server/MCP docs
- Output: `devweave_v2`分層package、schema-v2 types/errors/canonical JSON、thin transitional V2 launcher、2.0.0 shared version、contract fixtures與dependency/file-size/schema trace checks；不改current v1 governance launcher
- Verification: V2 schema golden/unknown-field/error-code tests、import/dependency contract、version parity、legacy command不存在於V2 parser、`git diff --check`
- Dependencies: none

## TASK-002: 實作 ExecPlan、RunService、risk/Gate 與 decision state
- Traces: REQ-005, REQ-007, REQ-008, NFR-001, NFR-002, AC-005, AC-007, AC-008, AC-016, AC-017, DEC-002, DEC-003, DEC-004
- Inputs: TASK-001 schemas/package、risk matrix、docs ExecPlan layout
- Output: Atomic PlanStore、optimistic revision/idempotency、RunService agent/host facades、risk escalation、Gate fingerprint/invalidation、immutable task definition、PendingDecision lifecycle與RunSnapshot reducer
- Verification: In-memory/filesystem adapter tests涵蓋三種risk、stale revision、unknown field、cancel/malformed decision、crash-before/after-write與duplicate event；完成一個scoped local commit
- Dependencies: TASK-001

## TASK-003: 實作 Git transaction 與 V1 export
- Traces: REQ-006, REQ-010, NFR-007, AC-006, AC-010, AC-022, DEC-005, DEC-008
- Inputs: TASK-002 RunService、recorded base ref、current 21 closed work/411 evidence repository history
- Output: GitPort/production adapter、clean/detached/collision preflight、run branch、declared-path staging/commit guard、base-ref invariant；`export-v1`從Git ref產生byte-stable JSON/Markdown index與recovery provenance
- Verification: Disposable repositories涵蓋clean/dirty/untracked/detached/collision/unrelated diff/base drift；export執行兩次byte-identical且斷言21 closed/411 evidence/input未改；完成一個scoped local commit
- Dependencies: TASK-002

## TASK-004: 重構 controlled verification 與 bounded observability
- Traces: REQ-013, NFR-001, NFR-003, AC-013, AC-016, AC-018, DEC-006
- Inputs: TASK-001 contracts、既有command_policy/controlled executor regression、TASK-002 revision/fingerprint
- Output: VerificationPlan evaluator、runtime executable resolver/hash、DAG/selection/writer barrier、shell-free executor、declared-effect reconciliation、typed evidence、redaction/size limits與usage-unavailable semantics
- Verification: read-only/writer/release-only/dependency/timeout/nonzero/undeclared/stale/runtime-path fixtures，確認只有current zero-exit declared effect gate-eligible且tracked config無絕對executable/hash；完成一個scoped local commit
- Dependencies: TASK-001, TASK-002

## TASK-005: 建立 project-scoped MCP server
- Traces: REQ-003, REQ-004, REQ-008, NFR-001, AC-003, AC-004, AC-008, AC-016, DEC-002, DEC-003, DEC-010
- Inputs: TASK-002 agent facade、TASK-004 verification、official project-scoped MCP config contract
- Output: stdio MCP initialize/tools-list/tools-call adapter、exact八tool schemas/annotations、bounded framing、`.codex/config.toml` required server與enabled_tools allowlist；無host alias/passthrough
- Verification: Transcript integration測試initialize/list/call、wrong protocol、unknown tool/field、path traversal、stale run、host impersonation、tool annotations與required config；Codex status probe fixture；完成一個scoped local commit
- Dependencies: TASK-002, TASK-004

## TASK-006: 建立公開 CLI 與 authenticated host bridge
- Traces: REQ-002, REQ-004, REQ-011, NFR-001, AC-002, AC-004, AC-011, AC-016, DEC-002, DEC-010
- Inputs: TASK-002 RunService、TASK-003 Git/export、TASK-004 verification
- Output: `doctor/inspect/check/verify/export-v1/mcp-serve`公開CLI、JSON envelope/exit codes、Codex absolute/PATH preflight與private child-stdio host bridge memory challenge；無download/fallback
- Verification: CLI process tests與fake executable/schema generator涵蓋PATH/config/missing/not-file/version/schema failure；host handshake/forged role/replay/EOF tests；缺Codex時零run/branch side effect；完成一個scoped local commit
- Dependencies: TASK-002, TASK-003, TASK-004

## TASK-007: 實作 CodexAppServerSession 與 event reducer
- Traces: REQ-001, REQ-002, REQ-012, NFR-002, NFR-006, AC-001, AC-002, AC-012, AC-017, AC-021, DEC-001, DEC-009, DEC-010
- Inputs: TASK-001 shared TS contracts、TASK-006 doctor/host client、official app-server stable subset
- Output: shell-free child transport、initialize/initialized、request correlation/timeouts、thread/turn/review/MCP-status method allowlist、bounded JSONL/error handling、authoritative item completion reducer、reasoning-content discard與reconnect/resume
- Verification: Scripted transcript tests涵蓋handshake、start/resume/steer/interrupt、plan/diff/item/usage/warning/error、malformed/oversized/unknown event、out-of-order response、exit/restart、experimental method rejection；完成一個scoped local commit
- Dependencies: TASK-001, TASK-006

## TASK-008: 實作 WorkspaceController、approval broker 與 review loop
- Traces: REQ-004, REQ-005, REQ-014, NFR-001, NFR-002, AC-004, AC-005, AC-014, AC-016, AC-017, DEC-001, DEC-002, DEC-004
- Inputs: TASK-002 RunService state、TASK-005 MCP readiness、TASK-007 app-server session
- Output: Per-workspace supervisor、host-only start/resume/decision/gate/cancel、phase-based sandbox、Codex command/file approval scope broker、completion orchestration、standard/high detached review與high max-three fix/reverify
- Verification: Controller harness涵蓋agent不能host mutate、pre-Gate read-only、scope denial、approval accept/decline/cancel、required MCP failure、review detached identity、advisory/critical/third-round blocker、restart idempotency；完成一個scoped local commit
- Dependencies: TASK-002, TASK-005, TASK-007

## TASK-009: 重建 VS Code rich client 與 accessibility evidence
- Traces: REQ-012, NFR-003, NFR-005, AC-012, AC-018, AC-020, DEC-009
- Inputs: TASK-007 event projection、TASK-008 controller、現有theme/CSP/a11y seams
- Output: Connection/run/thread/turn/plan/diff/tool approval/PendingDecision/Gate/verification/review/usage/diagnostic UI與start/resume/steer/interrupt/cancel controls；移除clipboard/prompt/Wiki snapshot workflow；DOM/a11y/log/screenshot evidence runner
- Verification: Unit/DOM tests、keyboard/roving tabindex/focus restore/ARIA/forced-colors/reduced-motion、stale-vs-authoritative labels、CSP/no-secret/no-reasoning、bounded screenshot provenance；typecheck/build與scoped local commit
- Dependencies: TASK-007, TASK-008

## TASK-010: 建立 docs knowledge tree、單一 Skill 與 architecture guardrails
- Traces: REQ-009, REQ-015, NFR-004, AC-009, AC-015, AC-019, DEC-007, DEC-008
- Inputs: TASK-001 architecture contract、approved artifacts、current README/AGENTS/baseline/Wiki/companions
- Output: 短版`AGENTS.md`、`ARCHITECTURE.md`、`docs/index.md`、product/design/reliability/security/quality、generated/exec-plan/tech-debt結構；單一DevWeave skill與phase references；link/duplicate-truth/instruction-size/module-size/dependency/trace checker
- Verification: Bounded-hop navigation、broken link、duplicate canonical topic、oversized module/root instructions、reverse dependency、schema/AC trace fixtures；repo搜尋無legacy companion invocation作為V2 surface；完成一個scoped local commit
- Dependencies: TASK-001, TASK-002

## TASK-011: 準備 2.0.0 package 與 clean-cutover finalizer
- Traces: REQ-010, REQ-015, NFR-006, NFR-007, AC-010, AC-015, AC-021, AC-022, DEC-005, DEC-008, DEC-010
- Inputs: TASK-003 export、TASK-005 MCP config、TASK-006 V2 launcher、TASK-009 Extension、TASK-010 docs/Skill
- Output: 2.0.0 source-derived VSIX candidate流程、VSIX gitignore/untracking、schema-v2 project config、exact legacy deletion/rename hash manifest與idempotent finalizer；在disposable clone驗證final HEAD無v1 raw ledger/Wiki/baseline/companions/clipboard/VSIX binaries
- Verification: Candidate verify-before-promote tests、version/entry/hash/provenance、finalizer fresh/retry/hash-mismatch/failure preservation、Git history recovery與post-finalizer V2 check；完成一個scoped local commit，實際repository finalizer保留到legacy G3 explicit approval後執行
- Dependencies: TASK-003, TASK-005, TASK-006, TASK-009, TASK-010

## TASK-012: 執行完整驗證、recovery drill 與 transition rehearsal
- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-011, AC-012, AC-013, AC-014, AC-015, AC-016, AC-017, AC-018, AC-019, AC-020, AC-021, AC-022, DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-007, DEC-008, DEC-009, DEC-010
- Inputs: TASK-001至TASK-011 outputs、Codex CLI hard prerequisite、Windows VS Code runtime、legacy transition work item
- Output: Targeted/full Python、MCP、Extension、package、docs、Git/recovery、real app-server E2E與UI evidence；V1 knowledge/baseline transition artifacts、acceptance matrix與pre-reviewed finalizer manifest；exactly-one isolated high-risk reviewer input ready
- Verification: 所有declared commands current/gate-eligible、22 AC有source-bound evidence、real Codex stdio/MCP/detached review round-trip、Windows walkthrough/screenshots、base ref unchanged、`git diff --check`與clean scoped diff；Codex CLI不存在時明確blocked而非mock pass
- Dependencies: TASK-004, TASK-008, TASK-011

## 驗證策略

- Targeted：每個TASK先跑對應Python unittest或Extension unit/DOM seam；失敗先停在該slice，不把後續full suite噪音混入。
- Contract：schema-v2 golden/invalid cases、CLI/MCP/host/app-server transcripts、role/revision/scope/path/symlink、dependency direction、docs navigation、module/root-size與REQ/AC/DEC/TASK trace。
- Git/recovery：全在disposable repositories驗證branch/commit/unrelated diff/base ref、V1 Git-ref export、crash injection、idempotent finalizer與Git-history recovery。
- Verification engine：read-only與writer DAG、changed paths、release-only、timeout/nonzero、undeclared effect、stale digest、runtime executable provenance及writer barrier。
- Extension：unit、DOM/a11y、typecheck、build、candidate package verifier及Windows Extension Host smoke；UI evidence包含bounded logs與關鍵screenshots hash。
- Live integration：使用實際resolved Codex CLI跑stdio initialize、required DevWeave MCP startup/status、thread start/resume、turn steer/interrupt、native approval與detached review。Fake transcript只算contract test，不能覆蓋AC-001/live certification。
- Regression：在legacy G3前保留既有repository contract、Python/Extension suites；V2 finalizer後改跑V2 full suite與final tree contract。
- Acceptance：每筆evidence綁current source/plan/command digest並連到TASK/AC；high-risk final diff由exactly-one isolated read-only reviewer檢查，critical findings不以廣泛waiver略過。
- Hygiene：所有階段跑`git diff --check`、secret/raw-prompt/reasoning scan、tracked absolute executable/hash scan、tracked VSIX/runtime scan與base-ref invariant。

G2前在legacy project policy新增兩個high-profile commands：`unit-tests-v2`執行V2 Python/contract suites，`app-server-e2e`執行真實Codex integration；現有Extension tests/typecheck/package/smoke仍保留。G2 approval凍結legacy Effective Verification Plan供transition G3使用。Finalizer切到schema-v2 config後，V2 `check/verify`再執行同一套final tree命令，避免用legacy frozen plan冒充post-cutover結果。

## 基線更新計畫

- Legacy G3前更新`.devweave/baseline/product.md`、`architecture.md`、`quality.md`，記錄2.0.0已驗證能力、上游app-server experimental maturity、Windows certification與transition/finalizer邊界。
- Verification phase將五個affected stale Wiki內容頁列為planned delete並同步legacy index/log，避免把舊clipboard/Wiki模型提升成新truth；actual finalizer再移除剩餘Wiki starter/index/log。
- Canonical長期內容寫入`ARCHITECTURE.md`與`docs/{product,design,reliability,security,quality}.md`；legacy baseline只服務本次G3，final HEAD移除，避免雙重truth。
- `docs/generated/v1-export.{json,md}`保存base ref、21 closed Work Items、411 evidence files與warning summary；raw payload不複製，回復方式是Git history。
- 本work item在legacy close後轉成`docs/exec-plans/completed/<run-id>.json`，並由finalizer移除`.devweave/work-items/` raw copy。

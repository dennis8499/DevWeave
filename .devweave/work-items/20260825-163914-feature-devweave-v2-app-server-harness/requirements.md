# 需求與驗收條件：DevWeave V2 app-server harness

<!-- DEVWEAVE:artifact=requirements version=1 work=20260825-163914-feature-devweave-v2-app-server-harness -->

## 假設與限制

- 使用者已允許 breaking changes，並選擇 V2 clean cutover；V1 不提供 dual-read 或 mutation compatibility。
- Codex CLI 是 hard prerequisite：只接受 PATH 可解析的 `codex`，或使用者／workspace 設定的絕對 executable path；DevWeave 不下載、不安裝、不猜測、不 fallback。
- App-server 使用 stdio JSONL stable protocol；WebSocket、`tool/requestUserInput` 與 dynamic tools 視為 experimental，本版不依賴。
- 本版認證矩陣限定 Windows x64 與 VS Code；內部 path/process/protocol abstractions 應可攜，但不宣稱其他 OS 已通過。
- Approval、decision resolution、run start/resume/cancel 與 Gate 決議只屬 host；agent-facing MCP server 不暴露等價 mutation。
- V2 run 從乾淨 base branch 建立 `devweave/<run-id>-<slug>` 並留在同一 checkout；不使用 worktree，不 push、不建 PR、不 merge、不自動切回。
- Low/standard/high 的最小 Gate 分別是：plan；plan + acceptance；scope + design + acceptance。Low 使用 self-review；standard 使用 detached review；high 使用 detached review/fix/reverify，最多三輪。
- 目前缺少 Codex CLI 的環境可執行不等於產品可接受；真實 app-server E2E 必須明確列為待補 evidence，不能以 unit mock 取代。

## 需求與驗收條件

## REQ-001: App-server 是主要執行面
- Priority: must
- Acceptance: AC-001
- Description: VS Code Extension 必須透過 Codex app-server stdio JSONL 完成 initialize、thread start/resume、turn start/steer/interrupt、streamed events、review 與 approval request 呈現；clipboard prompt handoff 不得是 V2 workflow path。

## REQ-002: Codex CLI hard prerequisite
- Priority: must
- Acceptance: AC-002
- Description: 啟動 run 前必須解析、驗證並記錄 PATH 中的 Codex CLI 或已設定絕對路徑；缺少、非檔案、不可執行或版本探測失敗時 fail closed，且不自動下載或 fallback。

## REQ-003: Agent-facing MCP capability
- Priority: must
- Acceptance: AC-003
- Description: Project-scoped MCP server 必須只暴露 `run_inspect`、`context_read`、`plan_save`、`decision_request`、`task_update`、`verification_run`、`verification_read`、`completion_request`，並對 run、phase、scope、schema 與權限做 fail-closed validation。

## REQ-004: Host-only control plane
- Priority: must
- Acceptance: AC-004
- Description: `run_start`、`run_resume`、`decision_resolve`、`gate_decide`、`run_cancel` 只能由 Extension host/control plane 呼叫；MCP tool list 與 agent transport 不得提供同義 alias 或任意 method passthrough。

## REQ-005: Risk-adaptive Gate
- Priority: must
- Acceptance: AC-005
- Description: Workflow 必須依 low/standard/high 產生不可跳過的必要 Gate 與 review policy，並以 current artifact fingerprint 綁定 approval；artifact、risk、scope 或 plan 改變時使相關 Gate 失效。

## REQ-006: Run-owned Git transaction
- Priority: must
- Acceptance: AC-006
- Description: 新 run 必須在 clean tracked/untracked preflight 後，於同一 checkout 從 current base 建立 `devweave/<run-id>-<slug>`；base ref 不移動，核准 phase/vertical slice 產生本地 commit，run 不執行 push、PR、merge 或自動切回。

## REQ-007: Typed ExecPlan 與可恢復 state
- Priority: must
- Acceptance: AC-007
- Description: 每個 run 只能有一份 typed ExecPlan 作為目標、決策、task、Gate、evidence 與 completion 的 authority；ephemeral process/event/cache state 必須可重建、可恢復且預設 gitignored。

## REQ-008: Pending decision lifecycle
- Priority: must
- Acceptance: AC-008
- Description: Agent 可提出 typed PendingDecision 並暫停受影響 task；只有 host 可解析有效選項或自訂答案，決議必須寫回 ExecPlan 並喚醒同一 run，取消、逾時、malformed 或 ambiguous answer 維持 pending。

## REQ-009: 單一 docs 知識來源
- Priority: must
- Acceptance: AC-009
- Description: Root `AGENTS.md` 必須縮成導航 map，`ARCHITECTURE.md` 與 `docs/index.md` 提供分層入口，產品、設計、可靠性、安全、品質、generated reference、active/completed ExecPlan 與 tech debt 均位於 `docs/`；V2 不再以 `wiki/` 或 baseline 建立第二份 truth。

## REQ-010: V1 一次性 export
- Priority: must
- Acceptance: AC-010
- Description: `export-v1` 必須唯讀掃描 v1 layout，輸出 deterministic summary/index 與資料計數，能清楚指出 21 個 closed Work Items、411 個 evidence files 的轉換結果；V2 runtime 不讀寫 v1，raw 資料可由 Git history 回復。

## REQ-011: 穩定 CLI 與 typed domain model
- Priority: must
- Acceptance: AC-011
- Description: V2 CLI 必須提供 `doctor`、`inspect`、`check`、`verify`、`export-v1`、`mcp-serve`，並對外使用版本化 `RunSnapshot`、`RunPlanDraft`、`PendingDecision`、`VerificationPlan`、`ReviewFinding` schema 與 machine-readable error codes。

## REQ-012: Rich client workflow UI
- Priority: must
- Acceptance: AC-012
- Description: Extension 必須顯示 connection/preflight、run/thread/turn、plan、diff、tool/approval、pending decision、Gate、verification、review、usage 與 diagnostics，並提供 start/resume/steer/interrupt/cancel 等對應控制；authoritative 與 projection/stale state 必須可辨識。

## REQ-013: 受控驗證與 evidence
- Priority: must
- Acceptance: AC-013
- Description: V2 必須保留 `shell=false`、bounded timeout、DAG/dependency closure、changed-path selection、declared writes/outputs、serial writers、source/input/output fingerprint 與 engine-derived eligibility；驗證只可由 declared executor 執行並產生 typed evidence。

## REQ-014: Review/fix/reverify
- Priority: must
- Acceptance: AC-014
- Description: Standard/high run 必須由與 implement turn 分離的 reviewer context 審查完整 approved plan、diff 與 evidence；high 可自動進行 fix/reverify，但最多三輪，超限或 critical unresolved finding 必須停在 host decision。

## REQ-015: V2 packaging 與 clean cutover
- Priority: must
- Acceptance: AC-015
- Description: 產品、Extension 與文件版本必須一致為 2.0.0；V2 HEAD 不追蹤舊 VSIX binaries、v1 raw runtime history、legacy companion-skill routing 或 clipboard-first UI，且不留下可誤用的 v1 mutation entrypoint。

## NFR-001: Approval 與 mutation 安全
- Priority: must
- Acceptance: AC-016
- Description: 所有高影響 mutation 必須以 typed capability、current run identity、scope、Gate 與 explicit host action 驗證；未知 method、未知欄位、stale revision、越界 path 或 agent 假冒 host 都 fail closed。

## NFR-002: Determinism 與 crash recovery
- Priority: must
- Acceptance: AC-017
- Description: Canonical serialization、stable ordering、atomic replace/append、idempotent reducer 與 process restart 必須讓相同 event sequence 產生相同 RunSnapshot，且 partial write 不可被誤認為 approved/current。

## NFR-003: Privacy 與 bounded observability
- Priority: must
- Acceptance: AC-018
- Description: Metrics 可記錄 duration、event/tool/selection/cache/usage availability 與 bounded diagnostics，但不得保存 raw reasoning、完整 prompts、secrets 或推估 token/cost；payload 與 raw log 必須有明確大小上限與 redaction。

## NFR-004: Maintainability 與 agent legibility
- Priority: must
- Acceptance: AC-019
- Description: Python/TypeScript monolith 必須依 domain boundary 拆分；mechanical checks 必須限制 root instructions、module size、dependency direction、public schema drift、broken docs links 與未追溯 acceptance，例外需有 owner、理由與到期條件。

## NFR-005: UI accessibility 與可觀察驗收
- Priority: must
- Acceptance: AC-020
- Description: 主要 UI 流程必須有 keyboard/focus/ARIA/forced-colors/reduced-motion contract，並在 release verification 產生 DOM/accessibility assertions、bounded logs 與關鍵狀態 screenshot artifacts。

## NFR-006: Windows-first 可攜邊界
- Priority: must
- Acceptance: AC-021
- Description: Windows x64／VS Code 是唯一宣稱的 V2 certification；path、process、JSONL framing、filesystem 與 Git adapters 不得硬編碼 Windows-only business logic，其他 OS 只能標示 unverified。

## NFR-007: 可回復交付
- Priority: must
- Acceptance: AC-022
- Description: 每個核准 phase/vertical slice 必須是可辨識本地 commit，base branch ref 保持不變；V1 export、Git history、run branch 與 failure diagnostics 必須足以在不自動 merge/reset 的前提下調查或回復。

## AC-001: App-server lifecycle round-trip
- Requirement: REQ-001
- Scenario: Given 可用的 Codex CLI 與 disposable repository，When host 啟動並初始化 app-server、start/resume thread、start/steer/interrupt turn 並接收 events，Then UI state 由 protocol event reducer 更新，且 clipboard adapter 不參與 workflow。

## AC-002: CLI preflight fail-closed
- Requirement: REQ-002
- Scenario: Given PATH 可用、設定絕對路徑、缺少 executable、錯誤檔案與 version probe failure fixtures，When 執行 doctor/run preflight，Then 前兩者回報已解析 provenance，其他情境以 machine-readable blocker 停止且沒有下載、run state、branch 或 app-server side effect。

## AC-003: MCP allowlist 與 guard
- Requirement: REQ-003
- Scenario: Given project-scoped MCP client，When 列出並呼叫八個允許 tools、未知 tool、越界 path、stale run 與錯誤 schema，Then only allowlisted/current/in-scope calls 成功，其餘 fail closed 且不改 authoritative state。

## AC-004: Host/agent capability isolation
- Requirement: REQ-004
- Scenario: Given agent MCP session 與 Extension host session，When 兩者嘗試 start/resume/resolve/gate/cancel，Then 只有 host session 可執行，MCP discovery 不包含 host-only operation 或 passthrough。

## AC-005: Risk matrix
- Requirement: REQ-005
- Scenario: Given low、standard、high fixtures，When 計算可進入 implementation/completion 的 Gate，Then 分別要求 plan；plan+acceptance；scope+design+acceptance，並套用 self/detached/max-three review policy；修改 fingerprint 後舊 approval 失效。

## AC-006: Git lifecycle
- Requirement: REQ-006
- Scenario: Given clean、dirty、detached、name-collision 與正常 base fixtures，When start run 與完成 phase，Then dirty/detached/collision 安全阻擋或回報，正常情境建立同 checkout run branch、base ref 不變並產生 scoped local commits，且沒有 push/PR/merge/switch-back。

## AC-007: ExecPlan restart
- Requirement: REQ-007
- Scenario: Given 已保存 plan、tasks、Gate 與 events 的 run，When host process 在任意 event boundary 重啟並 resume，Then reducer 重建等價 RunSnapshot、不重複 side effect，且 repo 只追蹤 canonical ExecPlan/必要 evidence。

## AC-008: Pending decision round-trip
- Requirement: REQ-008
- Scenario: Given agent 提出 PendingDecision，When host 以合法 option、自訂答案、取消、malformed 或 stale revision 回覆，Then 合法答案寫回同一 plan 並恢復 run，其餘維持 pending 且不推進 Gate/task。

## AC-009: Docs truth contract
- Requirement: REQ-009
- Scenario: Given fresh V2 checkout，When agent 從 `AGENTS.md` 導航並執行 docs checker，Then 可在 bounded hops 找到 architecture/product/reliability/security/quality/ExecPlan authority，無 `wiki/` 或 baseline truth 依賴、無 broken links 或重複 canonical topic。

## AC-010: V1 export determinism
- Requirement: REQ-010
- Scenario: Given current v1 Git tree，When 兩次執行 `export-v1`，Then 輸出 byte-stable index、記錄 21 work items 與 411 evidence files、列出不可轉換項，且未修改 v1 input；V2 commands 對 v1 mutation request 回明確 unsupported。

## AC-011: CLI/schema contract
- Requirement: REQ-011
- Scenario: Given 每個 public CLI verb 與五個 public schema 的 golden fixtures，When 執行 success、unknown field、invalid version 與 malformed input cases，Then JSON envelope、exit code、schema version與 error code 穩定且 fail closed。

## AC-012: Rich client state coverage
- Requirement: REQ-012
- Scenario: Given scripted app-server event transcript，When Webview 走過 connect、run、plan、diff、tool approval、decision、verification、review、usage、interrupt 與 error，Then 每個狀態有可操作且可存取的 UI，stale/projection 不被標為 authoritative。

## AC-013: Verification safety parity
- Requirement: REQ-013
- Scenario: Given read-only、writer DAG、release-only、undeclared write、timeout、stale digest 與 changed-path fixtures，When 執行 `verify`，Then selection/closure/stage deterministic，writers serial、shell disabled，只有 current zero-exit declared-effect observation 可 gate-eligible。

## AC-014: Bounded independent review
- Requirement: REQ-014
- Scenario: Given standard/high diff 與 advisory/critical findings，When 執行 review loop，Then reviewer context 與 implement turn 分離，standard 產生一次 verdict，high 最多三輪 fix/reverify；critical unresolved 或第四輪需求轉為 host blocker。

## AC-015: Clean 2.0.0 package
- Requirement: REQ-015
- Scenario: Given release candidate，When 執行 repository/package contract，Then 所有 public version 為 2.0.0，VSIX 由 build artifact 產生但不被 Git 追蹤，HEAD 不含 v1 raw ledger/Wiki/legacy companions/clipboard workflow，且 v1 只剩 export 說明與 index artifact。

## AC-016: Adversarial authorization
- Requirement: NFR-001
- Scenario: Given unknown methods、forged roles、stale revisions、path traversal、symlink escape 與 scope violations，When 經 CLI、MCP、app-server adapter 或 Extension 發送，Then 在任何 repository/process mutation 前一致拒絕並留下 bounded diagnostic。

## AC-017: Deterministic state
- Requirement: NFR-002
- Scenario: Given 相同 ordered transcript、crash-before/after-write injection 與重複 delivery，When reducer/storage 重播，Then canonical snapshot/hash 相同、partial record 不 current、重複 event 不重複 commit/verification/tool side effect。

## AC-018: Telemetry privacy
- Requirement: NFR-003
- Scenario: Given 含 prompt-like text、secret patterns、oversized diagnostics、unavailable usage 與合法 counters 的 events，When 寫入 metrics/log，Then secrets/prompts/reasoning 不落盤、超限拒絕或截斷有標記、usage unavailable 保持 null 且不推估。

## AC-019: Mechanical architecture checks
- Requirement: NFR-004
- Scenario: Given 正常 repo 與故意造成 oversized module、反向 dependency、長 root instruction、schema drift、broken docs link、untraced AC 的 fixtures，When 執行 `check`，Then 正常 repo 通過且每個違規以具體 path/code fail。

## AC-020: UI evidence bundle
- Requirement: NFR-005
- Scenario: Given Windows VS Code release walkthrough，When 執行 keyboard/ARIA/focus/forced-colors/reduced-motion 與關鍵狀態流程，Then tests 通過並產生 bounded DOM/accessibility report、log 與 screenshot，且 artifact 有 run/commit/protocol provenance。

## AC-021: Certification boundary
- Requirement: NFR-006
- Scenario: Given Windows certification report 與非 Windows environment metadata，When 生成 release status，Then 只有已跑完整矩陣的 Windows x64／VS Code 標示 certified，其他平台標示 unverified；core adapter tests 不依賴反斜線或 shell string。

## AC-022: Recovery drill
- Requirement: NFR-007
- Scenario: Given phase commits、V1 export、base ref 與注入的中途 failure，When 執行 recovery inspection，Then 可指出最後 current phase、diff、evidence、export 與回復 commit，base ref 未動且系統未自動 reset/merge/push。

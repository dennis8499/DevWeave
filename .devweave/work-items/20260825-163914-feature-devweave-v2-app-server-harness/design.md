# 系統設計：DevWeave V2 app-server harness

<!-- DEVWEAVE:artifact=design version=1 work=20260825-163914-feature-devweave-v2-app-server-harness -->

## 設計摘要

選定方案是「Codex app-server rich client + 單一 Python RunService + project-scoped MCP」。VS Code Extension 直接管理 Codex app-server 的 stdio JSONL connection；Python `RunService` 是 workflow、ExecPlan、Gate、Git、verification 與 review policy 的唯一 authority；MCP、CLI 與 Extension host bridge 都是 adapters，不擁有第二份 lifecycle state。

設計只使用 app-server 的 stable API subset：`initialize`／`initialized`、thread start/resume/read、turn start/steer/interrupt、item/turn/thread notifications、native command/file approvals、`review/start`、`mcpServerStatus/list` 與 MCP startup status。`initialize.capabilities.experimentalApi` 固定省略或為 `false`；WebSocket、dynamic tools 與 `tool/requestUserInput` 不在 Interface。官方文件目前仍將 app-server command 整體標示為 experimental/unsupported for production，因此 V2 對它採 exact executable/version/schema provenance、Windows preview certification 與 fail-closed capability probe，不把「stable API subset」誤稱為上游 production guarantee。

### Deep modules

| Module | 小型 Interface | 隱藏的 Implementation | Seam／Adapter 與 dependency 類別 |
| --- | --- | --- | --- |
| Python `RunService` | `inspect`、agent command、host command、`verify` | schema、revision、Gate、scope、decision、task、Git、commit、review loop、evidence 與 storage reconciliation | 外部 seam 是 typed command envelope；filesystem/Git/process 為 local-substitutable ports，production 與 in-memory/disposable-repo adapters 都是真實 adapters |
| TypeScript `CodexAppServerSession` | `connect`、`request`、`notify`、`events`、`close` | CLI resolve、child-process lifecycle、JSONL framing、request correlation、handshake、timeout、stderr diagnostics、protocol validation 與 restart | true external process seam；production child-process transport + transcript transport |
| TypeScript `WorkspaceController` | `startRun`、`resumeRun`、`steer`、`interrupt`、`decide`、`cancel`、state subscription | Host authentication、RunService/app-server coordination、approval broker、event reduction、reconnect 與 UI projection | Extension host seam；production VS Code adapters + in-memory controller harness |
| Python `VerificationEngine` | `plan`、`run`、`read` | executable resolution、DAG、changed-path selection、writer barrier、snapshots、eligibility、metrics、redaction | process/filesystem/Git ports；production subprocess + deterministic fake adapters |

刪除測試顯示這些 seams 有深度：若移除 `RunService`，Gate、revision、Git、verification 與 capability rules 會散落在 CLI/MCP/Extension；若移除 `CodexAppServerSession`，protocol correlation、framing、restart 與 validation 會散落在 controller/UI。相反地，MCP/CLI/host adapters 本身應保持薄，測試以 deep-module Interface 為主，不保留重複測試內部 helper 的 shallow suites。

### 長期不變量

- 每個 run 恰有一份 canonical typed ExecPlan；其他 snapshot、event、log、thread handle 與 UI projection 都可重建且不可凌駕 ExecPlan。
- 每個 mutation 帶 `run_id` 與 `expected_revision`，先驗 role/capability、phase、Gate、scope 與 path containment，再做 side effect；未知輸入 fail closed。
- Agent MCP 永遠不能 start/resume/cancel run、resolve decision、approve/reject Gate 或取得 host capability。
- Codex turn 在計畫 Gate 前使用 read-only sandbox；進入 implementation 後才使用 workspace-write、network disabled，並由 V2 guard 再限制 current task/scope。
- Base branch ref 不移動；DevWeave 不 push、PR、merge、reset 或自動切回。Unrelated working-tree change 會阻擋 DevWeave commit，而不是被納入或清除。
- Raw reasoning、完整 prompt 與 secrets 不進 DevWeave persistence。`item/completed` 是 app-server item authority；deltas 只供即時 UI。
- Tracked config 不保存絕對 executable path 或 executable hash；每次 run/verification 解析後把 provenance 放入該次 bounded evidence。

## 選項比較

### Workflow transport

1. 延伸 v1 filesystem snapshot + clipboard handoff：改動小，但仍需人工複製、Refresh 與兩套狀態推斷，無法直接承接 thread/turn/events/approvals。拒絕。
2. 使用 Codex SDK：適合 CI 或自動化 job，但官方指引把 rich-client deep integration 導向 app-server；若用 SDK，仍需自行建立 conversation history、approval/event bridge。拒絕。
3. 使用 app-server stdio JSONL：能直接取得 authentication/session、thread/turn、streaming item、diff、plan、usage、review 與 approvals。選定；代價是上游 app-server maturity 仍為 experimental，必須 version/schema pin、capability probe 與明確 certification boundary。

### Workflow authority

1. Extension、MCP 與 CLI 各自保存狀態：call path 短，但 Gate/revision/scope 很快漂移，安全規則需三份。拒絕。
2. 全面改寫成 TypeScript engine：可少一個 child process，但會丟棄已驗證的 Python policy/verification 演算法，且 MCP、CLI、test fixtures 需一起重建。拒絕。
3. Python `RunService` deep module + 薄 adapters：保留 stdlib、policy 與 disposable-repo test leverage；Extension 只透過 private authenticated host bridge 呼叫。選定。

### State 與 V1 相容

1. V1/V2 dual-read：看似平滑，但每個 Gate、evidence、task 與 knowledge rule 都需雙路徑，長期形成 migration 永久層。拒絕。
2. 將 V1 raw ledger直接搬進新 schema：會把 21 個歷史 lifecycle 與 411 個 evidence payload 變成 V2 runtime burden。拒絕。
3. Canonical V2 ExecPlan + deterministic V1 export/index：V2 不讀 V1，原始資料由 base commit/Git history 回復。選定。

### User decision surface

1. 依賴 experimental `tool/requestUserInput`：UI 整合直接，但會把 DevWeave Gate 綁到 experimental API，且 MCP side-effect elicitation與產品決策混在一起。拒絕。
2. DevWeave `PendingDecision` + host-only `decision_resolve`：agent 只能提出問題，Extension 呈現並由 host 回答；Gate 另走 `gate_decide`。選定。

`Design It Twice` 的多 sub-agent interface exercise 未啟動：使用者已在 G1 前的 Plan Mode 明確選定 app-server primary、clean cutover、risk gates、Git 與 docs strategy；G2 只把這些已回答決策落成內部 seams，沒有重新開啟產品方向選擇。

## 介面與資料流

### Repository layout

```text
.agents/skills/devweave/
  SKILL.md                         # 唯一 surfaced workflow skill
  references/                     # phase-specific progressive disclosure
  scripts/devweave.py             # thin V2 launcher
  scripts/devweave_v2/            # Python package; domain/application/adapters
.codex/config.toml                 # required project-scoped MCP, exact enabled_tools
.codex/hooks.json                  # V2 phase/scope guard
.devweave/project.json             # tracked schema-v2 project/verification config
.devweave/runtime/                 # ignored locks, events, logs, thread handles, UI evidence
docs/
  index.md
  product.md
  design.md
  reliability.md
  security.md
  quality.md
  generated/
  exec-plans/active/*.json         # one canonical typed ExecPlan per active run
  exec-plans/completed/*.json
  exec-plans/tech-debt.md
ARCHITECTURE.md
AGENTS.md                          # bounded map, not handbook
```

V1 transition 期間，現有 CLI/core 與本 work item 可暫時保留供 legacy G3 使用；release finalizer 只執行已驗證 manifest：把 transition plan 投影到 `docs/exec-plans/completed/`、移除 tracked v1 raw work-items/baseline/Wiki/companions/VSIX、切換 thin launcher，最後用 V2 `check`/tests 驗證 final tree。Finalizer 不重寫 Git history。

### Public schemas

所有 schema 都有 `schema_version: 2`、strict required fields、bounded strings/arrays、canonical JSON 與 unknown-field rejection（app-server inbound envelope除外，為 forward compatibility 可忽略未知非關鍵欄位）。

- `RunSnapshot`：`run_id`、`revision`、status/phase/risk、base/run branch、required/current Gates、task summary、pending decision、verification/review summary、thread/turn connectivity、blockers 與 timestamps。
- `RunPlanDraft`：goal、scope、non-goals、requirements/acceptance、decisions、immutable task definitions、verification plan、risk rationale；只可在對應 plan/design Gate 前 replace。
- `PendingDecision`：id、question、2–3 options、recommended option、`allow_other`、blocking task、created revision/status；不保存 host UI transcript。
- `VerificationPlan`：command id、argv tokens、cwd、affected paths、writes/outputs、dependencies、timeout、risk profiles、expected exit、release policy 與 definition digest；不含已解析絕對 path/hash。
- `ReviewFinding`：id、severity、summary、paths、requirement/AC/task links、status 與 round；不保存 reviewer reasoning。

Canonical ExecPlan 保存批准過的 workflow truth；`.devweave/runtime/<run-id>/` 保存 thread id、active turn、request correlation、event cursor、bounded logs 與 lock。Runtime 遺失時，host 從 ExecPlan 開新 thread並注入 current plan/context，不把 conversation continuity 當作 workflow truth。

### Python RunService Interface

Agent facade 只接受八個 operation：

| Operation | 可做 | 明確不可做 |
| --- | --- | --- |
| `run_inspect` | 取得 bounded RunSnapshot | 任意檔案讀取或 mutation |
| `context_read` | 依 docs index/allowlist 讀取 current task 所需 context | traversal、secret/runtime/raw reasoning |
| `plan_save` | 在 plan/design Gate 前 replace RunPlanDraft | approve Gate、改 base/branch、Gate 後偷改 task |
| `decision_request` | 建立一筆 PendingDecision 並阻擋 task | 自己回答或選擇 host decision |
| `task_update` | 依 immutable task id 更新 lifecycle/progress | 改 task definition、跳過 dependency/Gate |
| `verification_run` | 執行 frozen/declared VerificationPlan | 任意 argv、shell、未宣告 write |
| `verification_read` | 讀 bounded evidence/review projection | raw secret/log overflow |
| `completion_request` | 表示 agent 認為 ready，建立 host review request | complete/commit acceptance/merge |

Host facade 只有 `run_start`、`run_resume`、`decision_resolve`、`gate_decide`、`run_cancel`。Extension 啟動 private `internal-host-serve` child process後，以只存在兩個 process memory/stdin 的隨機 challenge-response token建立 session；token不放 argv、environment、檔案或 log。MCP adapter使用不同 entrypoint與 facade，client supplied `role=host` 永遠無效。

公開 CLI 只有：

- `doctor [--codex-path <absolute>]`
- `inspect [--run <id>]`
- `check`
- `verify --run <id> [--profile low|standard|high] [--path <relative>]`
- `export-v1 --source-ref <git-ref> --output <directory>`
- `mcp-serve`

JSON stdout 是唯一 machine output；human diagnostics 走 stderr。成功/失敗使用穩定 envelope與 machine error code。

### App-server Interface

`CodexAppServerSession` 使用 `spawn(resolvedCodex, ["app-server"], { shell: false, cwd: repo })`，逐行解析 stdout JSON，stderr只進 bounded/redacted diagnostic。每連線只送一次 `initialize`，`clientInfo.name = "devweave_vscode"`，不 opt in experimental API，成功後送 `initialized`。

Outbound method allowlist：`thread/start`、`thread/resume`、`thread/read`、`turn/start`、`turn/steer`、`turn/interrupt`、`review/start`、`mcpServerStatus/list`、`config/mcpServer/reload`。Inbound reducer接受對應 response/error與 `thread/*`、`turn/*`、`item/*`、`serverRequest/resolved`、`mcpServer/startupStatus/updated`、`configWarning`、`warning`、`error`。`item/completed`覆蓋 delta projection；reasoning item只保留 presence/duration/status，不保存或 render `content`。

每個 request 有 monotonic id、method-specific timeout 與 pending map；process exit會拒絕所有 pending calls。JSON line、aggregate output、diff、diagnostic與 UI buffer都有上限；unknown event不造成 crash，只產生 bounded `unsupported_event` diagnostic。Doctor 使用該 Codex executable執行 version probe與 `app-server generate-json-schema` 到 runtime temp，驗證所需 descriptors並保存 bundle hash；缺少 capability時不建立 run/branch。

### MCP project configuration

`.codex/config.toml` 以 `[mcp_servers.devweave]` 設定 repository-local stdio command，`required = true`，`enabled_tools` 精確等於八個 agent operations，startup/tool timeout bounded。Server tool annotations正確標示 read-only與 side-effect；但安全 authority仍是 RunService，而不是 annotation或模型自律。Thread start/resume前，host用 `mcpServerStatus/list` 確認 DevWeave server、exact tool set與 auth/startup current；required server失敗時不降級為無治理 turn。

### Gate、state 與 review

| Risk | Required Gates | Review |
| --- | --- | --- |
| low | `plan` | implement turn self-review；verification current後才可 acceptance completion |
| standard | `plan`、`acceptance` | 一次 `review/start` detached review |
| high | `scope`、`design`、`acceptance` | detached review → bounded fix/reverify，最多三輪 |

Risk可由 engine依 scope、security/data/schema/build/Git policy向上提升；任何 downgrade都需 host明確決議與 rationale。Gate approval綁定 ExecPlan revision及 canonical fingerprint；修改 risk/scope/decision/task definition/verification plan會使受影響 Gate與 evidence stale。High review以 `delivery: "detached"`，target使用 base branch或明確 commit；`exitedReviewMode`文字經 bounded parser轉成 ReviewFinding，不保存 reasoning。第三輪仍有 critical/unresolved finding時建立 blocker，不能自動進第四輪。

狀態主路徑：

```text
preflight → draft → awaiting required planning Gate(s) → implementing
          → verifying → reviewing → awaiting acceptance → completed
          ↘ blocked / cancelled
```

`PendingDecision`會把受影響 task設為 blocked，但不改整體 approved plan；host resolution以 expected revision寫回 decision record。取消/逾時/malformed/stale answer保留 pending。

### Git transaction

`run_start` 先確認 repository root、non-detached base、tracked/staged/untracked皆乾淨（ignored除外）、branch name未衝突，再以 argument array建立 `devweave/<run-id>-<slug>`。ExecPlan記錄 base branch/ref與 run branch。Scope/design Gate及每個 vertical-slice task完成後，commit coordinator只 stage task declared paths與ExecPlan；若存在未歸屬 diff、submodule、conflict、symlink escape或 base ref漂移就阻擋並交給 host。Commit message含 run/task id。DevWeave不執行 remote或 destructive Git command。

### Verification 與 observability

VerificationEngine沿用並重構 v2 evaluator語意：argv array、`shell=False`、runtime executable resolve/hash、bounded timeout、DAG closure、changed-path selection、release-only、serial writers、read-only parallel stage、pre/post filesystem+Git snapshot、declared output reconciliation與 engine-derived gate eligibility。Tracked `.devweave/project.json` 只保存 executable id/candidates與argv，不保存 machine-specific absolute path/hash。

Evidence保存 command/plan/source/input/output digest、exit/status、duration、selected/skipped/closure、changed paths、bounded stdout/stderr摘要與usage availability。數字和payload沿用明確上限；未知 usage保留 null，不由 bytes推估。App-server raw prompts、reasoning與secret-like value在adapter入口即丟棄或redact。

Extension release walkthrough為 connect、preflight failure、start、resume、plan、diff、Codex approval、PendingDecision、verification、detached review、interrupt、reconnect與error。自動產出 DOM/ARIA assertions、keyboard/focus/forced-colors/reduced-motion結果、bounded log與關鍵狀態screenshots；tracked report只保存hash、run/commit/Codex version/schema provenance，binary screenshots放ignored release artifacts。

## 失敗模式與回復

- Codex executable缺少/錯誤/版本或schema probe失敗：`doctor`回 blocker；不建立branch、ExecPlan或app-server process，不下載或fallback。
- App-server handshake timeout、malformed/oversized JSONL、unexpected exit：關閉process、reject pending requests、保存bounded diagnostic。若ExecPlan已存在，可由host重新preflight後 `run_resume`；thread handle存在則 `thread/resume`，否則由ExecPlan開新thread。
- Required MCP startup/tool set不符：thread start/resume fail closed；host可修復project config後呼叫reload/retry，不能繞過MCP繼續implementation。
- Stale revision、Gate fingerprint、task dependency或scope/path錯誤：mutation前拒絕並回current RunSnapshot；不做best-effort merge。
- Codex command/file approval越過current phase/task/scope：ApprovalBroker只提供decline/cancel並記錄diagnostic；eligible request仍需使用者explicit decision。
- Git dirty/unrelated diff或commit失敗：不stage/commit未宣告內容、不reset；保留working tree並建立host blocker。Base ref與既有commits提供回復點。
- Verification timeout、undeclared write、nonzero、stale digest或writer promotion失敗：evidence為ineligible，task/run停在verifying；writer candidate不得promotion。
- Process在atomic write前後crash：temp/partial file不current；restart以canonical ExecPlan revision與idempotent events重建，已記錄side-effect key避免重複commit/verify。
- Reviewer unavailable：standard/high均顯示blocked而不是假pass；high未解critical或第三輪後finding必須host處理。
- V1 export/finalizer失敗：base commit與run branch都保留，finalizer以manifest/hash idempotent重跑；不刪Git history、不自動reset。V1 raw可由記錄的base ref讀回。

回復策略不是自動rollback：每個phase/vertical slice commit是明確checkpoint，Extension顯示最後current commit與建議人工Git操作，但DevWeave本身不執行reset/revert/merge。Release finalizer只處理exact allowlisted legacy paths；任何hash/path不符即停止。

## 高風險分析

### Migration／遷移

`export-v1` 從G1記錄的base commit讀取Git objects，不掃描正在變動的working tree，因此deterministically匯出原有21個closed Work Items與411個evidence files，另列parse warning與source ref。V2不載入匯出資料。Transition work item在legacy G3完成後轉成一份completed ExecPlan；finalizer才移除tracked v1 work-items、baseline、Wiki、companions與VSIX。

### Rollback／回復

Base branch ref固定不動，所有交付只在run branch分段commit。任何階段可由使用者檢視/revert特定commit；DevWeave不自行reset。Clean cutover後若需V1 raw，使用export中的base ref或Git history；不承諾重新啟用V1 runtime。

### Security／安全

Host與agent採不同process entrypoint/facade；private host token只經child stdio記憶體交換。每個mutation都做role、revision、phase、Gate、scope、containment、symlink與command policy驗證。App-server前置階段read-only，implementation network disabled；未知method/field、shell string、arbitrary argv與host-role claim fail closed。Logs不保存prompt/reasoning/secret，approval UI顯示thread/turn/item與實際command/path。

### Compatibility／相容性

Public schema/CLI/Extension version一次升到2.0.0；V1只export，不dual-read。App-server只使用stable subset且不opt in experimental API，但上游command maturity仍為experimental，故Codex executable/version/schema hash成為certification provenance，unsupported version會阻擋。Windows x64／VS Code是唯一certified matrix；portable adapters不是其他OS通過宣告。

### Performance／效能

每workspace最多一個app-server session與一個host bridge；event reducer使用bounded per-thread/item maps及coalesced UI publish。JSONL line、diff、output、diagnostic、metrics、raw log與screenshot count都有上限。ExecPlan讀寫為單writer+optimistic revision；verification writers serial、read-only checks在barrier後依DAG平行。若大repo hashing超出budget，先以Git changed-path與streaming hash縮小輸入，不引入資料庫或background full index。

## 設計決策

## DEC-001: App-server stdio stable subset
- Requirements: REQ-001, REQ-002, REQ-012, NFR-006
- Decision: Extension直接spawn已驗證Codex CLI的`app-server` stdio JSONL，透過單一`CodexAppServerSession`使用stable subset，`experimentalApi=false`。
- Rationale: 官方將app-server定位為rich-client Interface；stdio具本機containment、簡單framing與child lifecycle ownership，最符合已選方向。
- Consequences: 可直接承接thread/turn/events/approvals/review；但需承擔上游experimental maturity，以version/schema probe與Windows certification限制風險。

## DEC-002: 單一 Python RunService 與雙 facade
- Requirements: REQ-003, REQ-004, REQ-011, NFR-001, NFR-004
- Decision: Domain/application規則只存在RunService；agent MCP與authenticated host bridge暴露不同facade，CLI是第三個薄adapter。
- Rationale: 將Gate、scope、revision、Git、verification與state locality集中，避免三個client各自推導。
- Consequences: Extension增加一個Python child process；但production/in-memory adapters形成真實test seam，Interface可跨callers重用。

## DEC-003: Canonical typed ExecPlan 與 ephemeral runtime
- Requirements: REQ-005, REQ-007, REQ-008, NFR-002
- Decision: `docs/exec-plans/{active,completed}/*.json`是唯一workflow truth；`.devweave/runtime/`只保存ignored/rebuildable process state。
- Rationale: 同時滿足agent legibility、Git traceability、crash recovery與不把transient event/log塞進HEAD。
- Consequences: Plan mutation較頻繁且需revision/atomic write；thread continuity遺失時以Plan重建，不保證相同conversation id。

## DEC-004: 風險自適應 Gate 與 bounded detached review
- Requirements: REQ-005, REQ-014, NFR-001
- Decision: low=`plan`+self-review；standard=`plan`+`acceptance`+一次detached review；high=`scope`+`design`+`acceptance`+最多三輪detached fix/reverify。
- Rationale: 將人力成本集中在不可逆/廣泛變更，同時使high-risk failure不會無限自動迴圈。
- Consequences: 同一public state machine需支援不同required Gate set；risk只能自動升級，降級需host rationale。

## DEC-005: 同 checkout run branch 與 scoped commits
- Requirements: REQ-006, NFR-007
- Decision: clean preflight後建立`devweave/<run-id>-<slug>`，每phase/vertical slice只commit declared paths，base ref固定且無remote/merge/switch-back。
- Rationale: 使用者明確選擇此Git ownership；小commit提供review/recovery checkpoint。
- Consequences: 開始時不能容納dirty repo；進行中unrelated edits會暫停DevWeave commit並要求host協調。

## DEC-006: 重構但保留Verification Policy v2 safety semantics
- Requirements: REQ-013, NFR-001, NFR-003
- Decision: 將policy/plan/executor/evidence拆成modules，保留shell-free、DAG、writer barrier、declared-effects與engine eligibility；executable只在runtime解析並記錄。
- Rationale: 既有安全語意已被測試，問題是monolith與machine-specific config，不是policy方向。
- Consequences: V1 frozen plan在transition期間維持；finalizer切到schema-v2 config後需再跑完整V2 contract。

## DEC-007: `docs/` 單一長期知識來源與單一 Skill
- Requirements: REQ-009, NFR-004
- Decision: Root instructions只做map；architecture/product/reliability/security/quality/ExecPlans/tech debt集中於docs；五個companion collapse成一個DevWeave skill的phase references。
- Rationale: 符合Harness Engineering的progressive disclosure與executable invariants，移除stale Wiki/baseline雙重truth。
- Consequences: V1 wikilink與companion invocation breaking；repository checker必須防止新雙重truth與broken navigation。

## DEC-008: Git-ref based V1 export 與 manifest finalizer
- Requirements: REQ-010, REQ-015, NFR-007
- Decision: Export從recorded base ref唯讀生成summary/index；legacy G3後以hash-bound allowlist finalizer完成tracked clean cutover。
- Rationale: 可精確保留21/411歷史摘要，又不讓active transition work污染計數或讓V2背負dual-read。
- Consequences: Raw detail只存在Git history；finalizer屬高風險release step，path/hash不符即停止並需post-cutover full check。

## DEC-009: Event-reduced rich UI 與 evidence-first accessibility
- Requirements: REQ-012, NFR-003, NFR-005
- Decision: UI由RunSnapshot + app-server event reducer投影；authority/stale明示，approval/decision分流；release產生DOM/a11y/log/screenshot evidence hash。
- Rationale: 使用者不再靠clipboard/Refresh，同時保留可機械驗收的觀察面。
- Consequences: Extension runtime可spawn受控process，安全面大於v1唯讀projection；必須有strict protocol/CSP/approval tests。

## DEC-010: 版本化、可探測、Windows-first protocol boundary
- Requirements: REQ-002, REQ-011, REQ-015, NFR-006
- Decision: DevWeave schema/product/Extension固定2.0.0；Codex/MCP在preflight協商/探測，tracked config不釘machine path，release只宣稱Windows x64/VS Code certified。
- Rationale: 上游protocol會演進且目前環境可能無Codex executable；顯式capability比猜測或silent fallback安全。
- Consequences: 真實app-server E2E是不可waive的release blocker；portable core tests不等於其他平台認證。

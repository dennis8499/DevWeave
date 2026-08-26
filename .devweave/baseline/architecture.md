# Architecture Baseline

此文件保存已驗收的系統邊界、介面與長期設計決策。由 DevWeave 工作項在 G3 前更新。

## System Context

Codex 透過 `.agents/skills/devweave/SKILL.md` 路由公開意圖；Router 在 pre-G2 mutation entry 的 `start`、`bind`、`revise` 或 bootstrap create 前確認 `request_user_input` host capability，未取得 capability 時停止並提示 Plan Mode，compatibility fallback 必須由使用者明確選擇。`devweave.py` 提供 JSON machine CLI；`devweave_core.py` 擁有 work locks、state、events、evidence、gate、bootstrap profile 與 Knowledge Review/plan currentness；`knowledge_core.py` 以 Python standard library 提供 Wiki reserved-starter preflight/bootstrap assessment、frontmatter、context records、coverage、canonical scaffold、source fingerprint、lint、snapshot 與 seal。單一 `.codex/hooks.json` PreToolUse hook 以 exact matcher `^(Bash|apply_patch|Edit|Write)$` 呼叫 `guard.py`，並依 host 使用 POSIX `command` 或 Windows `commandWindows` 從 Git root 定位同一 guard。五個 `.agents/skills/<companion>/` 目錄提供階段內工程方法，root `AGENTS.md` 是它們與唯一 DevWeave router 之間的 precedence interface。

## Boundaries and Interfaces

- `.devweave/work-items/`：machine lifecycle、artifacts 與 evidence；不得由 agent 直接編輯 JSON/JSONL ledgers。
- `.devweave/baseline/`：G3 接受的治理層 truth。
- `wiki/`：一般 Markdown 知識；G1 讀取，G2/implementation 唯讀，verification 僅允許 knowledge plan 精確 targets 與 coupled index/log。
- `.agents/skills/<companion>/`：由 `skills-lock.json` 追溯的 project-local upstream copies；只消費目前 phase context，產出必須回流 DevWeave artifact 或 evidence，不直接操作 machine ledger、Git 或 remote tracker。
- Product source、baseline 與 knowledge 各自具有 fingerprint。Wiki-only 變更不使 product evidence stale，但會使 G3 stale。
- Knowledge sources 固定為 1–5 個 repo-relative product paths；directory 以單次 Git listing 展開 tracked 與 non-ignored untracked files，再依排序後 current content hash。
- `init_project()` 先在 project lock 外檢查 Wiki，再於 lock 內重檢，成功補齊 Wiki 後才建立 project、baseline、cache 與 work-item control state；reserved conflict 不產生 partial control bundle。
- `knowledge bootstrap/review/context/plan/scaffold/seal` 都是唯一 router 下的 machine namespace；bootstrap 仍是 `kind: feature` 並沿用 G1/G2/G3/session binding，沒有第二個 Wiki state machine。
- High-risk G3 reviewer 由既有 DevWeave router 啟動 exactly once；Python engine 不 spawn Agent，只透過 machine-only `review record` 驗證固定 JSON、建立 additive `kind: review` evidence、report hash、current source/Git provenance 與 bounded raw log。不存在第二個 lifecycle、router、orchestrator 或平行 ledger。
- VS Code Extension 的 bootstrap recommendation 是 filesystem-only、non-authoritative projection；三個入口只經 `PromptComposer` 預覽/複製，engine output 才決定 create/resume/already-complete 與 gate currentness。

## Accepted Decisions

- 保持 schema version 1，knowledge settings/state 採 additive compatibility；只有新 Work Item 預設 `knowledge_review_required: true`，缺少 marker 的舊 active work 不新增追溯 blocker。
- `init/start` 非破壞性建立或採用 root `wiki/`；不相容同名內容 fail closed，交由 `doctor` 回報。
- `init/start` 對 missing、empty 或 custom-only Wiki 採 reserved-starter compatibility；只有 reserved starter file/directory 的錯誤 type 或 frontmatter 產生 `knowledge_conflict`。
- Bootstrap manifest 舊 entry 缺少 `existingPolicy` 時安全正規化為 `exact`；只有明確列出的 project、baseline、Wiki starter contract 可 `adopt-compatible`，未知 policy/kind 在任何 write 前 fail closed。
- 每個新式 Work Item 都必須有 current `promote|no-update` review；產品 source fingerprint 改變會 invalid review 並清空 plan。`no-update` 僅允許非 bootstrap、無 affected page、無 Wiki diff且 rationale 非空。
- Bootstrap readiness 要求 active/sourced/current 的 overview、architecture 與 module；bootstrap G3 必須 upsert 三至五個內容頁、零 product diff、零 delete，並同步 index/log/seal。既有 Wiki 超過五頁不影響 already-complete 判定。
- Canonical scaffold 支援九種內容型別，只允許 planned new upsert、合法 type directory 與 1–5 sources，採 exclusive no-overwrite placeholder create；seal 拒絕 placeholder、template token、invalid source 與 critical lint。
- Critical lint、undeclared/unchanged targets、未刷新 affected pages 或 log rewrite 阻擋 G3；其他 stale/orphan/semantic findings 為 warnings。
- Hook 是 Codex guardrail 而非 OS sandbox，G3 必須重新 reconcile 完整 Wiki diff。
- PreToolUse 採精確 `^(Bash|apply_patch|Edit|Write)$` matcher、單一 command handler、30 秒 timeout 與 status message；POSIX 使用 `python3 -X utf8 -B`，Windows handler 先以 `[Console]::InputEncoding`/`[Console]::OutputEncoding` 設定 .NET UTF-8，且不依賴 shell-scoped `$OutputEncoding` 變數，再使用 `powershell.exe` 呼叫 `py -3 -X utf8 -B`；兩者都從 `git rev-parse --show-toplevel` 解析 repository root。`doctor` 以 bounded、read-only launcher probe 驗證 Git root 與 nested VS Code terminal cwd，並把 launcher failure 與 guard policy deny 分開呈現。
- Companion Skills 採精確 allowlist 與未修改的 project-local copies；不安裝 Matt Pocock 的 setup/spec/ticket/implement orchestration。Instruction conflict 由 root policy 解決，upstream 更新必須建立新的 DevWeave feature。

## DevWeave Control Center VS Code Extension

- `vscode-extension/` 是 TypeScript Extension Host、vanilla Webview 與 esbuild bundle；Python DevWeave engine、JSON contract、work state、events、evidence、baseline 與 Wiki 仍是權威來源。
- `WorkspaceSnapshotReader` 只使用 VS Code workspace file API 讀取 project/work artifacts、evidence、events、baseline、Wiki、hook 與 skill metadata；不呼叫 Python、shell、Git、外部網路或 repository write API，也不自行重建 fingerprint。
- `BootstrapInstaller` 是受控的唯一 bootstrap write seam；它接收 build-time source-derived bundle 與 workspace filesystem adapter，集中執行 manifest path containment、SHA-256/byte-length integrity、parent/symlink/type preflight、same-byte adoption、idempotence 與 write-failure rollback。
- `bootstrap-compat.ts` 是 project/baseline/Wiki semantic contract 的單一 deep module；`BootstrapInstaller` 與 `WorkspaceSnapshotReader` 共用 normalized `existingPolicy`/`compatibility` metadata 與 validator，避免 Extension 顯示與實際寫入結果分歧。
- `VscodeBootstrapWorkspace` 僅透過 VS Code `workspace.fs` 寫入固定 manifest destinations；`ExtensionController` 只負責 workspace root、native modal confirmation、installer invocation、snapshot refresh 與 result reporting。既有合法 `project.json` 或 critical diagnostic 不會觸發自動重建。
- `esbuild.mjs` 從 repository 的 DevWeave skill、hook 與 starter templates 產生 VSIX 內 `dist/bootstrap/manifest.json`，bundle version 直接讀取 `package.json`；每個 source 都有 byte length/SHA-256，七個資料型 bootstrap destinations 明確宣告 semantic compatibility，其餘 controls 維持 exact。Runtime 不下載、不執行 source，也不依賴 Codex Chat、Python、shell、Git 或 network 完成 bootstrap。
- `PromptComposer` 是唯一 action seam，將 `ActionIntent` 轉成 deterministic、repo-relative、sanitized `PromptBundle`；optional `PlanModeGuidance` 只含 `required` 與 `stage`，不改變 `chatText`。Webview 只能經 `previewAction` 顯示預覽，再由使用者確認 `copyAction` 到 Codex Chat。Extension 不直接執行 mutation，也不提供 host mode adapter。
- `PreviewGate` 是純 Extension host module；copy ticket 綁定 panel identity、typed intent、prompt bundle、snapshot revision 與一次性 consume。Host 只接受 matching current ticket，Refresh、selection、initialization 或 snapshot update invalidate stale tickets；clipboard failure 只允許同一 ticket safe retry 一次。Host-launched `actionPreview` 傳回相同 intent/bundle/revision，`copyNextAction` 不得 bypass preview。
- Control Center 的 Wiki scheduler 將 query/type/show-all 結果實際 mount 到 `#wiki-results`；五個區域以 tab/tabpanel `aria-controls`/`aria-labelledby`、roving tabindex、方向鍵/Home/End 與 focus restore 實作。主要 CTA、native modal action、error、readiness 與 empty-state 使用繁體中文，technical command names 保留於 code label。
- Control Center 對 high-risk acceptance 投影 `Independent Review` readiness：missing/unavailable/advisory 為 attention，critical 為 not-ready，passed 且 source current 才為 ready；Extension 不啟動 Agent、engine、shell、Git、network 或 lifecycle mutation。
- Activity Bar TreeView 提供 repository/work-item navigation；Dashboard/Webview 提供 welcome、doctor、phase/gate、task/evidence、Wiki-first、acceptance 與唯讀 audit projection。多 work item 必須明確選取，不以第一筆資料默選。
- UI 使用 VS Code theme tokens、Codicons、CSP、ARIA/focus、high-contrast、reduced-motion 與非色彩單獨狀態表達；主要內容保持不透明，僅在控制項使用輕微透明效果。
- `extension-typecheck`、`extension-tests`、`extension-package` 與 `extension-smoke` 透過 DevWeave command profiles 管理；Extension 不提供 branch、commit、push、PR、Marketplace release、版本比較或還原。0.2.3 package verifier 只讀取 current VSIX，並對 package／bundle version、root/embedded source-derived hook、58 個 bootstrap files、119 個 VSIX entries、required entries、每個 bundled source 的 byte length／SHA-256 及 current artifact SHA-256 fail closed；既有 0.2.2 與 0.2.1 artifacts 保留，其他 VSIX 不屬於輸入或回復條件。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

Companion Skills provenance: `20260802-215810-feature-matt-pocock-skills`（待 G3 核准）。

Control Center provenance: `20260803-090218-feature-devweave-control-center-vs-code-extensio`（待 G3 核准）。

Bootstrap provenance: `20260803-112312-feature-vs-code-devweave`（待 G3 核准）。

Codebase LLM Wiki provenance: `20260803-161041-feature-codebase-llm-wiki`（待 G3 核准）。

Independent Review provenance: `20260804-122803-feature-g3-review-agent`（待 G3 核准）。

## DevWeave V2 app-server architecture candidate（等待 G3）

- V2 採 `Extension/Webview -> authenticated host bridge -> devweave_v2 application/core -> storage/git/verification adapters` 的單向邊界；agent 僅經 project-scoped MCP 進入受限 facade，host-only mutation 不會出現在 MCP discovery。
- 實際相容性探測以 Codex CLI `0.149.1` 完成；其 generated app-server schema 含 291 個 JSON files。實作已依真實 protocol 對齊 thread-scoped MCP inventory、object-shaped tool map、`thread/start` sandbox enum、`turn/start` sandbox policy、`turn/steer.expectedTurnId`、`reviewThreadId`、nested thread/turn events、`item.review` 與 `tokenUsage.total`。
- MCP `tools/list` 僅接受缺省/null cursor 與合法 `_meta`，未知欄位、非 null cursor 或 malformed metadata 均 fail closed；實際 app-server thread probe 已看到且只看到八個 DevWeave tools。
- Thread start/resume/reconnect 與每個 turn 都強制 `approvalPolicy=untrusted`、`approvalsReviewer=user`，避免 machine-level `auto_review` 先於 client policy 核准。Detached review 優先使用 `exitedReviewMode`；目前 alpha CLI 未送出該 item 時，只接受 `review/start` 回傳之 exact reviewer thread/turn 的 authoritative `agentMessage`，並要求同一 turn `completed`。
- Task scope 同時檢查 lexical 與 canonical repository-relative path；host 在 branch/start journal 前做 repository-aware validation，Extension 在 sandbox root 與每次 file approval 重新解析實體路徑，因此 NTFS 8.3 short name、symlink/junction、protected authority ancestor 與 repository escape 都 fail closed。
- `ExecPlan` 是唯一 canonical run authority；event/process/cache/thread state 位於 ignored runtime storage，可由 ordered events 重建。Canonical serialization、atomic replace/append、revision/mutation idempotency 與 scoped local phase commits共同提供 restart/recovery boundary。Acceptance 若在 completed state replace 後、archive move 前崩潰，authority-locked recovery 會先冪等完成 active-to-completed placement，再建立或驗證唯一 checkpoint commit/ref/digest/final journal。
- Controlled verification 使用 `shell=False`、固定 argv/cwd、runtime executable provenance、DAG/stage、declared effect reconciliation 與 per-command `env_allowlist`；只有 baseline OS variables 與明確允許名稱可傳入 child process。
- Live certification 將 runner 到 OpenAI Codex 服務的 outbound transport 與 Codex tool sandbox 分開治理：前者只在使用者明確 opt-in 且提供 verified executable 時開啟；後者固定 read-only、network disabled、`approvalPolicy=untrusted`、`approvalsReviewer=user` 並拒絕所有寫入。Harness 使用 global operation budget、較短 cleanup timeout 與 bounded/redacted phase diagnostics，讓 transport denial 能在 executor timeout 前 fail closed。
- Breaking finalizer 只接受 current manifest hash，並在任何 path/hash drift 時停止。主工作樹在 G3 前刻意維持 V1 transition authority；current suite 已證明 public-check fixture、architecture與 finalizer contract，exact finalized main tree仍須在 G3 後通過 public `check`且不得依賴被刪除的 V1 truth。

V2 candidate provenance: `20260825-163914-feature-devweave-v2-app-server-harness`（等待 G3 核准與 finalizer cutover）。

## Skill Governance Overlay

- DevWeave 仍是唯一 SDLC router；`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling` 與 `tdd` 是唯一五個 project-local companion allowlist，僅提供 current phase method，不建立第二套 lifecycle。
- `writing-great-skills` 是 maintenance-only Skill：可協助維護 Skill instructions，但不屬於 companion allowlist、Extension bootstrap bundle 或 product SDLC routing。
- 五個 companion 是保留 upstream `source`、`skillPath` 與 `computedHash` 的 local optimization overlay；`skills-lock.json` 是 provenance authority，最佳化文字不冒充 upstream release。
- Skill completion 以可檢查的 phase boundary、public seam、decision return、evidence、metadata/invocation policy 與 explicit completion criterion 為治理契約；不新增 public CLI、JSON schema、router、state、ledger 或 Git 操作。

## Verification Policy v2 Architecture

- `command_policy.py` 是 Guard、`verify --command`、`verify --profile`、Doctor、command mutation 與 G3 的唯一 policy evaluator。其輸入綁定 Work Item、phase、gate、session、command definition、argv/cwd、writes/outputs、affected paths、release stage、dependency closure 與 current project policy digest；unknown/ambiguous shell input fail closed。
- G2 approval 以同一 atomic state path 凍結唯一 Effective Verification Plan，保存 plan ID/digest、project policy digest、每個 command definition digest、required/selected/skipped/not-applicable、dependency closure、stage、write/exclusive policy、expected exit codes 與 gate eligibility policy。Runner 與 G3 不重建第二份 required set。
- Configured verification command 只能經 DevWeave controlled executor：trusted executable/hash、固定 argv/cwd、`shell=False`、bounded timeout、sanitized environment、前後 snapshot、output reconciliation 與 evidence recording。`writes != none` 在 temporary candidate 內 serial 執行，candidate fingerprint 凍結後才允許 writes:none parallel stage；shared output boundary 自動 exclusive。
- Evidence 是 engine-derived observation。只有 current plan/project/command/source fingerprints、controlled executor、zero-only formal success、無 timeout/error/undeclared effect 且 postcondition/promotion 成功時才可 `gate_eligible=true`；expectation/reproduction/diagnostic/failed evidence 不得作 G3 proof。Policy mutation 經 typed core path 使 active plan、gate 與受影響 evidence deterministic stale。

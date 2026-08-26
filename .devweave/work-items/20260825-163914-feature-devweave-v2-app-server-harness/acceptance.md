# 功能驗收：DevWeave V2 app-server harness

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260825-163914-feature-devweave-v2-app-server-harness -->

## 驗證範圍與來源

- Risk/profile：`high`／feature；G1 與 G2 已由使用者核准，human G3 尚未核准。
- Immutable base ref：`3662d8622b46a1cab6931da988db3c4280def783`。
- Scope reconciliation：`WAIVER-001` 只允許 exact `VERSION`；該 shared 2.0.0 marker 已由核准的 TASK-001／REQ-011／AC-011／AC-015 要求，但在 G1 machine path list 中漏列，waiver 不涵蓋任何其他 path。
- Current product source HEAD：`a6641b5719caa0bdcb4b2e2046ff8ca89b98f500`；source fingerprint：`21a3dcfb1ea4a25b836f02f4f61ca03389de41457fb3b554b0edb77a7c11baba`。`EVID-125` 至 `EVID-136` 全部綁定此 anchor；其後只允許 engine-owned evidence、legacy baseline/acceptance/Wiki governance，若 product source（包含 generated cutover manifest）再變更則必須重跑 current evidence 與 formal review。
- Codex provenance：CLI `0.149.1`，executable SHA-256 `a395030b56b126f608f2403036dddb654a9c063213e9c2b5f85d954cf490ebe6`，同目錄 `codex-code-mode-host.exe` SHA-256 `8f98cc7aa079b51dbfbb16a8e655a468a9c37c1cd23e22422c10cdfd6cace543`；291 個 generated schema files，schema SHA-256 `def4a7e9c01d3eaf697ad5a8ada283e6733c9b54892bc4e6928eb1132320d85a`。Doctor 在任何 process call 前要求完整 CLI distribution，缺 companion 時 fail closed。
- UI evidence：9/9 assertions、1 screenshot（155,956 bytes）；report 綁定 run、current HEAD、Codex version 與 schema hash，report SHA-256 `b40a3b3dc7b90b01b7708376377a7ba98b8f190134077e44d680b106cff77de6`、screenshot SHA-256 `c5a766d0691aacbafc30b7596bb820a6470b82e33e16968924f3d363b94ce839`，bounded log 中 secret 已 redacted。

## 驗證矩陣

狀態定義：`通過` 代表目前已有對應的 mechanical/rehearsal evidence；`阻擋` 代表不可用 mock 取代的 release evidence 尚缺；`G3 待切換` 代表 disposable-clone proof 已通過，但主工作樹必須等 human G3 才可執行 breaking finalizer。

| AC | Tasks | 狀態 | Evidence / 結果 |
| --- | --- | --- | --- |
| AC-001 | TASK-007, TASK-012 | 通過 | Scripted lifecycle 與真實 Codex stdio E2E 均通過：stored thread start/read/resume/delete、model turn、steer/interrupt、native approval request/client decline 與 authoritative completion 全部完成。 |
| AC-002 | TASK-006, TASK-012 | 通過 | Doctor 以實際 absolute Codex path 完成 version/executable/companion/schema provenance；missing/not-file/missing-companion/version/schema failure fixtures 均在副作用前 fail closed。 |
| AC-003 | TASK-005, TASK-012 | 通過 | MCP transcript/adversarial tests 通過；real app-server thread inventory 只列出 exact 8 tools，cursor/`_meta`/unknown-field validation 與 scope guards 已對齊實際 protocol。 |
| AC-004 | TASK-005, TASK-006, TASK-008 | 通過 | MCP discovery 無 host-only aliases/passthrough；authenticated host bridge、forged role/replay/agent-host mutation tests 通過。 |
| AC-005 | TASK-002, TASK-008 | 通過 | Low/standard/high Gate、fingerprint invalidation、self/detached/max-three review policy tests 通過。 |
| AC-006 | TASK-003, TASK-012 | 通過 | Actual run branch 為 `devweave/20260825-163914-app-server-harness`；scoped phase commits存在，base ref 未移動，未 push/PR/merge/switch-back；dirty/detached/collision fixtures 通過。 |
| AC-007 | TASK-002, TASK-012 | 通過 | Typed ExecPlan、atomic store、revision/mutation idempotency、restart reducer fixtures 通過；runtime state 預設 ignored。 |
| AC-008 | TASK-002, TASK-005, TASK-008 | 通過 | PendingDecision option/custom/cancel/malformed/stale round-trip 與 same-run resume tests 通過。 |
| AC-009 | TASK-010, TASK-012 | G3 待切換 | Canonical docs navigation、link/topic/trace guards與 public-check/finalizer contracts 通過；主樹在 G3 前刻意保留 legacy baseline/Wiki authority，exact finalized-tree public `check` 必須在 G3 後執行。 |
| AC-010 | TASK-003, TASK-011 | 通過 | `export-v1` byte-stable，記錄 21 closed work items／411 evidence files，input 未修改；raw V1 可由 immutable base/Git history回復。 |
| AC-011 | TASK-001, TASK-006 | 通過 | 六個 public CLI verbs、五個 versioned schemas、golden/unknown-field/version/error-code fixtures 通過。 |
| AC-012 | TASK-007, TASK-009 | 通過 | Extension event/controller/webview suites與 real VS Code smoke 通過；五個 accessible tabs 顯示 connection、run、plan、diff/tool、decision/Gate/verification/review/usage/diagnostics及 projection/stale 狀態。 |
| AC-013 | TASK-004, TASK-012 | 通過 | Verification DAG、selection、serial writers、`shell=False`、runtime executable hash、declared-effect reconciliation、stale/timeout/undeclared-write及 environment isolation tests 通過。 |
| AC-014 | TASK-008, TASK-012 | 通過 | Detached/max-three/critical-blocker controller tests 與 real detached reviewer thread 通過；strict versioned envelope 對 malformed、unavailable、contradictory output 均 fail closed。同一 isolated read-only reviewer 已以 `EVID-136` 確認 F-001、F-005 關閉且其餘 findings 無 regression。 |
| AC-015 | TASK-001, TASK-011 | G3 待切換 | 2.0.0 version/package contract、current-source 9-entry VSIX candidate verifier與 disposable clean-cutover forbidden-path/command scan通過；main finalizer 與 post-cutover final tree check 待 G3。 |
| AC-016 | TASK-002, TASK-005, TASK-006, TASK-008 | 通過 | Unknown method/field、forged role、stale revision、path/symlink/scope violation fixtures在 mutation 前拒絕並產生 bounded diagnostics。 |
| AC-017 | TASK-002, TASK-004, TASK-007 | 通過 | Canonical serialization、atomic replace/append、duplicate delivery及 crash-before/after-write replay tests 通過。 |
| AC-018 | TASK-004, TASK-009 | 通過 | Bounded metrics/log/diagnostic、secret redaction、reasoning discard、prompt non-persistence及 usage-unavailable/null semantics tests 通過。 |
| AC-019 | TASK-001, TASK-010 | G3 待切換 | Architecture fixture/checker涵蓋 root/module size、dependency direction、schema drift、docs links與 AC trace；current V2 suite 覆蓋 public-check fixture與 finalizer contracts，main transition tree需 finalizer 後重跑 exact public `check`。 |
| AC-020 | TASK-009, TASK-012 | 通過 | Extension 119/119、typecheck/build及 real VS Code `1.131.0` smoke 通過；UI report 9/9、1 screenshot、有完整 provenance與 bounds。 |
| AC-021 | TASK-001, TASK-011, TASK-012 | 通過 | 使用者明確核准資料傳送範圍後，Windows x64 path/process/JSONL/filesystem/Git adapter、VS Code smoke 與 real model-turn matrix 全部通過；其他 OS 維持 unverified。 |
| AC-022 | TASK-003, TASK-011, TASK-012 | 通過 | Scoped commit chain、immutable base、V1 export、failure-preserving finalizer tests與 disposable-clone recovery rehearsal通過；系統未自動 reset/merge/push。 |

## Profile 證據

- Current high-profile batch `VB-2238ef0753f0`：9/9 commands 通過、`max_parallel=1`，另有 2 個 release-only commands 明確 skipped。V2 Python 94/94（`EVID-132`）、repository contract 16/16（`EVID-128`）、CLI 24/24（`EVID-127`）、core 47/47 且 1 個既知 Windows symlink privilege skip（`EVID-129`）、guard 15/15（`EVID-130`）、knowledge 16/16（`EVID-131`），全部 current／gate-eligible。
- Extension unit/DOM/security：119/119 通過（`EVID-125`）；typecheck 通過（`EVID-126`）。其中 Windows 實體 `docs/EXEC-P~1/**` alias 在 host start、plan-save及 Extension approval/sandbox 三條路徑都於 mutation 前 fail closed。
- Main-tree real Codex E2E（`EVID-133`）：2 次 native command approval request 均由 client decline、interrupt 1 次且狀態為 `interrupted`、strict detached review envelope、exact 8 MCP tools、191 個 bounded protocol messages、synthetic persisted thread 已刪除；sentinel 不存在，run summary 未保存 prompt/reasoning/secrets。
- Acceptance crash-window fault injection 已在 completed state atomic replace 後立即中斷；restart 先冪等完成 active-to-completed placement，再建立 exactly one checkpoint commit/ref/digest/final journal，工作樹 clean，第二次 resume 不新增 commit（`EVID-132`）。
- 乾淨 certification clone `a6641b5719caa0bdcb4b2e2046ff8ca89b98f500` 的 tracked source clean，frozen local `origin/master` 精確指向 immutable base；2.0.0 source-derived VSIX candidate 共 9 entries、25,222 bytes，provenance SHA-256 `6235e9c7e5c89be91a1488bd4f31c6dca8fb0ff23c34104322a256eb4525007f`，VSIX SHA-256 `028c520e99a0361648720e2bf826fe5f71820c1dd1de8dd7a5268003c0fbcaaa`。Cached VS Code `1.131.0` smoke 在 updates-disabled 環境通過且未下載 artifact；UI 9/9。
- Machine-readable release attestation（`EVID-134`，retained report SHA-256 `7d2a5b8316b851babd11741ba9d0c4d74968976d91b4217c833c2bfe64acd9e2`）綁定目前 HEAD/fingerprint，並明確將 exact finalized-tree public `check`、V2 matrix及 forbidden-V1 scan列為 G3 後義務，不以 pre-G3 proof 冒充。
- Current acceptance synthesis 已以 `EVID-135` 綁定全部 22 項 AC、目前 HEAD/fingerprint、現有 evidence 與 G3 後義務。
- 同一 isolated read-only reviewer 的 final resolution review 已以 `EVID-136` 保存：`result=passed`、`severity=none`、零 findings，report SHA-256 `754d50046ed8d6346b33635e781fb3eba16596f4029b292e3e3e8d32567cb37e`。
- TASK-012 已建立 current-source audit snapshot，精確列出 `EVID-125` 至 `EVID-136`、目前 HEAD 與 source fingerprint。
- `EVID-001` 至 `EVID-113` 不得取代 current G3 proof；其中多數因後續 product source commit 或 manifest refresh stale。`EVID-123` 是未設定 live opt-in 時的預期 fail-closed 診斷，沒有啟動 network activity；已由單獨通過的 `EVID-124` 與完整 current batch內的 `EVID-133` supersede。舊 reviewer findings 仍保留為必須由同一 reviewer resolution review 的歷史。
- `EVID-114` 是修補 commit 後的 standalone controlled typecheck；第一次 current-source high-profile attempt `VB-3e439461ffdb` 中，`EVID-115`（Extension 119/119）、`EVID-116`（typecheck）、`EVID-117`（CLI 24/24）、`EVID-118`（repository contract 16/16）、`EVID-119`（core 47/47，1 skip）、`EVID-120`（guard 15/15）、`EVID-121`（knowledge 16/16）、`EVID-122`（V2 94/94）皆通過，只有未提供 explicit opt-in 的 live command 以 `EVID-123` fail closed。它們保留為 current diagnostic/history，但正式 frozen full-set proof 使用後續一次完成的 `VB-2238ef0753f0`／`EVID-125` 至 `EVID-133`；standalone opt-in proof `EVID-124` 亦由其中 `EVID-133` supersede。
- Formal release evidence 尚缺：human G3、main finalizer與 post-cutover full matrix。

## 基線更新

- `product.md` 加入 V2 app-server primary surface、exact MCP tools、2.0.0 clean cutover/recovery 與通過的 Windows x64 live certification。
- `architecture.md` 加入實際 Codex protocol/schema observations、forced user approval policy、strict review fallback、host/MCP boundary、ExecPlan authority、verification `env_allowlist` 與 hash-bound finalizer。
- `quality.md` 加入目前測試、real VS Code/UI/live evidence、Codex/schema provenance、disposable rehearsal與 remaining blockers。
- 以上三份 legacy baseline 只服務本次 G3；finalizer 後由 `ARCHITECTURE.md` 與 `docs/` 成為唯一長期 truth。

## Wiki 知識提升

Disposition：`promote`。V2 刻意取消 Wiki runtime authority，新的 durable knowledge 已寫入 `ARCHITECTURE.md` 與 `docs/{product,design,reliability,security,quality}.md`；legacy knowledge plan 精確刪除 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/command-policy-engine.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`，並同步 sealed `wiki/index.md` 與 append-only `wiki/log.md`。Engine 只允許 log 中、且 stem 精確列於本次 delete plan 的歷史 missing wikilink；index、其他頁面或未宣告 target 仍 fail closed。Actual finalizer 會在 G3 後依核准 manifest 移除剩餘 Wiki raw tree。

## 獨立 Review

- Initial point-cut：同一 isolated read-only reviewer 已以 `EVID-045` 回報 critical F-001 至 F-007 與 advisory F-008；後續 review 逐步確認 F-002／F-003／F-004／F-006／F-007／F-008／F-009 已解決。最新 pre-fix review `EVID-113` 只保留 critical F-001、F-005；所有舊 review evidence 都因後續 source commit stale，不能作目前 verdict。
- Final resolution point-cut：原 reviewer 對 current source、resolution diff、`EVID-125` 至 `EVID-135`、TASK-012 snapshot、acceptance與 baselines 完成唯讀複核；`EVID-136` 的 verdict 為 `passed/none`、零 findings。Reviewer 確認 F-001 的 repository-aware lexical＋canonical validation可拒絕 NTFS 8.3 alias、reparse point、protected ancestor與實體 escape，也確認 F-005 的 durable completed-plan archive placement會先於唯一 checkpoint reconciliation，且既有 findings 無 regression。

| Finding | Final disposition |
| --- | --- |
| F-001 | Closed and confirmed by `EVID-136`; real Windows NTFS short-name regressions cover host, plan-save and Extension. |
| F-002 | Resolved by `EVID-057`; current regression remains passing. |
| F-003 | Resolved by `EVID-057`; current regression remains passing. |
| F-004 | Resolved by `EVID-057`; current regression remains passing. |
| F-005 | Closed and confirmed by `EVID-136`; completed-state-before-archive crash injection proves exactly-one checkpoint and idempotent second resume. |
| F-006 | Resolved by `EVID-057`; current regression remains passing. |
| F-007 | Resolved by `EVID-057`; current regression remains passing. |
| F-008 | Resolved by `EVID-057`; current regression remains passing. |
| F-009 | Count remains 24/24 and no regression was found by `EVID-136`. |

## 殘餘風險與 blockers

- 使用者已明確核准 live test 的 bounded 資料範圍、唯讀 Codex tool sandbox 與拒絕所有寫入；runner 僅為連線 OpenAI Codex 服務取得 outbound network，最後 controlled E2E 通過且 sentinel 不存在。
- Current VS Code 1.131.0 smoke 僅使用本機 cached runtime，並以 updates-disabled 環境執行；未觀察到 artifact download。此 host 邊界與 inner Codex turn 的 `networkAccess=false` 分開稽核。
- 早期診斷發現 machine-level `approvalsReviewer=auto_review` 曾先行核准一個寫入 probe，建立 23-byte `DEVWEAVE_E2E_MUST_NOT_EXIST.txt`（SHA-256 `08bf587375b98094d35adf089bfbe1292e8cc9af686a5ccc2e0ff313338d796c`）。該 exact regular file 已驗證並刪除；產品已在 start/resume/reconnect/turn 強制 `untrusted + user`，最後 harmless approval probe 只收到 request 並由 client decline。
- Codex `app-server` protocol 仍可能隨目前 alpha CLI 變動；generated schema hash、doctor、strict boundary parsers與 protocol regression tests是 drift detection seam。
- 目前 alpha CLI 的 custom detached review 未送出官方 `exitedReviewMode` item；fallback 只接受 `review/start` 綁定的 exact reviewer thread/turn、authoritative `agentMessage` 與同一 turn `completed`，一般 agent message 不會被保留為 review。
- 保留的 pre-G3 transition manifest SHA-256 為 `c4b99adfa58a03c3f1d2d7a87d7fae51005e7255b60e26e8fb3e0a802c36d925`，但未嵌入目前修補後 provenance，因此不得視為 current 或 apply。Human G3 前不 refresh／prepare／apply；G3 後才以 current verification／review provenance 重新 prepare，呈現 final exact hash，再執行 finalizer。
- Initial reviewer 已在完整 point-cut 後提出 `EVID-045` 並歷經 resolution reviews；同一 reviewer 最終以 current `EVID-136` 確認所有 critical findings 已關閉，未使用 reviewer replacement 或 waiver 規避。

## 驗收結論

目前為「G3 technical readiness 已完成，等待 human G3 明確核准」：real Codex model-turn／detached-review、完整 distribution doctor、Windows x64 certification、current frozen-plan commands、乾淨複本 package/smoke/UI/live、current TASK-012 snapshot、recovery rehearsal與同一 reviewer 的 `passed/none` verdict皆完成。G3 核准前不會 refresh/prepare/apply manifest，也不會在主工作樹執行 breaking finalizer。

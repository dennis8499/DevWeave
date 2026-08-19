---
title: DevWeave Knowledge Workflow
type: architecture
sources: [.agents/skills, .codex/hooks.json, AGENTS.md, README.md, docs/使用手冊.md]
last_updated: 2026-08-19
tags: [architecture]
status: active
source_fingerprint: "sha256:ee0f5dc08ab7e9986325a4013d43c4fa0d98b97348e217b3a22b5e01389270a2"
verified_by: 20260819-140802-bug-fix-node-20-and-posix-ci-regressions
---

# DevWeave Knowledge Workflow

## Context

DevWeave 將 Codebase Wiki 納入既有 Work Item lifecycle，而不是建立第二套 Wiki skill 或背景索引服務。Wiki 提供快速定位入口；source 與已核准 artifacts 仍是權威事實來源。G1/G2/Gate 的 material decision 問答採 Plan-first：canonical `request_user_input` 是 Codex host seam，router/phase guidance 只定義 payload 與 lifecycle，不新增另一個 lifecycle、engine state 或 UI。所有 pre-G2 mutation entry 先經 Router preflight；host capability 不可見時，Router 在 Work Item mutation 前停止並提示切換 Plan Mode。

## Companion Skill routing and completion

`devweave` 先決定 managed work item、session binding、current phase 與 human Gate；companion Skills 只在該 phase 內提供方法。G1 由 `grill-me`/`grilling` 在 Plan Mode 逐題處理 material requirements，使用 `request_user_input` 時每次一題、二至三個互斥選項、推薦第一項 `(Recommended)`、trade-off 與 host `Other`；G2 由 `codebase-design` 在 Plan Mode 固定 module/interface/seam/depth/locality/test-surface。普通或 Skill context 在 G2 前看不到工具時先回到 Plan Mode，只有明確 compatibility 才用結構化 fallback。只有 current G2 後 `tdd` 才能以 public seam 執行 red → minimal green vertical slices，bug diagnosis 則維持 red-capable loop 並在 G2 前使用 temporary/cache repro。每個 Skill 的答案、假設、設計與 evidence 回到當前 DevWeave artifact；新決策以 `revise` 回到最早受影響 phase。

`writing-great-skills` 是 maintenance-only overlay，不是 router 或 companion；它不在精確五個 companion allowlist、`skills-lock.json` 五筆 upstream set 或 Extension bootstrap bundle 中。五個 companion 的 upstream source/path/computedHash 保持 lock provenance 不變，local optimization 只整理 description、progressive disclosure、positive steering、completion criteria、metadata 與 phase boundaries。

Repository contract 以 exact six-governed-Skill set、frontmatter identity、relative-link containment、`devweave` implicit invocation、`grill-me` disabled implicit invocation 與 `disable-model-invocation` policy 補充驗證；UTF-8 quick validation、isolated forward-test、unit/Extension package/smoke/tests/typecheck 與 `git diff --check` 提供 current evidence。這個 overlay 不新增 public CLI、JSON schema、router、state、ledger 或 Git mutation。

## Components and Data Flow

1. `$devweave wiki bootstrap` 由 router 轉成 `knowledge bootstrap`。Engine 先評估 active、sourced、current 的 overview、architecture 與 module；完整時回 `already_complete`，否則 resume 或 create bootstrap-profile feature Work Item。

## Verification selection and evidence metrics

Verification remains an engine-owned extension of the existing project command contract. A command may declare `affected_paths`, `writes`, `outputs`, `release_only`, and `depends_on`. A low/standard affected-path run selects only intersecting classified commands, records explicit skip reasons, and closes dependencies without resurrecting release-only commands. A high profile is intentionally a full set even when a path filter is supplied, so efficiency selection never reduces high-risk coverage. Commands without metadata remain compatible in an explicit full-profile run and are skipped from selective non-high runs.

The same evidence pipeline records bounded `duration_ms`, context page/byte/char counts, tool counters, and verification selected/skipped/closure/cache metrics. The complete metrics payload is capped at 250,000 bytes and each numeric counter at 10,000,000. Exact host usage is optional: when Codex does not expose token/cost data, evidence records `usage.status=unavailable` with null usage fields. The engine rejects unknown or oversized metrics and does not store prompts or secrets.
2. G1 的 `knowledge context` 固定先記錄 index，再記錄最多五頁的 path、status、content hash、stored/computed source fingerprint。Nonfresh、矛盾或不足 knowledge 必須先形成 gap，才允許最小 raw-source fallback；repository 已能證實的事實不轉成使用者問題。
3. G1 由 `grill-me`/`grilling` 在 Plan Mode 逐題處理 material decisions。Codex host 可見時使用 `request_user_input`，題目提供兩至三個互斥選項、第一項 `(Recommended)`、trade-off 與 host `Other`；不可用時，普通 context 先回到 Plan Mode，只有無法切換或明確 compatibility 才使用相同結構的 numbered fallback。等待有效 answer 後才回流 `brief.md`/`requirements.md`；`validate` 後的問題、範圍、非目標、驗收與剩餘假設才可送 G1 explicit approval。
4. G2 由 `codebase-design` 在 Plan Mode 逐題處理 design choices，沿用 shared native-question contract。回答回流 `design.md`/`plan.md`，並在 `validate` 後以 Gate Double Check 展示選定/淘汰方案、介面、資料流、失敗處理、回復方式與 immutable task plan；G2 前不修改產品內容或 tracked tests。G2 後普通模式只執行 approved tasks；新的 material requirement/design/scope/task decision 必須停止並 `revise`。
5. G2 決定 bootstrap 的三至五個高價值頁或一般工作的 product design；Wiki 到 verification 前皆唯讀。使用者改變已批准答案或 Gate 發現新決策時，透過 `revise` 使受影響 Gate 失效並回到最早階段。
6. `init`/`start` 先以 read-only preflight 檢查 Wiki，再取得 project lock 並重檢；missing、empty 或 custom-only root 只補缺少的 starter，reserved file/directory type 或 frontmatter conflict 則在 `.devweave` project、baseline、cache、work-item 建立前回報 `knowledge_conflict`。
7. High-risk G3 在 final product/Wiki/baseline/diff/scope/evidence 穩定後，由唯一 router 啟動 exactly one isolated read-only Independent Review Agent。Reviewer 只能讀取 approved artifacts、完整 diff、risk/scope、baseline、Wiki context 與 evidence，不繼承主 Agent reasoning，也不能寫 source/Wiki/ledger 或 approve/revise/close；G2 `Design It Twice` 的 3+ design sub-agents 是不同階段的 optional comparison。
8. Router 將固定 JSON report 寫到 incoming cache，透過 machine-only `review record` 交給 engine。Engine 驗證 incoming 與 final log cache 的逐層 containment（含 symlink escape）、size、enum、AC/TASK coverage 與 current source fingerprint，redact secrets，寫入 `kind: review` evidence、Git HEAD、report hash、reviewer ID、context mode 與 bounded raw report；Python engine 不 spawn Agent。
9. Verification 的 `knowledge review` 保存 disposition、rationale、affected/covered/uncovered paths 與 product change fingerprint。後續產品 fingerprint 改變會使 knowledge review、plan 與 source-bound review evidence invalid，並要求重新審查。
10. `promote` 建立一至五個 content upsert/delete；新頁經 canonical scaffold 先成為 placeholder。完成 active 內容後同步 index、append-only log，再 seal source fingerprint 與 Work Item provenance。`no-update` 僅在非 bootstrap、無 affected page、無 Wiki diff 時成立。
11. G3 重新比對完整 Wiki diff、affected pages、plan、coupling、log、seal、baseline、current evidence 與 Independent Review。`passed` 正常通過；unavailable/advisory 形成 warning；critical security/data-loss/irreversible/scope finding 只有 exact named `review-critical` acceptance waiver 可解除。它只驗證實作是否符合已批准內容，不默默補入新需求或設計。人工核准後才可 close。
12. 0.2.3 Windows release verification 必須固定記錄 `py -3 -X utf8 -B ... doctor`、Extension tests/typecheck/package/smoke、Python release baseline、symlink 權限結果、disposable walkthrough 與 `git diff --check`；VSIX verifier 只驗證 current 0.2.3，包含 58 個 bootstrap files、119 個 VSIX entries、source length/hash、artifact SHA-256 與 root/embedded hook equality，並保留 0.2.2 artifact。本 work item 的 Extension final run 為 89 tests、Python final run 為 111 tests（1 skipped）。Release 必須先建立 candidate、完成 verifier，再以 atomic promotion 取代 current；verification 或 promotion 失敗不得破壞 current。High-risk review 仍只由 router 啟動 exactly one isolated read-only reviewer；failed evidence、未說明的 skip、stale evidence 或非 current `passed` review 都不符合 G3 release bar。
13. Windows Codex 的 PreToolUse launcher 是 bootstrap control contract：exact matcher `^(Bash|apply_patch|Edit|Write)$` 同時提供 POSIX `command` 與 Windows `commandWindows`。Windows path 使用 `powershell.exe -NoLogo -NoProfile -NonInteractive -Command`，先設定 `[Console]::InputEncoding`/`[Console]::OutputEncoding` 為 .NET UTF-8，再以 `py -3 -X utf8 -B` 和 `Join-Path (git rev-parse --show-toplevel)` 從 Git root 執行 `guard.py`；它不依賴 shell-scoped `$OutputEncoding`，可由 `cmd.exe`、Windows PowerShell 5.1、PowerShell 7 與 VS Code terminal 啟動。guard 以 UTF-8 bytes 解析/輸出，程序 exit 與 guard 的 `permissionDecision` JSON 是分離的結果，Extension 不會靜默覆寫既有 exact hook。launcher failure 與正常 process exit 0 的 policy deny 必須分開診斷。

## Public CI module and contract seam

`.github/workflows/ci.yml` 是 repository 唯一 Public CI Module。它的外部 interface 只有 `pull_request`／`master` push 與 Python、Node、hygiene check conclusions；內部以 12 個 Python cells、4 個 Node cells、1 個 hygiene job 隱藏 runner/runtime 展開。GitHub Actions 是唯一真實 provider，因此沒有建立第二個 CI adapter、scheduler 或 workflow lifecycle。

Repository-local seam 位於 `tests/test_repository_contract.py`。測試不呼叫 GitHub API、不加入 YAML parser，而是以 UTF-8 text 與 canonical job indentation 分離三個 job blocks，再對核准 matrix、commands、完整 Action SHA、`contents: read`、`persist-credentials: false` 與無 secret／error suppression 契約做 deterministic assertions。這讓 workflow 被刪除、縮減或放寬權限時，在 hosted run 前先產生本機 red signal；完整 YAML semantic 與真實 runner 結果仍由 GitHub 外部 oracle 負責。

Node 測試的跨平台 seam 不再把 quoted `**` glob 交給 Node 20／shell 解讀。`run-unit-tests.mjs` 自行遞迴探索、排序並將每個 absolute `.test.ts` path 以 argv 傳給 resolved `tsx/cli`，使用 `process.execPath`、`shell: false`，並把空集合、spawn error、signal 與 non-numeric exit 全部轉成非零。Python 測試則以 current interpreter 的 canonical resolved path 斷言 CLI、以 temporary repository 取代 Windows-only 假路徑；真實 CMD／Windows PowerShell／PowerShell 7 launcher tests 在非 Windows 明確 skip 並附固定 prerequisite reason。

這兩個 seam 的最終外部 oracle 是 PR #1 run `32231940371`：commit `036ca6b2cbaabe117a82420948e5b7c3bdbd2a83` 的 12 個 Python、4 個 Node 與 1 個 hygiene checks 共 17/17 通過。Hosted observation 只作補充 provenance；G3 仍要求同一 source fingerprint 的 controlled、zero-only、gate-eligible local evidence。

CI 不進入 DevWeave machine lifecycle：它不 approve Gate、不寫 state/events/evidence、不更新 Wiki、不 commit/push/開 PR。Node build output 只存在 runner workspace；smoke/package/release 保留在 frozen release-only verification policy。Public CI pass 只代表 development contract，不改寫特定 Windows release certification。

## VS Code Control Center integration

VS Code Extension 是這條 lifecycle 的唯讀 projection client。Host 以 `WorkspaceSnapshotReader` 讀取 project、work item、Wiki、evidence 與 bootstrap completeness；它不執行 Python engine、shell、Git、network 或 Codex API。使用者確認初始化後，`BootstrapInstaller` 才能套用 0.2.3 allowlisted control bundle；project、三份 baseline 與三份 Wiki starter 依 shared semantic validator 採用合法 evolved bytes，其他 controls 仍以 exact policy 檢查，missing-only write 與 conflict/rollback 邊界不變。

Bootstrap bundle 內的 hook 來自根目錄 `.codex/hooks.json`，其 exact `PreToolUse` matcher 與 POSIX/Windows dual path 經 `cmd.exe /d /s /c`、Windows PowerShell 5.1、PowerShell 7、root/nested Git-root cwd 實際驗證，包含 raw UTF-8 payload；正常 DevWeave policy deny 仍輸出 `hookSpecificOutput.permissionDecision: deny` 且 process exit 0。這個 source-derived 行為由 package verifier 與 repository contract regression 固定檢查。

Knowledge section 的查詢是 Extension-local 行為，不會改寫 G1 context 或 Wiki：`WikiSearchModel` 保留 draft/applied query，按 Enter 後才以 case-insensitive contains 搜尋 title、path 與 body preview；type filter 是精確匹配，結果與 metric 真實 mount 到 `#wiki-results`。檔案 watcher 仍自動 refresh，但由 250ms debounce、single-flight 與 latest-pending coordinator 合併 burst，snapshot 的平行讀取最後以 deterministic order 合併。

Preview safety 由 host `PreviewGate` 最終 enforcement：ticket 綁定 panel identity、typed intent、完整 prompt bundle、snapshot revision 與一次性 consume；intent 以 discriminated-union 欄位逐欄比較，不使用可碰撞的 delimiter key，protocol 也拒絕危險控制字元。Refresh、初始化、work selection 或 snapshot 更新會 invalidate 舊 ticket；clipboard failure 只可在同一 current ticket 安全 retry 一次。Host-launched `actionPreview` 傳回同一 intent/bundle/revision，使 `devweave.copyNextAction` 不再 bypass preview。

`devweave.wikiBootstrap` 也必須走同一條 host preview route；native command 入口不持有直接 clipboard seam。Webview 的 `dashboard-sections.ts` 將五個 tab 的順序、方向鍵/Home/End 與 panel `id`/`aria-labelledby`/hidden state 保持為純 contract，inactive panel 仍存在讓每個 `aria-controls` 有效，並由 bounded release test 驗證 focus restore 與 forced-colors CSS boundary。

Copy transaction 將 clipboard adapter failure 與成功後的 `copyResult`/native toast notification 分離：ticket 一旦被成功 consume 並寫入 clipboard，後續 notification transport failure 不得 restore，避免同一 preview 被重複複製；Python/Extension walkthrough markers 由 configured verification commands 留在 current raw logs。

Plan Mode handoff 是非權威的 Extension guidance：no-active 或 pre-G2 snapshot 由 `SnapshotGuidance` 帶出 optional `PlanModeGuidance`，mutation preview 與 copied result 顯示「先切換 Plan Mode，再貼到 Codex Chat」。`PromptBundle.chatText` 仍是原本的 `$devweave ...` prompt，copy 仍可用；Extension 不讀取、切換或模擬 host mode，也不建立 host mode adapter。

Control Center 的五個區域使用 tab/tabpanel `aria-controls`、`aria-labelledby`、roving tabindex、方向鍵/Home/End 與 focus restore；主要 CTA、native modal action、readiness、error 與 empty-state copy 使用繁體中文。錯誤的 user-facing status 先顯示繁中指引，原始技術訊息只放在可展開 detail，技術 command 名稱保留在 code/technical label。

說明頁是 Extension bundle 內的 lazy local content，不寫入 target repository，也不需要網路。這些 UI／package 知識在 G3 promote 更新，若需求或設計改變仍須回到同一 Work Item 的 `revise` 與 Gate lifecycle。

## Boundaries

- `knowledge_core` 不讀寫 Work Item ledger；`devweave_core` 在 WorkLock 內擁有 lifecycle 與 event policy；CLI 只做 JSON adapter。
- `knowledge_core.inspect_wiki` 是 init 的 read-only reserved-starter seam；`devweave_core.init_project` 在 lock 外與 lock 內各檢查一次，只有 preflight 成功才建立 control bundle。
- Guard 只允許 verification 中 knowledge plan 的 content paths，以及自動 coupling 的 `wiki/index.md`、`wiki/log.md`。
- Review Agent 的啟動權只在既有 router；Python engine 只記錄 machine report，Extension 只投影 readiness，三者不產生第二個 lifecycle 或平行 ledger。
- 互動式問答由 router/phase guidance 約束；`new`、`feature`、`refactor`、`bug`、`wiki bootstrap` 與回到 G1/G2 的 `revise` 在 `start`、`bind`、`revise` 或 bootstrap create 前完成 Plan Mode preflight。不新增 pending-question state、CLI、JSON schema、VS Code UI 或第二套 question ledger。沉默與模糊同意不構成 approval，未回答的 material decision 會停在目前階段。
- `request_user_input` 的可見性由 Codex host 決定；repository 不宣稱 ordinary/Skill native support，也不提供 fake alias 或 adapter。Router 無 capability 證據時必須停止並提示切換 Plan Mode，只有使用者明確選擇 compatibility 才進入 structured fallback。取消、逾時、malformed、空值與 ambiguous result 維持 pending，Gate 仍只接受 validation 後的既有 `approve`/`revise` CLI contract。
- 每頁最多五個 sources；每次 context 最多五個內容頁；每次 promotion 最多五個 content targets。
- Bootstrap 不接受 repository 子路徑 scope，不修改產品 source，且需 promote overview、至少一個 architecture、至少一個 module。
- Extension 不建立 process/network seam，也不自行重算 Git/source fingerprint；其 bootstrap、PreviewGate 與 Independent Review readiness 判定都是非權威 filesystem projection，但 host copy boundary 仍是 clipboard 安全的最終 enforcement point。
- `bootstrap-compat.ts` 是 installer 與 snapshot 共用的 semantic validator seam；manifest 缺少 policy 時正規化為 exact，unknown policy/kind 在寫入前 fail closed。

## Evidence and Gaps

- Lifecycle、legacy compatibility、source invalidation、bootstrap G1→G3、九種 scaffold、guard 與 seal 由 Python regression 覆蓋。
- Extension intent parity、strict protocol、unknown state fail-closed、no-process/no-network、package 與 Extension Host activation 由 unit/security/typecheck/package/smoke 驗證。
- Durable value 是語意判斷，machine 只能提供 coverage 與 affected-page obligation；最終由 Knowledge Review rationale 與 G3 人工核准承擔。Repository contract tests 可檢查政策存在，實際對話是否逐題等待仍需以運行時情境驗收。
- Plan Mode native round-trip 與 ordinary/Skill tool visibility 必須以 host/manual evidence 驗證；目前 ordinary/Skill context 未暴露工具時，current result 是 unavailable compatibility，不可把 structured fallback 或 policy text 誤報成 native pass。

G3 selection parity 的細節也屬於同一 frozen plan contract：`release-only` command 與 `release-only-dependency:<id>` 都是 plan-defined skip，不得被 G3 當成缺少 required command；Runner 與 G3 必須逐字重用 skip reason。

## Verification Policy v2 與 G3 parity（2026-08-16）

驗證入口不再各自推導 command 是否安全。唯一的 `command_policy.py` evaluator 同時服務 PreToolUse Guard、command/profile runner、Doctor、command set/remove 與 G3 validator；任何 unknown flag、shell operator、substitution、redirection、非 canonical executable/cwd、錯誤 phase/risk/session/release context 都 fail closed。configured command 的直接 Bash 呼叫只回報「請使用 `devweave verify`」，不啟動命令。

G2 approval 在 Work Item state 內凍結 Effective Verification Plan，保存 plan ID/digest、project policy digest、command definition digests、required/selected/skipped/not-applicable 集合、dependency closure、stage、writes、outputs、expected exit policy 與 gate eligibility policy。Runner 的 selection response 與 G3 required set 都直接重用這份 snapshot；release-only command 沒有 explicit release context 時是 skipped，依賴它的 smoke command 也明確 skipped，不會被另一入口重新要求。

Evidence 是 execution observation，不是 caller assertion。engine 會記錄 canonical argv/cwd、plan/command/source/input/output fingerprint、實際 exit code、changed/undeclared paths 與 execution channel；只有 controlled executor、zero-only formal success、current digest/source、無 timeout/error/undeclared effect 且 postcondition/promotion 成功時才 `gate_eligible=true`。policy mutation 會使 plan、G2/G3 與 command evidence stale；writes command 先在 candidate stage 完成，read-only stage 只能在 writer barrier 後平行。

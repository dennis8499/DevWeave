---
title: Knowledge Engine
type: module
sources: [.agents/skills/devweave/scripts, tests/devweave_test_support.py, tests/test_cli.py, tests/test_devweave_core.py, tests/test_repository_contract.py]
last_updated: 2026-08-13
tags: [module]
status: active
source_fingerprint: "sha256:c422adb540ff1cc910d9705fa7ba1e25697a74ade8232a011717756f3e27f260"
verified_by: 20260813-142228-feature-devweave-vs-code-extension
---

# Knowledge Engine

## Responsibility

Knowledge Engine 是 DevWeave 既有 Python engine 內的深模組組合。`knowledge_core.py` 提供純 Wiki/source 運算、reserved-starter preflight 與安全檔案操作；`devweave_core.py` 將這些能力綁定 Work Item phase、gate、review、plan、event 與 acceptance policy；`devweave.py` 暴露穩定 JSON machine commands。Engine 是 machine lifecycle 與 knowledge state 的權威；G1/G2 的逐題問答則由唯一 router 與 phase guidance 驅動，經 host canonical `request_user_input` seam 回答並寫入既有 artifacts，不在 Engine 內維護 pending-question state。

## Public Surface

- `knowledge bootstrap`：repository-wide assessment，回傳 `already_complete|resume|created`。
- `knowledge status`：回報 health、bootstrap reasons、affected pages、covered/uncovered changed paths、review currentness 與 planned updates。
- `knowledge context`：replace G1 ordered context，強制 index-first、最多五個內容頁與 nonfresh gap。
- `knowledge review`：在 current G2 後記錄 `promote|no-update`；產品 source fingerprint 改變時失效。
- `knowledge plan`：replace 一至五個 content targets，自動 coupling index/log。
- `knowledge scaffold`：只對 planned new upsert，以九種 canonical template 進行 exclusive create。
- `knowledge seal`：只接受 planned upserts/coupled pages，拒絕 placeholder、template token、invalid source 與 critical lint。
- `init/start`：在 project lock 外與 lock 內做 Wiki reserved-starter preflight；missing、empty、custom-only root 可補 starter，reserved type/frontmatter conflict 以 `knowledge_conflict` fail closed，且不留下 partial `.devweave` control state。
- machine-only `review record`：由既有 router 傳入固定 reviewer JSON report 與 opaque reviewer ID；只接受 high-risk G3 的 isolated/read-only review，產生 source-bound `kind: review` evidence 與 redacted report provenance，不是新的 public chat verb。

## Verification and metrics contract

`command set` accepts optional relative `affected_paths`, `writes` (`none|generated|tracked-artifact`), `outputs`, and `release_only`. `verify --profile <low|standard|high> --path <path>` applies path intersection for non-high profiles, reports skipped reasons and dependency closure, and preserves a full command set for high. Release-only commands and their dependents are not silently reintroduced into low/standard selection. Invalid metadata, traversal, duplicate paths, unknown fields, malformed metrics, and oversized payloads fail closed.

Verification evidence remains the single durable metrics surface. The engine records execution duration and bounded verification selection; callers may add bounded context/tool counters and explicit usage. The complete metrics payload is limited to 250,000 bytes and numeric counters to 10,000,000. Usage is status-aware: unavailable host usage is stored as unavailable with null token/cost fields, never inferred from bytes or prompt text. Legacy evidence without `metrics` remains readable.

CLI machine output explicitly reconfigures standard streams to UTF-8 when the host supports it, preserving non-ASCII executable paths and argv values in JSON evidence and command responses; embedded streams that cannot be reconfigured keep their existing transport without changing the schema.

0.2.3 current-version-only release 不新增 Python public command、CLI schema 或 engine lifecycle。Repository contract 以既有 test surface 機械檢查 README、使用手冊、Extension README 與內嵌 Help 的單一 0.2.3 交付、限定認證環境、Python release baseline、88 項 Extension tests 與 data-preserving incident response；package verifier 只接受明確的 candidate artifact，完成 source-derived 58 個 bootstrap files、119 個 VSIX entries、artifact hash 與 hook equality 後才由 release orchestrator promotion，失敗時保留 current 並清理 candidate；並保留 0.2.2 與 0.2.1 artifact。Extension 的 PreviewGate、`actionPreview` protocol、legacy `copyNextAction` 與 Wiki DOM mount 都是 projection/client-side seams。Python engine 仍是 work state、multi-work `next/status --all`、bootstrap cancel/failure 與 gate/evidence 的權威來源。

Release verification 將這個 boundary 綁到 current source fingerprint：Extension bounded walkthrough 需覆蓋 fresh/evolved/conflict/rollback 與 multi-work selection，Python targeted fixtures 需確認 conflict 保留 user bytes；high-risk review 仍只能由 router 透過 machine-only `review record` 記錄，不能由 engine 或 Extension 自行啟動。

互動式決策不是新的 public machine command：G1 由 `grill-me`/`grilling` 協助確認 material requirements，G2 由 `codebase-design` 協助確認 material design；Plan Mode 是目前正式入口，每次只處理一題並等待使用者回答。Gate 在 `validate` 後再做 Double Check，若答案或決策改變，沿既有 `revise` 使 Gate 與 artifacts 回到正確階段。

## Native question contract

- Canonical host tool 是 `request_user_input`；每次 request 只有一題，options 為二至三個互斥選項，第一項標記 `(Recommended)`，每個選項有 trade-off/description，host `Other` 保留自訂答案。
- `new`、`feature`、`refactor`、`bug`、`wiki bootstrap` 與回到 G1/G2 的 `revise` 先做 Plan Mode preflight，再進入 `start`、`bind`、`revise` 或 bootstrap create；未見 `request_user_input` capability 時 Router 必須停止並提示切換 Plan Mode。
- G1/G2/Gate 的 material decisions 在 Plan Mode 提問。普通或 Skill context 在 G2 前看不到工具時先停止並回到 Plan Mode；只有 host 無法切換或使用者明確選擇 compatibility 時，才使用同順序、同推薦、同 custom-answer 的 structured fallback，不建立 fake adapter 或額外 question state。
- G2 current 後，普通模式只執行 approved task；實作中新的 requirement/design/scope/task decision 必須停止並透過 `$devweave revise` 回到最早受影響 phase。
- Host result 只可正規化為目前 question identity 與 valid selection/custom text；cancelled、timeout、malformed、empty 或 ambiguous result 不得寫 artifact、approve Gate 或猜答案。既有 validation 與 CLI `approve`/`revise` 仍是權威。
- Tool visibility 是外部 host capability。Engine、Skill 與 VS Code Extension 不建立 `requestUserInput` alias、fake adapter、pending-question schema、CLI 或第二套 ledger。

## Dependencies

- Runtime 僅使用 Python standard library 與 Git CLI；沒有向量資料庫、全文檢索服務或 Token instrumentation。
- Source/page path 必須 normalize 為 repository-relative；Wiki、`.devweave` 與 `.git` 不得成為 page source。
- Source fingerprint 納入 tracked 與非 ignored untracked content、dirty bytes、rename/delete 與 branch identity；Wiki 與 framework ledger 不污染 product evidence fingerprint。
- Review report 只可來自 `.devweave/cache/incoming/<work-id>/` containment，受 project raw-log size limit、固定 envelope、UTF-8、AC/TASK ID、secret redaction 與 SHA-256 hash 保護；engine 寫入 `.devweave/cache/logs/<work-id>/` 前會逐層驗證 final path containment 並拒絕 symlink escape，Agent 不可直接寫 evidence JSON/JSONL。
- Canonical templates 位於 `.agents/skills/devweave/assets/wiki/templates/`，是 engine-owned inputs；live knowledge 固定在根 `wiki/`。

## Behavior and Gaps

- Bootstrap readiness 要求無 critical lint，且 overview、architecture、module 皆 active、sourced、current 並有 `verified_by`；既有 Wiki 超過五頁仍可視為完成。
- Wiki bootstrap skeleton 的 compatibility 只檢查保留 starter files/directories；非保留自訂內容不會因缺少 `index.md` 被誤判 conflict。`init_project()` 成功完成 Wiki preflight 後才建立 project、baseline、cache 與 work-item directories。
- `affected_pages` 依 Work Item 起始 Wiki source overlap 計算；既有 affected page 在 G3 必須 refresh/seal 或 delete。Coverage 將 current active pages 的 source overlap 投影成 covered/uncovered，供 durable-value review 判斷。
- Codex PreToolUse 的 process 與 policy 是兩個 boundary：exact matcher `^(Bash|apply_patch|Edit|Write)$` 同時保留 POSIX `command` 與 Windows `commandWindows`。Windows runner 經 `cmd.exe`、Windows PowerShell 5.1、PowerShell 7 或 VS Code terminal 啟動 `powershell.exe -NoLogo -NoProfile -NonInteractive`，先設定 `[Console]::InputEncoding`/`[Console]::OutputEncoding` 為 .NET UTF-8，再以 `py -3 -X utf8 -B` 從 Git root 執行 `guard.py`；不依賴 shell-scoped `$OutputEncoding`，guard 直接讀寫 UTF-8 bytes，deny JSON 仍以 process exit 0 結束。這不改變 guard decision schema，也不把 launcher failure 與 policy deny 混為一談。
- Knowledge Engine 不替 agent 判斷哪些 repository facts 應詢問使用者；可由 Wiki/source/artifacts 查出的事實由流程自動整理，只有會改變目標、範圍、介面、風險、相容性或驗收的 material decision 進入對話。這是 router policy，不是 engine 自動決策。
- 新式 state 以 `knowledge_review_required: true` 啟用完整 contract；缺少 marker 的 schema-v1 Work Item 維持 legacy compatibility，不追溯阻擋。
- Scaffold 採 no-overwrite create；seal 先完成所有候選 preflight，再以 per-file atomic replace 寫 provenance。多檔 I/O 仍是逐檔 atomic，最終完整性由 G3 reconciliation 保證。
- Engine 不自動判斷每個 uncovered path 是否值得長期保存，也不強迫一檔一頁；這是刻意保留給 agent review 與人工 G3 的語意責任。
- Engine 不判定沉默、模糊同意或 agent 推斷為 approval；explicit human approval 仍是 gate event 的必要條件。G3 只檢查實作對已批准內容的符合性，新需求必須經 `revise`，不能在驗證時默默補入。
- Engine 不負責注入或檢測 host question UI；Plan Mode/native visibility、ordinary/Skill exposure、answer round-trip、cancel/timeout/malformed 是 router/host integration 的外部證據。Policy text 與 structured fallback 不可作為 ordinary native support 的證明。
- G3 review validator 對 current `passed` 放行、對 unavailable/advisory 發 warning，對 critical finding 要求每個具名 `F-###` 有 acceptance-gate `review-critical` waiver；source fingerprint 改變會讓 review stale，legacy evidence 仍可讀但不能冒充 current independent review。

## Lifecycle boundary

DevWeave 仍是唯一 router；Companion Skills 是階段內方法，不建立第二套 work-item lifecycle、artifact set 或 approval protocol。`diagnosing-bugs` 仍限於既有診斷階段，`tdd` 仍只能在 current G2 approval 後的 implementation 使用；若 implementation 發現新 material decision，必須停止並 `revise`。此互動規則不新增 CLI、JSON schema、ledger 欄位或 VS Code UI。

## Skill governance boundary

Engine 以 repository contract 投影精確六個受治理 Skill：唯一 `devweave` router 加五個 companion。`writing-great-skills` 僅是 maintenance-only instruction overlay，不進 companion allowlist、lock provenance 或 Extension bootstrap bundle。五個 companion 的 upstream source/path/computedHash 維持 `skills-lock.json` 原值；local optimization 不改寫 upstream provenance。

Skill quality checks 是 engine 外的 repository contract 與 UTF-8 validator 輸入：frontmatter identity、metadata、relative links、implicit invocation policy、單題決策、G1/G2 stop、public seam、red-capable repro、independent oracle 與 completion criteria。`grill-me` 的 `disable-model-invocation` 是必要 metadata，validator 不支援時由 contract 補驗；不因此增加 machine lifecycle state 或 public command。

## Extension integration boundary

- `vscode-extension/src/snapshot.ts` 只把 project、work、gate、task、evidence、Wiki 與 diagnostics 投影成 filesystem snapshot；它不執行 Python engine、shell、Git、network 或 Codex API，並與 installer 共用 `bootstrap-compat.ts` semantic validator。
- `vscode-extension/src/presentation.ts` 是 Extension-local 的 presentation seam，集中 public command 任務語言、非權威 snapshot guidance、review readiness、繁中 diagnostic copy 與 audit event mapping；`SnapshotGuidance` 與 `PromptBundle` 的 optional `PlanModeGuidance` 只提供 `required`/`stage` handoff metadata，不改變 Python schema 或 `$devweave` prompt contract。
- `vscode-extension/src/snapshot.ts` 以 optional nested review projection 讀取 result/severity/findings/hash；`presentation.ts` 在 high-risk acceptance 增加 Independent Review check，missing/unavailable/advisory 顯示 attention、critical 顯示 not-ready，Extension 不啟動 Agent 或修改 lifecycle。
- Control Center Webview 以總覽、工作項目、知識、驗證（含稽核）與說明五區分區；active work 與 closed history 分組，Knowledge 列表以 snapshot 內資料提供搜尋、分類與 bounded initial list，使用者可明確顯示全部。
- `setDisplayMode` 只更新 Extension `workspaceState`。初始化仍是使用者確認後的固定 bootstrap write；其他命令只預覽／複製 prompt 到 Codex Chat，送出後由使用者 Refresh 取得新的檔案投影。

## VS Code Extension contract

Control Center 依賴 engine 產生的 filesystem projection，但不把 Extension 當成 machine lifecycle 的權威來源。`WorkspaceSnapshotReader` 只讀取 project、hook、skills、baseline、Wiki 與 Work Item artifacts；`WorkspaceSnapshot.bootstrap` 另外依 bundle destination/hash contract 回報 expected、missing、conflicts 與 complete。`project.json` 存在本身不能代表完整初始化。

Extension 的 Wiki 搜尋不新增 knowledge machine command 或索引服務。`WikiSearchModel` 將輸入拆成 draft 與 applied query，Enter 才套用大小寫不敏感的包含式搜尋，欄位是 title、path 與 body preview；分類是 exact type filter，show-all 只改變可見頁數。Webview 保留輸入 DOM，結果與 metrics 真實 mount 到 `#wiki-results`，`RenderScheduler` 合併同一 event loop 的 local renders。

Watcher refresh 與手動 refresh 共用 `RefreshCoordinator`。Coordinator 一次只允許一個 snapshot read；burst 期間保留最新 pending request，成功結果不被較舊 read 回退。Reader 對互不依賴的檔案操作使用平行讀取，但以 sorted path/id 合併 projection 與 diagnostics，維持 engine contract 的 deterministic output。

Bootstrap bundle 的來源與目的地由 build-time manifest 固定，版本從 package version 產生：`devweave` 加上五個核准 companion skills、通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter。`existingPolicy` 缺少時安全預設 `exact`；只有 project、三份 baseline、三份 Wiki starter 宣告 `adopt-compatible` 與固定 compatibility kind。`BootstrapInstaller.inspect()` 與 snapshot 先做 read-only integrity/path preflight，再以 shared validator 判定 evolved bytes；install 只建立 missing paths，寫入失敗則 rollback 本輪建立的檔案。Dashboard 以 completeness projection 提供初始化／補齊入口。

Codex hook bootstrap 來源是根目錄 `.codex/hooks.json` 的 exact `PreToolUse` group。Windows runner 透過 `cmd.exe`、Windows PowerShell 5.1、PowerShell 7 或 VS Code terminal 啟動 `powershell.exe -NoLogo -NoProfile -NonInteractive`，先設定 `[Console]::InputEncoding`/`[Console]::OutputEncoding` 為 .NET UTF-8，再以 `py -3 -X utf8 -B` 和 Git-root expression 導向 `.agents\skills\devweave\scripts\guard.py`；不使用 shell-scoped `$OutputEncoding`。0.2.3 manifest 與 VSIX 內嵌相同 dual-path contract，verifier 會拒絕缺少 explicit UTF-8、exact matcher、使用 `$repo` 或 root/embedded hook drift 的 bundle。`doctor` 會先檢查 prerequisite、schema 與 root/nested launcher probe；既有 workspace 的 exact hook 需要使用者確認後更新，Extension 不會靜默覆寫。

`vscode-extension/src/preview-gate.ts` 是純 host-side ticket seam；它只接受同一 panel、typed intent、snapshot revision 的 preview bundle，intent 以欄位結構比較避免 delimiter collision，protocol 拒絕危險控制字元，one-shot consume 後才交給 clipboard adapter，revision/selection/refresh 更新會使 ticket stale，clipboard failure 只允許同一 current ticket retry 一次。0.2.3 的 public command handoff 維持原有 `$devweave` command text 與 Python schema：Extension 先預覽、由使用者確認複製到 Codex Chat，完成後 Refresh 取得新 snapshot；多 active work 的 `next` 要求明確 selection，未指定 work 的 `status` 產生 `$devweave status --all`，`copyNextAction` 只開啟 Control Center。初始或 pre-G2 guidance 只顯示「先切換 Plan Mode，再貼到 Codex Chat」，不提供 host mode command 或 adapter。

Copy success 的 Webview result 與 native toast 是 consume 後的通知，不屬於 clipboard adapter failure；因此 notification 發生錯誤時不會把已成功 consumed 的 ticket 還原。Host error path 將原始錯誤轉成繁中 primary status，technical detail 只在可展開區域呈現。Configured full-suite raw logs 會保留 bounded fresh/evolved/conflict/rollback/multi-work 與 accessibility markers，供 G3 獨立核驗 walkthrough provenance。

說明內容嵌入 Extension bundle 並在首次切換 help section 時 render；它不落地到 workspace、不發 network request。Extension runtime 維持 no process、no shell、no external network，除使用者確認的固定 bootstrap path 外不提供 workspace write seam。

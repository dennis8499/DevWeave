---
title: Knowledge Engine
type: module
sources: [.agents/skills/devweave/assets/wiki/templates, .agents/skills/devweave/scripts, tests, vscode-extension]
last_updated: 2026-08-04
tags: [module]
status: active
source_fingerprint: "sha256:f65e2279e62f1a8e493e9a3d799a4806cfa066db3b370dd2dce0df2d70200838"
verified_by: 20260804-205655-feature-devweave-0-2-1-windows
---

# Knowledge Engine

## Responsibility

Knowledge Engine 是 DevWeave 既有 Python engine 內的深模組組合。`knowledge_core.py` 提供純 Wiki/source 運算、reserved-starter preflight 與安全檔案操作；`devweave_core.py` 將這些能力綁定 Work Item phase、gate、review、plan、event 與 acceptance policy；`devweave.py` 暴露穩定 JSON machine commands。Engine 是 machine lifecycle 與 knowledge state 的權威；G1/G2 的逐題問答則由唯一 router 與 phase guidance 驅動，回答寫入既有 artifacts，不在 Engine 內維護 pending-question state。

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

0.2.1 Windows release 不新增 Python public command、CLI schema 或 engine lifecycle。Extension 的 PreviewGate、`actionPreview` protocol、legacy `copyNextAction` 與 Wiki DOM mount 都是 projection/client-side seams；Python engine 仍是 work state、multi-work `next/status --all`、bootstrap cancel/failure 與 gate/evidence 的權威來源。

Release verification 將這個 boundary 綁到 current source fingerprint：Extension bounded walkthrough 需覆蓋 fresh/evolved/conflict/rollback 與 multi-work selection，Python targeted fixtures 需確認 conflict 保留 user bytes；high-risk review 仍只能由 router 透過 machine-only `review record` 記錄，不能由 engine 或 Extension 自行啟動。

互動式決策不是新的 public machine command：G1 由 `grill-me`/`grilling` 協助確認 material requirements，G2 由 `codebase-design` 協助確認 material design；每次只處理一題並等待使用者回答。Gate 在 `validate` 後再做 Double Check，若答案或決策改變，沿既有 `revise` 使 Gate 與 artifacts 回到正確階段。

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
- Knowledge Engine 不替 agent 判斷哪些 repository facts 應詢問使用者；可由 Wiki/source/artifacts 查出的事實由流程自動整理，只有會改變目標、範圍、介面、風險、相容性或驗收的 material decision 進入對話。這是 router policy，不是 engine 自動決策。
- 新式 state 以 `knowledge_review_required: true` 啟用完整 contract；缺少 marker 的 schema-v1 Work Item 維持 legacy compatibility，不追溯阻擋。
- Scaffold 採 no-overwrite create；seal 先完成所有候選 preflight，再以 per-file atomic replace 寫 provenance。多檔 I/O 仍是逐檔 atomic，最終完整性由 G3 reconciliation 保證。
- Engine 不自動判斷每個 uncovered path 是否值得長期保存，也不強迫一檔一頁；這是刻意保留給 agent review 與人工 G3 的語意責任。
- Engine 不判定沉默、模糊同意或 agent 推斷為 approval；explicit human approval 仍是 gate event 的必要條件。G3 只檢查實作對已批准內容的符合性，新需求必須經 `revise`，不能在驗證時默默補入。
- G3 review validator 對 current `passed` 放行、對 unavailable/advisory 發 warning，對 critical finding 要求每個具名 `F-###` 有 acceptance-gate `review-critical` waiver；source fingerprint 改變會讓 review stale，legacy evidence 仍可讀但不能冒充 current independent review。

## Lifecycle boundary

DevWeave 仍是唯一 router；Companion Skills 是階段內方法，不建立第二套 work-item lifecycle、artifact set 或 approval protocol。`diagnosing-bugs` 仍限於既有診斷階段，`tdd` 仍只能在 current G2 approval 後的 implementation 使用。此互動規則不新增 CLI、JSON schema、ledger 欄位或 VS Code UI。

## Extension integration boundary

- `vscode-extension/src/snapshot.ts` 只把 project、work、gate、task、evidence、Wiki 與 diagnostics 投影成 filesystem snapshot；它不執行 Python engine、shell、Git、network 或 Codex API，並與 installer 共用 `bootstrap-compat.ts` semantic validator。
- `vscode-extension/src/presentation.ts` 是 Extension-local 的 presentation seam，集中 public command 任務語言、非權威 snapshot guidance、review readiness、繁中 diagnostic copy 與 audit event mapping；它不改變 Python schema 或 `$devweave` prompt contract。
- `vscode-extension/src/snapshot.ts` 以 optional nested review projection 讀取 result/severity/findings/hash；`presentation.ts` 在 high-risk acceptance 增加 Independent Review check，missing/unavailable/advisory 顯示 attention、critical 顯示 not-ready，Extension 不啟動 Agent 或修改 lifecycle。
- Control Center Webview 以總覽、工作項目、知識、驗證（含稽核）與說明五區分區；active work 與 closed history 分組，Knowledge 列表以 snapshot 內資料提供搜尋、分類與 bounded initial list，使用者可明確顯示全部。
- `setDisplayMode` 只更新 Extension `workspaceState`。初始化仍是使用者確認後的固定 bootstrap write；其他命令只預覽／複製 prompt 到 Codex Chat，送出後由使用者 Refresh 取得新的檔案投影。

## VS Code Extension contract

Control Center 依賴 engine 產生的 filesystem projection，但不把 Extension 當成 machine lifecycle 的權威來源。`WorkspaceSnapshotReader` 只讀取 project、hook、skills、baseline、Wiki 與 Work Item artifacts；`WorkspaceSnapshot.bootstrap` 另外依 bundle destination/hash contract 回報 expected、missing、conflicts 與 complete。`project.json` 存在本身不能代表完整初始化。

Extension 的 Wiki 搜尋不新增 knowledge machine command 或索引服務。`WikiSearchModel` 將輸入拆成 draft 與 applied query，Enter 才套用大小寫不敏感的包含式搜尋，欄位是 title、path 與 body preview；分類是 exact type filter，show-all 只改變可見頁數。Webview 保留輸入 DOM，結果與 metrics 真實 mount 到 `#wiki-results`，`RenderScheduler` 合併同一 event loop 的 local renders。

Watcher refresh 與手動 refresh 共用 `RefreshCoordinator`。Coordinator 一次只允許一個 snapshot read；burst 期間保留最新 pending request，成功結果不被較舊 read 回退。Reader 對互不依賴的檔案操作使用平行讀取，但以 sorted path/id 合併 projection 與 diagnostics，維持 engine contract 的 deterministic output。

Bootstrap bundle 的來源與目的地由 build-time manifest 固定，版本從 package version 產生：`devweave` 加上五個核准 companion skills、通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter。`existingPolicy` 缺少時安全預設 `exact`；只有 project、三份 baseline、三份 Wiki starter 宣告 `adopt-compatible` 與固定 compatibility kind。`BootstrapInstaller.inspect()` 與 snapshot 先做 read-only integrity/path preflight，再以 shared validator 判定 evolved bytes；install 只建立 missing paths，寫入失敗則 rollback 本輪建立的檔案。Dashboard 以 completeness projection 提供初始化／補齊入口。

`vscode-extension/src/preview-gate.ts` 是純 host-side ticket seam；它只接受同一 panel、typed intent、snapshot revision 的 preview bundle，intent 以欄位結構比較避免 delimiter collision，protocol 拒絕危險控制字元，one-shot consume 後才交給 clipboard adapter，revision/selection/refresh 更新會使 ticket stale，clipboard failure 只允許同一 current ticket retry 一次。0.2.1 的 public command handoff 維持原有 `$devweave` command text 與 Python schema：Extension 先預覽、由使用者確認複製到 Codex Chat，完成後 Refresh 取得新 snapshot；多 active work 的 `next` 要求明確 selection，未指定 work 的 `status` 產生 `$devweave status --all`，`copyNextAction` 只開啟 Control Center。

Copy success 的 Webview result 與 native toast 是 consume 後的通知，不屬於 clipboard adapter failure；因此 notification 發生錯誤時不會把已成功 consumed 的 ticket 還原。Host error path 將原始錯誤轉成繁中 primary status，technical detail 只在可展開區域呈現。Configured full-suite raw logs 會保留 bounded fresh/evolved/conflict/rollback/multi-work 與 accessibility markers，供 G3 獨立核驗 walkthrough provenance。

說明內容嵌入 Extension bundle 並在首次切換 help section 時 render；它不落地到 workspace、不發 network request。Extension runtime 維持 no process、no shell、no external network，除使用者確認的固定 bootstrap path 外不提供 workspace write seam。

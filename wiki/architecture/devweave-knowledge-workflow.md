---
title: DevWeave Knowledge Workflow
type: architecture
sources: [.agents/skills/devweave, AGENTS.md, README.md, docs/使用手冊.md, vscode-extension/src]
last_updated: 2026-08-04
tags: [architecture]
status: active
source_fingerprint: "sha256:c33eb5394d8cdbd9f6b95432ea017069afae4c7072bb6c7070e58f0b171eeb84"
verified_by: 20260804-122803-feature-g3-review-agent
---

# DevWeave Knowledge Workflow

## Context

DevWeave 將 Codebase Wiki 納入既有 Work Item lifecycle，而不是建立第二套 Wiki skill 或背景索引服務。Wiki 提供快速定位入口；source 與已核准 artifacts 仍是權威事實來源。互動式 G1/G2 問答是 router 與 phase guidance 的決策協作規則，不是另一個 lifecycle 或 engine state。

## Components and Data Flow

1. `$devweave wiki bootstrap` 由 router 轉成 `knowledge bootstrap`。Engine 先評估 active、sourced、current 的 overview、architecture 與 module；完整時回 `already_complete`，否則 resume 或 create bootstrap-profile feature Work Item。
2. G1 的 `knowledge context` 固定先記錄 index，再記錄最多五頁的 path、status、content hash、stored/computed source fingerprint。Nonfresh、矛盾或不足 knowledge 必須先形成 gap，才允許最小 raw-source fallback；repository 已能證實的事實不轉成使用者問題。
3. G1 由 `grill-me`/`grilling` 逐題處理 material decisions。每題先呈現 context、建議與 tradeoff，等待回答後才回流 `brief.md`/`requirements.md`；`validate` 後的問題、範圍、非目標、驗收與剩餘假設才可送 G1 explicit approval。
4. G2 由 `codebase-design` 逐題處理 design choices。回答回流 `design.md`/`plan.md`，並在 `validate` 後以 Gate Double Check 展示選定/淘汰方案、介面、資料流、失敗處理、回復方式與 immutable task plan；G2 前不修改產品內容或 tracked tests。
5. G2 決定 bootstrap 的三至五個高價值頁或一般工作的 product design；Wiki 到 verification 前皆唯讀。使用者改變已批准答案或 Gate 發現新決策時，透過 `revise` 使受影響 Gate 失效並回到最早階段。
6. High-risk G3 在 final product/Wiki/baseline/diff/scope/evidence 穩定後，由唯一 router 啟動 exactly one isolated read-only Independent Review Agent。Reviewer 只能讀取 approved artifacts、完整 diff、risk/scope、baseline、Wiki context 與 evidence，不繼承主 Agent reasoning，也不能寫 source/Wiki/ledger 或 approve/revise/close；G2 `Design It Twice` 的 3+ design sub-agents 是不同階段的 optional comparison。
7. Router 將固定 JSON report 寫到 incoming cache，透過 machine-only `review record` 交給 engine。Engine 驗證 incoming 與 final log cache 的逐層 containment（含 symlink escape）、size、enum、AC/TASK coverage 與 current source fingerprint，redact secrets，寫入 `kind: review` evidence、Git HEAD、report hash、reviewer ID、context mode 與 bounded raw report；Python engine 不 spawn Agent。
8. Verification 的 `knowledge review` 保存 disposition、rationale、affected/covered/uncovered paths 與 product change fingerprint。後續產品 fingerprint 改變會使 knowledge review、plan 與 source-bound review evidence invalid，並要求重新審查。
9. `promote` 建立一至五個 content upsert/delete；新頁經 canonical scaffold 先成為 placeholder。完成 active 內容後同步 index、append-only log，再 seal source fingerprint 與 Work Item provenance。`no-update` 僅在非 bootstrap、無 affected page、無 Wiki diff 時成立。
10. G3 重新比對完整 Wiki diff、affected pages、plan、coupling、log、seal、baseline、current evidence 與 Independent Review。`passed` 正常通過；unavailable/advisory 形成 warning；critical security/data-loss/irreversible/scope finding 只有 exact named `review-critical` acceptance waiver 可解除。它只驗證實作是否符合已批准內容，不默默補入新需求或設計。人工核准後才可 close。

## VS Code Control Center integration

VS Code Extension 是這條 lifecycle 的唯讀 projection client。Host 以 `WorkspaceSnapshotReader` 讀取 project、work item、Wiki、evidence 與 bootstrap completeness；它不執行 Python engine、shell、Git、network 或 Codex API。使用者確認初始化後，`BootstrapInstaller` 才能套用 0.2.0 allowlisted control bundle；部分 workspace 只補齊缺檔，既有不同 bytes 的檔案保留為 conflict。

Knowledge section 的查詢是 Extension-local 行為，不會改寫 G1 context 或 Wiki：`WikiSearchModel` 保留 draft/applied query，按 Enter 後才以 case-insensitive contains 搜尋 title、path 與 body preview；type filter 是精確匹配，結果與 metric 透過局部 render 更新。檔案 watcher 仍自動 refresh，但由 250ms debounce、single-flight 與 latest-pending coordinator 合併 burst，snapshot 的平行讀取最後以 deterministic order 合併。

說明頁是 Extension bundle 內的 lazy local content，不寫入 target repository，也不需要網路。這些 UI／package 知識在 G3 promote 更新，若需求或設計改變仍須回到同一 Work Item 的 `revise` 與 Gate lifecycle。

## Boundaries

- `knowledge_core` 不讀寫 Work Item ledger；`devweave_core` 在 WorkLock 內擁有 lifecycle 與 event policy；CLI 只做 JSON adapter。
- Guard 只允許 verification 中 knowledge plan 的 content paths，以及自動 coupling 的 `wiki/index.md`、`wiki/log.md`。
- Review Agent 的啟動權只在既有 router；Python engine 只記錄 machine report，Extension 只投影 readiness，三者不產生第二個 lifecycle 或平行 ledger。
- 互動式問答由 router/phase guidance 約束；不新增 pending-question state、CLI、JSON schema、VS Code UI 或第二套 question ledger。沉默與模糊同意不構成 approval，未回答的 material decision 會停在目前階段。
- 每頁最多五個 sources；每次 context 最多五個內容頁；每次 promotion 最多五個 content targets。
- Bootstrap 不接受 repository 子路徑 scope，不修改產品 source，且需 promote overview、至少一個 architecture、至少一個 module。
- Extension 不建立 process/network seam，也不自行重算 Git/source fingerprint；其 bootstrap 與 Independent Review readiness 判定都是非權威 filesystem projection。

## Evidence and Gaps

- Lifecycle、legacy compatibility、source invalidation、bootstrap G1→G3、九種 scaffold、guard 與 seal 由 Python regression 覆蓋。
- Extension intent parity、strict protocol、unknown state fail-closed、no-process/no-network、package 與 Extension Host activation 由 unit/security/typecheck/package/smoke 驗證。
- Durable value 是語意判斷，machine 只能提供 coverage 與 affected-page obligation；最終由 Knowledge Review rationale 與 G3 人工核准承擔。Repository contract tests 可檢查政策存在，實際對話是否逐題等待仍需以運行時情境驗收。

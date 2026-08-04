---
title: DevWeave Knowledge Workflow
type: architecture
sources: [.agents/skills/devweave, AGENTS.md, README.md, docs/使用手冊.md]
last_updated: 2026-08-04
tags: [architecture]
status: active
source_fingerprint: "sha256:8ffca49e8f46595f0f943593670dfd0550045977d3b710051061637e6e0f3ad5"
verified_by: 20260804-085630-feature-g1-g2
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
6. Verification 的 `knowledge review` 保存 disposition、rationale、affected/covered/uncovered paths 與 product change fingerprint。後續產品 fingerprint 改變會使 review invalid，並清空 plan/seals。
7. `promote` 建立一至五個 content upsert/delete；新頁經 canonical scaffold 先成為 placeholder。完成 active 內容後同步 index、append-only log，再 seal source fingerprint 與 Work Item provenance。`no-update` 僅在非 bootstrap、無 affected page、無 Wiki diff 時成立。
8. G3 重新比對完整 Wiki diff、affected pages、plan、coupling、log、seal、baseline 與 current evidence；它只驗證實作是否符合已批准內容，不默默補入新需求或設計。人工核准後才可 close。

## Boundaries

- `knowledge_core` 不讀寫 Work Item ledger；`devweave_core` 在 WorkLock 內擁有 lifecycle 與 event policy；CLI 只做 JSON adapter。
- Guard 只允許 verification 中 knowledge plan 的 content paths，以及自動 coupling 的 `wiki/index.md`、`wiki/log.md`。
- 互動式問答由 router/phase guidance 約束；不新增 pending-question state、CLI、JSON schema、VS Code UI 或第二套 question ledger。沉默與模糊同意不構成 approval，未回答的 material decision 會停在目前階段。
- 每頁最多五個 sources；每次 context 最多五個內容頁；每次 promotion 最多五個 content targets。
- Bootstrap 不接受 repository 子路徑 scope，不修改產品 source，且需 promote overview、至少一個 architecture、至少一個 module。
- Extension 不建立 process/network seam，也不自行重算 Git/source fingerprint；其 bootstrap 判定是非權威 filesystem projection。

## Evidence and Gaps

- Lifecycle、legacy compatibility、source invalidation、bootstrap G1→G3、九種 scaffold、guard 與 seal 由 Python regression 覆蓋。
- Extension intent parity、strict protocol、unknown state fail-closed、no-process/no-network、package 與 Extension Host activation 由 unit/security/typecheck/package/smoke 驗證。
- Durable value 是語意判斷，machine 只能提供 coverage 與 affected-page obligation；最終由 Knowledge Review rationale 與 G3 人工核准承擔。Repository contract tests 可檢查政策存在，實際對話是否逐題等待仍需以運行時情境驗收。

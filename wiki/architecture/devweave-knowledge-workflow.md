---
title: DevWeave Knowledge Workflow
type: architecture
sources: [.agents/skills/devweave, AGENTS.md, README.md, docs/使用手冊.md]
last_updated: 2026-08-03
tags: [architecture]
status: active
source_fingerprint: "sha256:ba2bcd855f38e1964db2f5a124a0a291594277c40863827ba6b4cf2772e1177b"
verified_by: 20260803-161041-feature-codebase-llm-wiki
---

# DevWeave Knowledge Workflow

## Context

DevWeave 將 Codebase Wiki 納入既有 Work Item lifecycle，而不是建立第二套 Wiki skill 或背景索引服務。Wiki 提供快速定位入口；source 與已核准 artifacts 仍是權威事實來源。

## Components and Data Flow

1. `$devweave wiki bootstrap` 由 router 轉成 `knowledge bootstrap`。Engine 先評估 active、sourced、current 的 overview、architecture 與 module；完整時回 `already_complete`，否則 resume 或 create bootstrap-profile feature Work Item。
2. G1 的 `knowledge context` 固定先記錄 index，再記錄最多五頁的 path、status、content hash、stored/computed source fingerprint。Nonfresh、矛盾或不足 knowledge 必須先形成 gap，才允許最小 raw-source fallback。
3. G2 決定 bootstrap 的三至五個高價值頁或一般工作的 product design；Wiki 到 verification 前皆唯讀。
4. Verification 的 `knowledge review` 保存 disposition、rationale、affected/covered/uncovered paths 與 product change fingerprint。後續產品 fingerprint 改變會使 review invalid，並清空 plan/seals。
5. `promote` 建立一至五個 content upsert/delete；新頁經 canonical scaffold 先成為 placeholder。完成 active 內容後同步 index、append-only log，再 seal source fingerprint 與 Work Item provenance。`no-update` 僅在非 bootstrap、無 affected page、無 Wiki diff 時成立。
6. G3 重新比對完整 Wiki diff、affected pages、plan、coupling、log、seal、baseline 與 current evidence；人工核准後才可 close。

## Boundaries

- `knowledge_core` 不讀寫 Work Item ledger；`devweave_core` 在 WorkLock 內擁有 lifecycle 與 event policy；CLI 只做 JSON adapter。
- Guard 只允許 verification 中 knowledge plan 的 content paths，以及自動 coupling 的 `wiki/index.md`、`wiki/log.md`。
- 每頁最多五個 sources；每次 context 最多五個內容頁；每次 promotion 最多五個 content targets。
- Bootstrap 不接受 repository 子路徑 scope，不修改產品 source，且需 promote overview、至少一個 architecture、至少一個 module。
- Extension 不建立 process/network seam，也不自行重算 Git/source fingerprint；其 bootstrap 判定是非權威 filesystem projection。

## Evidence and Gaps

- Lifecycle、legacy compatibility、source invalidation、bootstrap G1→G3、九種 scaffold、guard 與 seal 由 Python regression 覆蓋。
- Extension intent parity、strict protocol、unknown state fail-closed、no-process/no-network、package 與 Extension Host activation 由 unit/security/typecheck/package/smoke 驗證。
- Durable value 是語意判斷，machine 只能提供 coverage 與 affected-page obligation；最終由 Knowledge Review rationale 與 G3 人工核准承擔。

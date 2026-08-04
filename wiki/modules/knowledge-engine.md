---
title: Knowledge Engine
type: module
sources: [.agents/skills/devweave/assets/wiki/templates, .agents/skills/devweave/scripts, tests, vscode-extension]
last_updated: 2026-08-03
tags: [module]
status: active
source_fingerprint: "sha256:c23474109c03e2b312dd51d5be702deed2f6b9b2c730a9a48c81e01a1018493d"
verified_by: 20260803-215202-feature-devweave-control-center-ux
---

# Knowledge Engine

## Responsibility

Knowledge Engine 是 DevWeave 既有 Python engine 內的深模組組合。`knowledge_core.py` 提供純 Wiki/source 運算與安全檔案操作；`devweave_core.py` 將這些能力綁定 Work Item phase、gate、review、plan、event 與 acceptance policy；`devweave.py` 暴露穩定 JSON machine commands。

## Public Surface

- `knowledge bootstrap`：repository-wide assessment，回傳 `already_complete|resume|created`。
- `knowledge status`：回報 health、bootstrap reasons、affected pages、covered/uncovered changed paths、review currentness 與 planned updates。
- `knowledge context`：replace G1 ordered context，強制 index-first、最多五個內容頁與 nonfresh gap。
- `knowledge review`：在 current G2 後記錄 `promote|no-update`；產品 source fingerprint 改變時失效。
- `knowledge plan`：replace 一至五個 content targets，自動 coupling index/log。
- `knowledge scaffold`：只對 planned new upsert，以九種 canonical template 進行 exclusive create。
- `knowledge seal`：只接受 planned upserts/coupled pages，拒絕 placeholder、template token、invalid source 與 critical lint。

## Dependencies

- Runtime 僅使用 Python standard library 與 Git CLI；沒有向量資料庫、全文檢索服務或 Token instrumentation。
- Source/page path 必須 normalize 為 repository-relative；Wiki、`.devweave` 與 `.git` 不得成為 page source。
- Source fingerprint 納入 tracked 與非 ignored untracked content、dirty bytes、rename/delete 與 branch identity；Wiki 與 framework ledger 不污染 product evidence fingerprint。
- Canonical templates 位於 `.agents/skills/devweave/assets/wiki/templates/`，是 engine-owned inputs；live knowledge 固定在根 `wiki/`。

## Behavior and Gaps

- Bootstrap readiness 要求無 critical lint，且 overview、architecture、module 皆 active、sourced、current 並有 `verified_by`；既有 Wiki 超過五頁仍可視為完成。
- `affected_pages` 依 Work Item 起始 Wiki source overlap 計算；既有 affected page 在 G3 必須 refresh/seal 或 delete。Coverage 將 current active pages 的 source overlap 投影成 covered/uncovered，供 durable-value review 判斷。
- 新式 state 以 `knowledge_review_required: true` 啟用完整 contract；缺少 marker 的 schema-v1 Work Item 維持 legacy compatibility，不追溯阻擋。
- Scaffold 採 no-overwrite create；seal 先完成所有候選 preflight，再以 per-file atomic replace 寫 provenance。多檔 I/O 仍是逐檔 atomic，最終完整性由 G3 reconciliation 保證。
- Engine 不自動判斷每個 uncovered path 是否值得長期保存，也不強迫一檔一頁；這是刻意保留給 agent review 與人工 G3 的語意責任。

## Extension integration boundary

- `vscode-extension/src/snapshot.ts` 只把 project、work、gate、task、evidence、Wiki 與 diagnostics 投影成 filesystem snapshot；它不執行 Python engine、shell、Git、network 或 Codex API。
- `vscode-extension/src/presentation.ts` 是 Extension-local 的 presentation seam，集中 public command 任務語言、非權威 snapshot guidance、review readiness、diagnostic copy 與 audit event mapping；它不改變 Python schema 或 `$devweave` prompt contract。
- Control Center Webview 以總覽、工作項目、知識、驗證與稽核分區；active work 與 closed history 分組，Knowledge 列表以 snapshot 內資料提供搜尋、分類與 bounded initial list，使用者可明確顯示全部。
- `setDisplayMode` 只更新 Extension `workspaceState`。初始化仍是使用者確認後的固定 bootstrap write；其他命令只預覽／複製 prompt 到 Codex Chat，送出後由使用者 Refresh 取得新的檔案投影。

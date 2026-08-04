# 功能驗收：修正 G1/G2 問答、Wiki 初始化與 Extension bundle 相容性

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260804-183511-feature-g1-g2-wiki-extension-bundle -->

## 驗證矩陣

本次驗證使用目前產品 source fingerprint `96a3076a11277a276679acc0274f0e4520e1e7258a795643a59ffc33a73ecb59`，Git HEAD 為 `6c75f4d289243306c8f469f27ac1f3c5cb9ee8d0`。

| 驗收條件 | 任務 | current evidence | 結果 |
| --- | --- | --- | --- |
| AC-001 native-first G1 問答 | TASK-001 | EVID-017 | 通過；原生 question facility 契約、推薦選項、trade-off、Other 與單題流程已同步文件與 regression。 |
| AC-002 structured fallback | TASK-001 | EVID-017 | 通過；host 不可用時保留 numbered fallback 與明確自訂答案。 |
| AC-003 不新增 lifecycle/state/Gate | TASK-001 | EVID-017 | 通過；沒有新增 question state、CLI、schema、ledger 或 Gate 語義。 |
| AC-004 custom-only Wiki 初始化 | TASK-002 | EVID-019 | 通過；notes-only/custom-only root 可保留既有 bytes 並只補 reserved starters。 |
| AC-005 Wiki conflict 不留 partial state | TASK-002 | EVID-019 | 通過；reserved type/frontmatter conflict 在 `.devweave` control state 建立前 fail closed。 |
| AC-006 bootstrap advisory 邊界 | TASK-005 | EVID-019 | 通過；普通新／feature 工作的 missing bootstrap 為 advisory，bootstrap profile 仍沿既有 lifecycle。 |
| AC-007 evolved bundle adoption | TASK-003、TASK-004 | EVID-014、EVID-017 | 通過；project、三份 baseline、三份 Wiki starter 依宣告的 semantic contract 採用合法 evolved bytes。 |
| AC-008 invalid/malformed fail-closed | TASK-003、TASK-004 | EVID-014、EVID-017、EVID-018 | 通過；unknown metadata、invalid identity/content、integrity/path/type conflict 均在寫入前拒絕。 |
| AC-009 provenance/integrity compatibility | TASK-004 | EVID-017 | 通過；shared validator、manifest metadata、snapshot/installer 一致性與 security boundary 有 regression coverage。 |
| AC-010 Extension safety/regression | TASK-004、TASK-005 | EVID-015、EVID-017、EVID-018、EVID-019 | 通過；Extension smoke、60 項 unit/security、typecheck 與 Python repository suite 均通過。 |

EVID-003 至 EVID-013 是較早 verification/review attempt 的紀錄，因 evidence linkage revision 已正式標為 stale；current profile 以 EVID-014、EVID-015、EVID-017、EVID-018、EVID-019 為準。EVID-006 的第一次 package 嘗試因 sandbox 對 esbuild 的目錄讀取限制失敗；未用作通過依據。EVID-016 的 Extension test 嘗試因 Windows `cp950` console encoding 中斷且沒有建立 evidence；之後以 UTF-8 mode 完成 EVID-017。EVID-020 是 current isolated review 的 machine record。

## Profile 證據

本 Work Item 為 high-risk feature，已完成 feature acceptance、regression 與 high-risk review 要求的前置驗證：

- `python -B -m unittest discover -s tests -v`：94 項通過，1 項因 Windows symlink privilege skip（EVID-012）。
- `npm run test`：60/60 通過（EVID-017）。
- `npm run typecheck`：通過（EVID-018）。
- `npm run package`：產生 0.2.0 VSIX，驗證 57 個 bootstrap files、108 個 VSIX entries（EVID-014）。
- `npm run test:smoke`：VS Code Extension Host activation 與既有 commands 通過（EVID-015）。
- `git diff --check`：驗收前後均未發現 whitespace error；僅有 Windows checkout 的 LF/CRLF conversion warning。

## 基線更新

已透過 DevWeave baseline declaration 更新並驗證三份 accepted governance truth：

- `.devweave/baseline/product.md`：native-first G1/G2 問答、Wiki reserved-starter preflight/custom-only 行為，以及七個資料 contract 的 semantic adoption 邊界。
- `.devweave/baseline/architecture.md`：lock 外／內的 Wiki preflight、Extension `bootstrap-compat.ts` shared seam，以及 manifest 的 exact/adopt-compatible 宣告。
- `.devweave/baseline/quality.md`：custom-only compatibility、semantic adoption 的 fail-closed 限制、94+1 Python suite、60 項 Extension suite 與 package 產物數量。

三個 target 均已由 `baseline --target` 宣告，沒有 undeclared baseline diff。

## Wiki 知識提升

Knowledge Review 為 `promote`，理由是本次形成可重用的 native-first decision interface、Wiki reserved-starter initialization order、bootstrap advisory boundary 與 Extension semantic bundle compatibility。

- affected pages：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`。
- plan：四個 content upsert、零 delete；由 engine coupling `wiki/index.md` 與 `wiki/log.md`。
- 所有受影響頁面已完成 active/sourced/current seal，沒有 placeholder、template token、uncovered changed path 或 critical lint warning。
- seal 使用 product change fingerprint `96a3076a11277a276679acc0274f0e4520e1e7258a795643a59ffc33a73ecb59`；封存後 knowledge fingerprint 為 `2d398bdfc48a9d0648cfdefa070e0e7dc13f2c9e9bd877eefbe8c78d667a467f`。
- bootstrap core 現在為 complete；普通工作不會因 missing bootstrap 被阻擋。

## 殘餘風險

無 named `review-critical` waiver。已知限制如下：

- native question facility 是否可用由 Codex host 決定，因此 repository 只保證 native-first 的選項契約與等價 numbered fallback。
- Windows symlink privilege 使一項 Python 測試 skip；其餘 suite 通過，相關 symlink safety 仍由既有測試與 G3 reconciliation 覆蓋。
- EVID-006 僅代表受限 sandbox 的一次失敗嘗試；EVID-014 已在核准環境重跑相同 package command 並通過。
- `WAIVER-001` 是針對 package-derived `vscode-extension/devweave-control-center-0.2.0.vsix` 的窄幅 out-of-scope waiver，不涵蓋其他 Extension source 或 behavior。
- VS Code Extension 仍是 filesystem-only、non-authoritative projection，不會代替 Python engine 執行 lifecycle 或自動修復 critical state。

## 獨立 Review

EVID-013 屬於 evidence-linkage revision 前一個 G3 attempt 的唯一 review record，已依 lifecycle 正式標 stale。Current high-risk G3 attempt 的唯一 reviewer machine record 為 EVID-020：`result=unavailable`、`severity=none`、`context_mode=isolated_read_only`、無 findings；原因是 bounded review 在完整 source/diff reconciliation 前被中止。依固定協定這是 warning，不是 critical finding；沒有需要 waiver 的 named `F-###`。

## 驗收結論

三項使用者需求均已完成實作與 current regression：G1/G2 改為 Codex host 原生選項問答並保留結構化 fallback；Wiki 初始化先做 reserved-starter preflight、支援 custom-only root 並在 conflict 前不留下 partial control state；Extension 對七個明確資料 contract 採 semantic adoption，避免既有合法內容被誤判為需補齊或被覆寫。

Independent Review 已完成 current machine record；目前只尚待使用者明確 G3 approval，在此之前不執行 close。

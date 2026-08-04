# 功能驗收：建立 G1/G2 互動式決策流程

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260804-085630-feature-g1-g2 -->

## 驗證矩陣

| 驗收條件 | 對應工作 | 證據 | 結果 |
| --- | --- | --- | --- |
| AC-001：G1 只詢問未決的 material decision，facts 由 repository 查證 | TASK-001, TASK-004 | EVID-007 | 通過；政策與 artifacts review 確認 `grill-me`/`grilling`、逐題提問、推薦/取捨與等待規則。 |
| AC-002：G1 回答回流並在 validate 後等待明確核准 | TASK-001, TASK-004 | EVID-007 | 通過；確認答案回流既有 artifacts、Gate summary 與 explicit approval 邊界。 |
| AC-003：G2 使用 `codebase-design` 並禁止提前實作 | TASK-001, TASK-004 | EVID-007, EVID-006 | 通過；文件/手動 review 確認 G2 write boundary，完整 Python suite 通過。 |
| AC-004：G2 Double Check 與 `revise` 回退 | TASK-001, TASK-004 | EVID-007 | 通過；確認 validate 後摘要、明確 G2 approval，以及新決策回到最早受影響 phase。 |
| AC-005：文件與 repository contract policy 一致 | TASK-002, TASK-003, TASK-004 | EVID-006, EVID-007 | 通過；完整 Python unittest 84 tests 全數通過，包含 interactive policy contract test。 |
| AC-006：不改變既有 machine/runtime contract | TASK-003, TASK-004 | EVID-002, EVID-003, EVID-004, EVID-005, EVID-006 | 通過；Extension package/smoke/tests/typecheck 與完整 Python suite 均通過，未新增 CLI、schema、ledger 或 UI。 |

所有 command evidence 使用同一 current source fingerprint：`2eacac76afb96b89e70570d54097027a36c3e6b3a89f374b1609461e1f661108`；stale evidence 為 0。EVID-001 是受 sandbox ACL 影響的第一次 package 診斷失敗；同一 `extension-package` 命令在允許的執行環境重跑為 EVID-002 並成功，不代表產品 package 失敗。

## Profile 證據

本 Work Item 為 `feature`，已完成 acceptance 與 regression：

- `extension-package`：EVID-002 passed。
- `extension-smoke`：EVID-003 passed，Extension Host smoke 完成。
- `extension-tests`：EVID-004 passed，17 個 subtests 全數通過。
- `extension-typecheck`：EVID-005 passed。
- `unit-tests`：EVID-006 passed，Python unittest 84 tests 全數通過。
- repository contract targeted suite：8/8 passed；`git diff --check` passed（僅有 Windows LF/CRLF normalization warnings）。
- 手動 acceptance review：EVID-007 passed；它驗證政策與 artifacts，實際未來 agent 對話仍需運行時情境觀察。

## 基線更新

不更新 `.devweave/baseline/`。本次只調整 router/phase policy、root policy、使用文件、repository contract test 與 G3 Knowledge Review Wiki；未改變既有 machine lifecycle、runtime boundary、產品目標或驗證命令。已透過 DevWeave baseline command 記錄 no-update rationale，targets 為空。

## Wiki 知識提升

Knowledge Review disposition 為 `promote`。理由是本次 G1/G2 關鍵決策問答、Gate Double Check 與 `revise` 回流規則屬於可重用的 workflow knowledge，且既有三個內容頁受影響。

- affected pages：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`。
- covered changed paths：`AGENTS.md`、`README.md`、`docs/使用手冊.md`、`tests/test_repository_contract.py`；uncovered paths：無。
- upsert：上述三個內容頁；delete：無。
- coupled：`wiki/index.md`、`wiki/log.md`；log 已 append 一筆 `20260804-085630-feature-g1-g2` promote entry。
- seal：三個內容頁與 index/log 均已由 `knowledge seal` 封存；目前 `knowledge status` 為 `healthy`，pending refresh、stale pages、unsealed pages、critical warnings 均為空。
- bootstrap assessment 在 promotion 後已達 overview、architecture、module current readiness；本 work 不需另建 bootstrap work item。

## 殘餘風險

- `devweave bind` 在本 session 仍回報 `awaiting_hook`、`bound_at: null`；因此本驗收不宣稱 Codex hook guard 已啟用。這是執行環境限制，不改寫 work item policy，也不以它冒充 Gate approval。
- EVID-007 只能由 policy/artifact review 證明規則已落盤，無法單靠 repository contract test 保證每次未來 agent 對話都會真實逐題等待；需以手動運行時情境持續觀察。
- 無 waiver；沒有 product source、tracked test（本次新增的 policy contract test 除外）、Python engine、schema、ledger、VS Code runtime、Companion Skill 或 `skills-lock.json` 變更。

## 驗收結論

本次已完成「自動查證事實 → G1/G2 逐題確認關鍵決策 → artifacts → Gate Double Check → G3 conformance verification」的政策落地。G1、G2 已由使用者明確核准；所有 standard verification、contract tests、Wiki promote/seal 與 baseline rationale 均已完成。剩餘事項只有 G3 的人工確認，以及後續實際對話對「逐題等待」的運行時觀察。

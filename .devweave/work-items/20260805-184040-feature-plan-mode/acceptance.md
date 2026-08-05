# 功能驗收：初始 Plan Mode 導流

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260805-184040-feature-plan-mode -->

## 驗證矩陣

目前 source fingerprint：`1c6fe9728f1d0703e8bb1ffe71a8de6e80d15bda54df5953764326486fe69e8a`；Git HEAD：`248814fc01f0d0c76988efcf85c6b4a5711a0fbc`。

| AC | TASK | current evidence | 結果 |
| --- | --- | --- | --- |
| AC-001 | TASK-001、TASK-007、TASK-008 | EVID-018 | Python full suite 103 tests 通過，確認 Router/native-question contract 與 pre-G2 mutation ordering。 |
| AC-002 | TASK-001、TASK-007、TASK-008 | EVID-018 | 確認未取得 `request_user_input` host capability 時必須停止；compatibility fallback 只由明確選擇啟用。 |
| AC-003 | TASK-001、TASK-007、TASK-008 | EVID-018 | 確認 `start`、`bind`、`revise` 與 bootstrap Work Item 建立前的 Plan Mode preflight 契約。 |
| AC-004 | TASK-002、TASK-003、TASK-004、TASK-008 | EVID-019、EVID-020 | `PlanModeGuidance` 依 command／phase 正確產生；`PromptBundle`／`SnapshotGuidance` optional metadata 與 typecheck 通過。 |
| AC-005 | TASK-002、TASK-003、TASK-004、TASK-008 | EVID-018、EVID-019 | `chatText` 保持原本 `$devweave ...` 內容；無 fake adapter、host command、checkbox 或 Extension mode switch。 |
| AC-006 | TASK-003、TASK-004、TASK-008 | EVID-019、EVID-022 | 無 active work、pre-G2 overview、mutation preview 與 copy flow 均保留 Plan Mode handoff，copy 仍可用。 |
| AC-007 | TASK-003、TASK-004、TASK-008 | EVID-019、EVID-022 | stale preview、multiple active work、selection、post-G2 approved task 與既有 preview safety 行為維持。 |
| AC-008 | TASK-005、TASK-006、TASK-008 | EVID-021、EVID-022 | 0.2.2 package、VS Code Extension Host smoke 通過；bootstrap 與 release artifact 邊界正確。 |
| AC-009 | TASK-002、TASK-003、TASK-004、TASK-005、TASK-006、TASK-008 | EVID-018、EVID-019、EVID-020、EVID-021、EVID-022 | Python／Extension tests、typecheck、package、smoke 均為 current passing evidence；`git diff --check` 無 whitespace error。 |

Current passing evidence：EVID-018（103 tests，581.685 秒，`skipped=1`）、EVID-019（Extension 77 tests）、EVID-020（typecheck）、EVID-021（0.2.2 VSIX，58 bootstrap files／119 entries）、EVID-022（Extension Host smoke，Exit 0）。

歷史診斷 evidence EVID-001 至 EVID-017 已由後續 source-bound evidence 取代或標記 stale；其中 timeout、sandbox ACL、暫存 pycache package 與舊測試計數問題均未作為本次 current pass。

## Profile 證據

本 Work Item 為 `feature`，因此以 acceptance 與 regression 共同驗證。EVID-018 是完整 Python acceptance；EVID-019 是 Extension regression suite；EVID-020 是 Extension typecheck；EVID-021 是 package profile；EVID-022 是 VS Code Extension Host acceptance smoke。所有 current evidence 均綁定上述 source fingerprint。

## 基線更新

已透過 DevWeave baseline CLI 更新並保留三個 accepted baseline：

- `.devweave/baseline/product.md`：記錄 pre-G2 Plan Mode 導流、explicit compatibility fallback、Control Center handoff 與 0.2.2／0.2.1 artifact 狀態。
- `.devweave/baseline/architecture.md`：記錄 Router host capability seam、mutation ordering、optional guidance metadata 與 chatText compatibility。
- `.devweave/baseline/quality.md`：記錄 103 Python tests、77 Extension tests、0.2.2 package／smoke 結果與 600 秒 unit-tests timeout；EVID-018 以 581.685 秒通過。

`git diff --check` 已執行並通過；輸出只有 Windows 對 LF／CRLF 的一般警告。

## Wiki 知識提升

Knowledge Review disposition 為 `promote`，理由是本次變更會持續影響 Router preflight、native-question contract、Extension guidance 與 release／quality baseline。affected content pages 為四頁：

- `wiki/overview.md`
- `wiki/architecture/devweave-knowledge-workflow.md`
- `wiki/modules/knowledge-engine.md`
- `wiki/modules/vscode-extension.md`

Knowledge plan 只 upsert 上述四個內容頁，並耦合更新 `wiki/index.md` 與 `wiki/log.md`；沒有 delete，未超過五個內容頁。六頁均已由本 Work Item sealed，最後 Knowledge status 為 `healthy`，無 placeholder、critical lint、stale page 或 pending refresh。

## 殘餘風險

1. Codex host 的 Plan Mode 切換仍是使用者操作；Router 只能以 `request_user_input` 可見性判斷 capability，Extension 不讀取或切換 host mode。實際 host 切換未由此 repository test 自動模擬，需在手動驗收時確認。
2. Python full suite 有一項 Windows symlink privilege 案例 skipped；EVID-018 已明確記錄，需在同一 build、具 symlink 權限的隔離環境補驗後才可宣稱完整無 skip。
3. package／smoke 使用 elevated Windows 執行以避開 Extension Host／esbuild ACL 限制；VS Code Host 已以 Exit 0 完成 smoke。沒有 review-critical finding，也沒有 waiver。

其餘既有 multiple active work、stale preview、post-G2 與 bootstrap write-boundary 行為由 current tests／smoke 覆蓋，無新增已知風險。

## 驗收結論

實作、文件、baseline、Wiki promote、current acceptance／regression evidence、typecheck、package 與 smoke 均已完成。Router 在 pre-G2 mutation 前要求 Plan Mode；host capability 不可見時停止並提示切換，只有使用者明確選擇 compatibility 才進入 numbered structured fallback。Control Center 以 optional `PlanModeGuidance` 提示 handoff，維持原有 `$devweave ...` chatText 與 copy 能力。

本 Work Item 已具備進入 G3 人工核准的條件；尚未代替使用者核准 G3，也尚未 close Work Item。

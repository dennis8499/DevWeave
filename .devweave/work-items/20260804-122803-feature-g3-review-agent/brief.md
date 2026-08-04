# 工作摘要：高風險 G3 獨立 Review Agent

<!-- DEVWEAVE:artifact=brief version=1 work=20260804-122803-feature-g3-review-agent kind=feature -->

## 問題與目標

DevWeave 的 high-risk G3 目前只要求一筆 `kind: review` evidence，沒有要求 router 實際啟動隔離 reviewer，也沒有保存 reviewer provenance、原始報告或 unavailable/critical 結果。這使「independent review」停留在文件與摘要層，無法讓 maintainer 或人類 reviewer 確認審查是否真的發生。

本 feature 要在 high-risk Work Item 完成最終 verification 後，由唯一 DevWeave router 啟動一個隔離、唯讀的 Review Agent；由 Python engine 接收並保存結果、原始報告與 current source provenance，並讓 G3 清楚區分可接受 warning 與必須處理的 critical finding。

成功訊號：high-risk G3 會有一次可追溯的 reviewer attempt；passed review 正常通過、unavailable/timeout 形成不阻擋的 warning、critical finding 阻擋 G3（除非有明確窄幅 waiver），而 standard/low-risk Work Item 不啟動 reviewer。

## 現況證據

### Wiki facts

- `wiki/index.md` 指向 overview、DevWeave workflow、Knowledge Engine 與 VS Code Extension 四個相關頁面；本 Work Item 已以 index-first 順序記錄這五頁的 status、content hash 與 source fingerprint。
- Wiki 已確認 DevWeave 是唯一 lifecycle router，Extension 是唯讀 projection，G3 會檢查 current evidence、baseline、Wiki 與人工核准。

### Source-backed facts

- `devweave_core.py` 的 G3 validation 目前只在 high risk 將 `review` 加入 required evidence kinds，沒有 reviewer identity、report、result severity 或 raw report contract。
- `add_evidence` 目前只保存一般摘要、AC/TASK、source fingerprint、Git HEAD 與 optional raw log；沒有 review-specific record API。
- `devweave.py` 目前沒有 machine-only `review record` command。
- VS Code `WorkspaceSnapshotReader` 會投影 evidence，`presentation.ts` 的 readiness 目前沒有 high-risk independent-review check。
- `Design It Twice` 已提供 G2 在使用者需要替代介面時啟動 3+ sub-agents 的方法；這不是本 feature 要改寫的 G3 行為。

### Inferences

- Agent spawn 必須位於 Codex/router orchestration layer；Python engine 應保持 deterministic state/evidence authority，不應加入第二個 orchestrator 或 child-process runtime。
- 由於 reviewer 會讀取完整 final diff，應在產品、baseline、Wiki promotion 與必要 evidence 穩定後、G3 summary 前執行。

### Unresolved gaps

- Wiki 未描述 high-risk G3 isolated reviewer、review provenance、unavailable warning 與 critical finding gate 行為；已在 `knowledge context` 中記錄 gap，source 與已核准 artifacts 作為後續設計依據。

## 範圍

本 Work Item 包含：

- high-risk G3 的單一隔離唯讀 reviewer invocation contract 與固定 reviewer output contract。
- machine-only `review record` CLI/engine seam、review evidence schema、raw report cache、report hash、opaque reviewer provenance 與 current source invalidation。
- unavailable/timeout/malformed output 的 warning 行為、advisory findings、critical findings 與 `review-critical` 窄幅 waiver 的 G3 validation。
- `SKILL.md`、verification phase、contracts、AGENTS、README、使用手冊與 accepted baseline 的政策同步。
- VS Code Control Center 的 high-risk Independent Review readiness projection 與相關 regression tests。
- Python engine/CLI、repository contract、Extension unit/typecheck/package/smoke 與手動 reviewer-flow 驗收。

## 非目標

以下不在範圍內：

- 不為 standard/low-risk Work Item 自動啟動 reviewer。
- 不新增公開 `$devweave` chat verb、第二套 work-item lifecycle、第二個 router 或獨立 orchestrator。
- 不讓 Python engine 自行 spawn Agent、執行 Codex API、shell、network 或 child process。
- 不改變 G2 `Design It Twice` 的條件式 3+ sub-agent 設計比較流程。
- 不回溯 reopen 已 closed Work Item，也不直接修改既有 JSON/JSONL ledger。
- 不把 reviewer 報告寫入獨立 tracked spec；完整報告只由 engine 保存至 work item cache，摘要與 provenance 進入 evidence。

## 風險

風險等級：high

本變更改寫 high-risk G3 的 evidence/validation contract，影響治理安全、人工 gate、CLI schema、Extension projection 與 repository policy。主要風險是 reviewer output 不可信、Agent 不可用、敏感資料進入 raw report、source 在 review 後變更，以及 UI 與 engine currentness 不一致。

緩解方式是隔離 context、唯讀 reviewer prompt、bounded report/cache、secret redaction、repo-relative path containment、source fingerprint、critical finding blocker、窄幅 waiver、engine-owned writes、legacy additive compatibility 與完整 Python/Extension regression。可逆性以保留既有 evidence 欄位、只對新 high-risk G3 套用 reviewer result contract，以及透過 `revise` 回到最早受影響 phase 維持。

## Profile 補充

本 Work Item 採 feature profile。既有 G3 必要 acceptance/regression evidence 保持不變；high-risk 額外加入一個隔離 reviewer attempt 與 review result。舊 active/closed Work Item 的既有 evidence 不做 migration 或追溯 blocker。

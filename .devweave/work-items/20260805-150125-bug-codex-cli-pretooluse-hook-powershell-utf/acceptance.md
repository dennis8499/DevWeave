# 功能驗收：修正 Codex CLI PreToolUse Hook 的 PowerShell 與 UTF-8 失敗

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260805-150125-bug-codex-cli-pretooluse-hook-powershell-utf -->

## 驗證矩陣

本驗收以 Git HEAD `745e54445e6ef50a6a261e296cfe243324fcda3a`、current product
source fingerprint `947fd0a9cf0d13104c9340fd0ab10a7ed67e50e1b71e6a1d3f018478645d113f`
為準；Wiki knowledge fingerprint 為
`8d4a19e8dae60f2910b499afb1de230e9ca56a2f64530c802ebe53994ece7a75`。

| 驗收條件 | 結果 | current evidence | 說明 |
| --- | --- | --- | --- |
| AC-001 cmd.exe launcher contract | 通過 | EVID-007、EVID-016 | 真實 `cmd.exe /d /s /c` process exit 0，deny JSON 合法且保留 `PreToolUse` envelope。 |
| AC-002 PowerShell launcher contract | 通過 | EVID-007、EVID-016 | root/nested cwd 與繁中 raw UTF-8 payload 均可由 PowerShell outer runner 執行，process exit 0。 |
| AC-003 policy 與 malformed-input safety | 通過 | EVID-007、EVID-016 | unbound Write 與 malformed input fail-closed deny；read-only Bash 無輸出；正常結果 exit 0。 |
| AC-004 bootstrap/package consistency | 通過 | EVID-008、EVID-013 | package verifier 通過新 launcher semantic contract；0.2.1 VSIX 為 58 bootstrap files、118 entries，SHA-256 `a7c8f260cd958b28835c1a00528f65db6c2933a42863131cd3254fd36fd3162e`。 |
| AC-005 repository verification | 通過（含環境性 skip） | EVID-009、EVID-010、EVID-011、EVID-012、EVID-015、EVID-016、EVID-017 | Python 102 tests、Extension 73 tests、typecheck、smoke、targeted contract 與獨立 review 通過；Python suite 有一項既有 symlink privilege skip，詳見殘餘風險。 |

歷史 TDD/reproduction evidence 亦保留在追溯鏈中：EVID-001、EVID-002、EVID-003、
EVID-004 與 EVID-005 記錄修正前的 PowerShell quoting/CP950 failure；EVID-006 是
TASK-002 的 green slice，但因後續 source-derived package/文件調整而被標為 stale。
EVID-014 是第一次在受限 sandbox 執行 smoke 的 Access denied，隨後由 EVID-015 在
允許 package/smoke 執行的環境完成；EVID-007、EVID-008、EVID-009、EVID-010、
EVID-011、EVID-012、EVID-013、EVID-015、EVID-016 與 EVID-017 是修正後的 current passing
證據。這些歷史失敗不代表目前 source 的失敗，也未刪除 ledger 紀錄。

四個 Task 均已完成：TASK-001 對應 EVID-005，TASK-002 對應 EVID-006，TASK-003
對應 EVID-007/EVID-008，TASK-004 對應 EVID-009 至 EVID-017。

## Profile 證據

本 Work Item 是 `bug` profile：以 EVID-001 至 EVID-005 完成可重現的紅燈，
再以 EVID-007、EVID-008、EVID-009、EVID-010、EVID-011、EVID-012、EVID-013、
EVID-015、EVID-016 與 EVID-017 完成修正後的 process、policy、package、Extension 與
full-suite regression。`git diff --check` 無 whitespace error，僅有 Windows
既有 LF/CRLF conversion warnings。


## 基線更新

已透過 DevWeave baseline CLI 記錄「不更新」：targets 為空。原因是本次只修正
Windows process adapter 與 UTF-8 transport，不改變單一 router、hook policy、
JSON envelope、lifecycle、schema 或 verification governance truth；新增的
launcher/transport 行為已由 source-bound Wiki 保存。`.devweave/baseline/` bytes
保持不變。

## Wiki 知識提升

Knowledge Review 為 `promote`，`current=true`，health 為 `healthy`。四個 affected
content pages 已 refresh/upsert 並 seal：

- `wiki/overview.md`
- `wiki/architecture/devweave-knowledge-workflow.md`
- `wiki/modules/knowledge-engine.md`
- `wiki/modules/vscode-extension.md`

Engine coupling 同步更新並 seal `wiki/index.md` 與 `wiki/log.md`；delete 為零，
plan 內沒有未宣告頁面。`docs/使用手冊.md`、`tests/test_repository_contract.py`
與 `vscode-extension/scripts/verify-package.mjs` 已被 coverage；VSIX 是由這些
root source、esbuild 與 verifier 再生的 derived artifact，因此列為唯一
`uncovered_changed_path`，沒有獨立 durable knowledge。最後狀態為
`pending_refresh=[]`、`stale_pages=[]`、`unsealed_pages=[]`、`warnings=[]`，並
append 了一筆 work-attributed promote log。

## 獨立 Review

本 Work Item 為 high-risk。依 approved design 與 repository policy，final
artifacts 穩定後只由 DevWeave router 啟動一次 isolated、read-only Independent
Review Agent；reviewer 僅接收 approved brief/requirements/design/plan、完整 diff、
risk/scope、accepted baseline、Wiki context、current source fingerprint、Git
HEAD 與既有 evidence，不得修改 source/Wiki/ledger 或執行 gate。review result 會
由 machine-only `review record` 固定記錄；`passed` 才是正常通過，unavailable 或
advisory 只形成 warning，具名 critical finding 才需要 exact waiver。

唯一 router invocation 已完成並由 machine-only `review record` 記錄為
`EVID-017`：`result=passed`、`severity=advisory`、reviewer ID
`019fd0e5-52b2-7cf3-9531-7c47c65957b7`，report SHA-256
`6bcda073a9700576ef9504c5304242ee1a170e8c71f1d0f5830f053f143b9478`。Review
確認實作符合核准需求、設計、tasks 與 current evidence，沒有具名 critical
security、data-loss、irreversible 或 scope finding。唯一 advisory 是既有
WinError 1314 symlink privilege skip，與本次 hook change 無關；因此不需要
`review-critical` waiver。

## 殘餘風險

- `F-001`／EVID-017：Python full suite 的 `test_review_record_rejects_symlinked_final_log_directory`
  因 Windows `WinError 1314` 缺少 symlink privilege 而 skip；普通權限與一次
  escalated targeted attempt 均無法取得該 OS privilege。這是既有 review-log
  containment 的環境性限制，不是本次 hook source 的失敗；目前沒有新增 waiver。
- 使用者仍需在 Codex `/hooks` 重新信任變更並以新 session，於 repository root 與
  nested workspace 各觸發一次 read-only 與受 guard 阻擋的 write，完成 host-level
  operational acceptance。自動化 child-process contract 已覆蓋相同 launcher seam。
- 無 baseline target、schema migration、data-loss、network、dependency 或
  rollback migration；VSIX package 只接受 current 0.2.1。

## 驗收結論

目前實作已完成 approved G2 scope：Codex Windows hook 改用 shell-neutral、
non-interactive PowerShell launcher，Python guard 明確以 UTF-8 bytes 讀寫，並保留
既有 policy deny、fail-closed 與 process exit 0 semantics。root/nested cwd、
cmd.exe/PowerShell、繁中 raw UTF-8、malformed input、read-only、package、
Extension 與 Python regression 均有 current evidence。Wiki promote/seal 與
baseline no-update record 也已完成。

本文件可供 G3 審閱；在唯一 Independent Review report 完成且使用者明確核准
G3 前，Work Item 不視為已驗收或可 close。

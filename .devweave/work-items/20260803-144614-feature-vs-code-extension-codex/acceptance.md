# 功能驗收：收斂 VS Code Extension 至初始化與公開 Codex 命令

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260803-144614-feature-vs-code-extension-codex -->

## 驗證矩陣

本次驗收使用的 EVID-006～EVID-011 均綁定 current source fingerprint `91f861505813558138b270f9cd36ea43f82fa6e7022904bddd012df70a935ca5`；EVID-001～EVID-005 是 final source 變更前的歷史 evidence，保留為 stale audit record，不作為本次 AC 的唯一證據。

| AC | 結果 | Evidence | Tasks |
| --- | --- | --- | --- |
| AC-001 八個公開命令表單 | 通過 | EVID-006、EVID-011 | TASK-001、TASK-003、TASK-004 |
| AC-002 work selection 與 optional work | 通過 | EVID-006、EVID-011 | TASK-003、TASK-004 |
| AC-003 公開 prompt preview/copy | 通過 | EVID-006、EVID-007、EVID-011 | TASK-001、TASK-002、TASK-003、TASK-004 |
| AC-004 bootstrap regression | 通過 | EVID-008、EVID-009、EVID-010 | TASK-002、TASK-004、TASK-005 |
| AC-005 唯讀 Dashboard 與入口收斂 | 通過 | EVID-006、EVID-007、EVID-008、EVID-009、EVID-011 | TASK-002、TASK-003、TASK-004、TASK-005 |
| AC-006 parser 拒絕 machine intents | 通過 | EVID-006、EVID-007、EVID-011 | TASK-001、TASK-003、TASK-004 |
| AC-007 README 與流程一致 | 通過 | EVID-008、EVID-011 | TASK-005 |
| AC-008 安全回歸 | 通過 | EVID-006、EVID-007、EVID-010 | TASK-001、TASK-004 |
| AC-009 完整驗證 | 通過 | EVID-006、EVID-007、EVID-008、EVID-009、EVID-010 | TASK-004、TASK-005 |

所有 configured command 均以 exit code 0 完成：Extension tests 13/13、root unit tests 62/62；typecheck、package 與 VS Code Extension Host smoke 亦通過。`git diff --check` 通過。

## Profile 證據

本 work 為 feature，已具備 feature profile 所需的 acceptance 與 regression：

- EVID-011（acceptance）：完成 Webview/host source review，確認八個公開命令欄位、work selection、optional work、required work、preview/copy 邊界、唯讀 projection 與 README/command metadata。
- EVID-006（regression）：公開命令 prompt/parser/security tests，13/13 通過。
- EVID-010（regression）：root repository unit tests，62/62 通過。
- EVID-007、EVID-008、EVID-009：typecheck、production package 與 VS Code Extension Host smoke 通過。

## 基線更新

本次只收斂 `vscode-extension` 的 page-facing command seam、Webview 操作表單與文件；既有 bootstrap boundary、preview/copy boundary、readonly Dashboard boundary 與 public verb contract 均仍適用，沒有需要更新的 accepted living baseline。未修改 `.devweave/baseline/`，因此沒有 baseline target 需要宣告。

## Wiki 知識提升

無變更。verification 時 `knowledge status` 顯示 `affected_pages=[]`、`pending_refresh=[]`、`stale_pages=[]`，本 work 沒有 Wiki diff，因此未建立空的 knowledge plan，也沒有更新或 seal page。`wiki/overview.md` 的既有 placeholder warning 保留為 unrelated residual warning，未被本次 source diff 影響。

## 殘餘風險

- 無 waiver、無 critical diagnostic；current AC 證據沒有 stale，僅保留 EVID-001～EVID-005 的歷史 stale audit record。
- `wiki/overview.md` 仍是既有 placeholder；它不屬於本 work 的 affected page，後續 Wiki work 再處理。
- 本次不新增資料夾手動選取；依 approved scope 維持既有 workspace root resolution。
- Extension 仍不直接執行 Codex；使用者必須自行審閱並在 Codex Chat 送出複製的公開命令。

## 驗收結論

實作已完成並通過目前 source fingerprint 下的完整驗證。Dashboard 現在只提供初始化與八個公開 `$devweave` 對話命令的 preview/copy 表單；既有 work、gate、task、evidence、artifact、Wiki、audit、Refresh、work selection 與檔案開啟維持唯讀或展示用途。可提交 G3 acceptance，待使用者核准後立即 close work item。

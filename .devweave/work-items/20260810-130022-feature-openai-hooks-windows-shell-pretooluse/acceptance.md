# 功能驗收：依 OpenAI Hooks 最佳實踐強化 Windows 跨 Shell PreToolUse 相容性

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260810-130022-feature-openai-hooks-windows-shell-pretooluse -->

## 驗證矩陣

現行 product source fingerprint：`4235d5e3138a8bec86f73b7a8174b2472276d4ec0236441bfefb3f79386dc7e4`。

| Acceptance | TASK | current 證據與結果 |
| --- | --- | --- |
| AC-001 exact PreToolUse matcher、timeout、status 與 dual command contract | TASK-001、TASK-006 | EVID-014、EVID-015、EVID-018 passed；repository contract、hook schema、VS Code terminal matrix 與 package source-derived contract 均通過。 |
| AC-002 CMD/root+nested/UTF-8 deny matrix | TASK-001、TASK-003、TASK-006 | EVID-014、EVID-015 passed；實際 VS Code CMD terminal 與完整 Python suite 均驗證 root/nested cwd、繁中 deny JSON。 |
| AC-003 PowerShell 5.1、PowerShell 7/root+nested/malformed/read-only matrix | TASK-001、TASK-003、TASK-006 | EVID-014、EVID-015 passed；兩個實際 VS Code PowerShell terminals 與 repository contract 驗證 launcher、malformed input deny、read-only Bash silence。 |
| AC-004 唯讀 doctor diagnostics 與 bounded launcher probe | TASK-002、TASK-006 | EVID-014、EVID-015 passed；六個 VS Code root/nested doctor outputs 均為 13/13 checks、`launcher-probe=true`，並由完整 suite 覆蓋 fixture/CLI contract。 |
| AC-005 Extension 0.2.3、source-derived hook、package 與 smoke | TASK-004、TASK-006 | EVID-014、EVID-016、EVID-017、EVID-018、EVID-019、EVID-021 passed；typecheck、77 unit tests、0.2.3 package（58 bootstrap files/119 VSIX entries/root-embedded equality）與 VS Code smoke 均通過，0.2.2/0.2.1 artifacts 保留。 |
| AC-006 文件與 operator recovery boundary | TASK-005、TASK-006 | EVID-014、EVID-015、EVID-017、EVID-019 passed；README、繁中手冊、AGENTS、Extension README/help、repository contract 與 smoke projection 均同步。 |
| AC-007 整合品質、current evidence 與 scope | TASK-001–TASK-006 | EVID-014、EVID-015、EVID-016、EVID-017、EVID-018、EVID-019、EVID-020、EVID-021、EVID-022 passed；`git diff --check` 通過，所有現行 required high-risk command profiles 有 current passing evidence。 |

所有列出的 current 證據均綁定同一 source fingerprint。EVID-001–EVID-012 是較早的同類或環境性證據，已由 engine 標記 stale；EVID-010 是 sandbox 無法讀取 parent/bootstrap path 的環境性 package 嘗試，未被採為通過證據。EVID-013 是 final source stabilization 前的第一次 high-risk review，已因 source fingerprint 改變 stale；其 F-001「缺少 VS Code integrated-terminal walkthrough」由 EVID-014 補齊，EVID-020 是同一 reviewer identity 對 current artifacts 的 passed re-review，僅保留 F-002 advisory。

## Profile 證據

本 work item 是 `feature`。current CLI evidence 同時包含 manual walkthrough（EVID-014）、root acceptance（EVID-015）、Extension typecheck/tests（EVID-016、EVID-017、EVID-021）、elevated package/smoke（EVID-018、EVID-019）與 final isolated review（EVID-022）；root Python suite 為 101 tests、1 symlink-privilege skip，Extension suite 為 77 tests。Package 與 smoke 在需要存取 VS Code/esbuild 外部執行環境時以核准的 elevated verification 執行；產品結果仍由 package verifier、smoke exit code 與固定 review envelope 判定。

## 基線更新

已透過 DevWeave baseline CLI 宣告並更新三份 accepted baseline：

- `.devweave/baseline/architecture.md`：記錄 exact matcher、POSIX/Windows dual launcher、.NET UTF-8 console normalization、Git-root resolution、doctor bounded probe、launcher/policy boundary，以及 0.2.3 source-derived package contract。
- `.devweave/baseline/quality.md`：記錄 101/1-skip Python suite、77 Extension tests、0.2.3 package（58/119）、explicit console encoding quality attribute、Windows launcher quality attribute 與 current high-risk command profiles。
- `.devweave/baseline/product.md`：記錄 CMD、PowerShell 5.1、PowerShell 7、VS Code terminal 的 one-line doctor/operator capability、handler UTF-8 initialization、0.2.3 current VSIX 與 retained 0.2.2/0.2.1 boundary。

三個 target 均有實際內容變更，無未宣告 baseline path。

## Wiki 知識提升

Knowledge Review 已由 CLI 記錄 `promote`，理由是 dual-path hook、Windows doctor launcher matrix、source-derived Extension package、explicit console encoding 與 operator recovery boundary 具跨 work item 重用價值。Knowledge plan 宣告並完成四個 content upsert：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`；同步更新 coupled `wiki/index.md` 與 append-only `wiki/log.md`，每頁均以 CLI seal。最後 `knowledge status` 為 `healthy`，`pending_refresh`、`stale_pages`、`uncovered_changed_paths`、`unsealed_pages` 與 warnings 均為空；log 保留一筆初始 promote 與一筆 final source-refresh note，均 attributed to this work item。

## 殘餘風險

- 一項 symlink containment 測試因目前 Windows token 沒有 symlink privilege 而 skipped；其餘 101 tests 通過。這是驗證環境限制，不是以 waiver 宣稱該案例通過。
- Extension package/smoke 的 sandbox 嘗試受到 esbuild/VS Code 外部 process path 權限限制；失敗的 EVID-010 已被同一 profile 的 elevated current passing EVID-018 取代，未把環境失敗當成產品成功。
- `py -3`、Git、repository trust 與 UTF-8 是 Windows operator prerequisite；doctor 會以明確欄位回報缺少 launcher、shell 或 trust。PreToolUse 是 Codex guardrail，不是 OS sandbox，hosted/global/plugin tools 與 hook 停用後的外部編輯不在本 change 的保證範圍。
- EVID-014 的 walkthrough 使用暫存 extension 產生真實 VS Code terminals，並保留 root/nested JSON、process exit markers 與三個 `OK` logs；這證明 repository-controlled hook/doctor seam，不把 Codex host trust 或第三方 hosted/global/plugin tool coverage 擴張成產品保證。
- EVID-022 final current high-risk review 為 `passed`，無 critical finding；F-002 是非 Windows doctor skipped-check 語義的 advisory，明確不擴大本次 Windows release scope。仍待 human G3 approval；在此之前驗收結論不宣稱已關閉。

目前沒有 review-critical、out-of-scope 或 missing-command waiver；第一次 review 的 stale critical result 不以 waiver 取代，已由 EVID-014 與 EVID-022 final current re-review 處理。

## 獨立 Review

唯一 DevWeave router 已啟動 exactly one isolated、read-only reviewer；EVID-013 的第一次 report 在 source stabilization 後 stale，之後以相同 reviewer identity resume，並由 EVID-022 記錄 final current `passed` 結果（EVID-020 為中間 current re-check）。Reviewer 僅接收 current product/Wiki/baseline/diff/scope/evidence、核准 artifacts、risk/scope、accepted baseline、Wiki context、source fingerprint 與 Git HEAD；結果透過 machine-only `review record` 寫入，Extension 不啟動 reviewer，也沒有建立第二個 reviewer。

## 驗收結論

目前 implementation、Wiki promotion、baseline 更新、EVID-014～EVID-022 current verification 已完成；Windows CMD、PowerShell 5.1、PowerShell 7 及 VS Code terminal 的 launcher contract、doctor guidance、0.2.3 Extension package 與測試結果均符合已核准 AC。EVID-022 的 advisory F-002 已保留在驗收風險中；請由使用者核准 G3，G3 核准前不 close work item、不宣稱正式完成。

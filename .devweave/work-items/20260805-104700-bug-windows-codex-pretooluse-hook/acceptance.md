# 功能驗收：修正 Windows Codex PreToolUse Hook 失敗

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260805-104700-bug-windows-codex-pretooluse-hook -->

## 驗證矩陣

| Acceptance | 結果 | Tasks | Current evidence | 說明 |
| --- | --- | --- | --- | --- |
| AC-001 | 通過 | TASK-001、TASK-004 | EVID-007 | `cmd.exe /d /s /c` 實際啟動標準 PowerShell launcher；process exit code 為 0，`commandWindows` 已移除。 |
| AC-002 | 通過 | TASK-002、TASK-004 | EVID-007 | 未綁定 Write payload 返回合法 `hookSpecificOutput.permissionDecision: deny` JSON，process exit code 仍為 0；`guard.py` 未修改。 |
| AC-003 | 通過 | TASK-003 | EVID-005 | 0.2.1 package verifier 通過，embedded hook 使用 canonical Windows command；0.1.0／0.2.0 legacy artifact 的固定 hash 通過。 |
| AC-004 | 通過 | TASK-002、TASK-004 | EVID-006 | root Python 98 tests（既有 symlink privilege skip 1）、Extension 73/73、typecheck、package、Windows smoke 與 `git diff --check` 通過。 |
| AC-005 | 通過 | TASK-003 | EVID-005 | 使用手冊區分 process failure 與 DevWeave policy deny，並說明 exact bootstrap 不會被 Extension 靜默覆寫。 |

Current product source fingerprint：`d1580353e72e0905924535ed47ebea83c4ad6bbb89c80f37396632c159381c77`；Git HEAD：`8300fac45be9573ee265665ec6557e130391de3b`。

## Profile 證據

本 Work Item 是 bug profile。修正前的 Unix command 在 Windows `cmd.exe` 下失敗，保留於 EVID-001／EVID-002 作為 reproduction history；修正後以 EVID-003／EVID-004 完成 targeted launcher/regression，並以 current source-bound EVID-007 重新覆蓋 AC-001／AC-002。EVID-003／EVID-004 的早期 fingerprint 已由 EVID-007 取代，不把 stale evidence 當成 current acceptance。

完整驗證命令與結果：

- `python -B -m unittest discover -s tests -v`：98 tests，1 項既有 symlink privilege skip，通過。
- `npm.cmd run test`：73 pass、0 fail、0 skipped/todo。
- `npm.cmd run typecheck`：通過。
- `npm.cmd run package` 與 package verifier：0.2.1 產生 58 bootstrap files、118 VSIX entries，通過 embedded hook semantic checks。
- `npm.cmd run test:smoke`：Windows Extension Host smoke 通過；sandbox 初次阻擋 esbuild parent read，升權後同一命令成功，非產品失敗。
- `git diff --check`：通過，沒有 whitespace error。
- DevWeave command-bound current evidence：EVID-009（`unit-tests` regression）、EVID-011（`extension-tests`）、EVID-012（`extension-typecheck`）、EVID-014（`extension-package`）與 EVID-015（`extension-smoke`）均為 zero-exit passed；EVID-010 是 cp950 stdout encoding failure，EVID-013 是 sandbox 環境失敗，兩者都不是產品失敗，並已由後續 current pass 取代。

## 基線更新

不更新 `.devweave/baseline/product.md`、`.devweave/baseline/architecture.md` 或 `.devweave/baseline/quality.md`。本次只修正 Windows launcher 啟動 adapter、測試、文件與 source-derived package；不改變 guard decision schema、CLI、engine lifecycle、accepted system boundary 或 verification profile。

## Wiki 知識提升

Knowledge Review 為 `promote`。Rationale：Windows Codex hook launcher、0.2.1 bootstrap 行為，以及 process failure 與 policy deny 的分層是可重用的 Extension integration knowledge。

- Affected pages：`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`、`wiki/overview.md`。
- Upserts：上述四個既有 content pages；沒有 delete、沒有新增 placeholder。
- Coupled：`wiki/index.md`、`wiki/log.md`，並追加一筆 work-attributed `promote` log。
- Seal：四個 content pages 加 index/log 共六頁，皆由本 work item 以 2026-08-05、current source fingerprint seal；`knowledge status` 回報 healthy、無 stale/unsealed/critical lint warning。
- Uncovered artifact：0.2.1 VSIX 是 release binary，已由 EVID-005 的 package verifier 覆蓋，不新增專用 Wiki page。`.codex/hooks.json` 是 framework path，product coverage snapshot 不列入 changed product paths；其行為由根 hook、sealed `vscode-extension` page、repository regression 與 package evidence 直接覆蓋。

## 獨立 Review

- High-risk router exactly started one isolated read-only reviewer，reviewer ID 為 `019fcfea-0aec-77b1-a06b-3dbe688712e8`，machine-only record 為 EVID-008。
- Reviewer 回傳 malformed `unavailable` payload；engine 拒絕將 `result=unavailable` 與 advisory findings 視為有效，依 contract 轉為 `unavailable`／`severity=none`／無 findings 的安全 fallback。結果是 warning，不是 passed；沒有 critical finding，也沒有 `review-critical` waiver。
- Review source fingerprint 與 current evidence 同為 `d1580353e72e0905924535ed47ebea83c4ad6bbb89c80f37396632c159381c77`，context mode 為 `isolated_read_only`，涵蓋 AC-001～AC-005 與 TASK-001～TASK-004。

## 殘餘風險

- High-risk Independent Review 已依 router 啟動 exactly one isolated read-only reviewer。原始回傳為 malformed `unavailable` advisory payload，`review record` 依契約安全降級為 `unavailable`／neutral、無 findings，形成 EVID-008 warning；沒有 critical finding，也沒有 `review-critical` waiver。這不構成 passed，需保留為 G3 warning。
- 本次 process-level verification 已證明 Windows `cmd.exe` 啟動鏈與 guard JSON/exit contract；若既有 workspace 的 `.codex/hooks.json` 仍是舊內容，Extension 不會靜默覆寫，使用者仍須確認內容、重新套用 bootstrap 並重啟／信任 repository hook。
- 未宣稱 WSL、macOS 或 Linux 支援；正式範圍只涵蓋原生 Windows。

## 驗收結論

修正後的標準 hook 已由 Windows `cmd.exe` 可啟動的 PowerShell command 取代 Unix-only launcher，`commandWindows` 已移除，`guard.py` 與既有 allow/deny JSON contract 未改變。Current evidence 已覆蓋 AC-001 至 AC-005；0.2.1 VSIX、bootstrap、legacy artifacts、文件、Wiki promote/seal 與完整高風險驗證均已完成。唯一 high-risk reviewer 結果是 unavailable warning，無 critical finding；請由人員進行 G3 最終核准後 close work item。

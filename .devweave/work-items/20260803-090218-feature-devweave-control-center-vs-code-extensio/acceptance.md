# 功能驗收：建立 DevWeave Control Center VS Code Extension

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260803-090218-feature-devweave-control-center-vs-code-extensio -->

## 驗證矩陣

目前 source-bound passing evidence 的 fingerprint：
`77dc8e7b6563f73a4b37b47b3b6397357e67851a8323e4e8350a9dc6596dfa8b`

| Acceptance | 對應 evidence | 結果 |
| --- | --- | --- |
| AC-001 | EVID-008, EVID-012, EVID-013, EVID-015, EVID-016 | 通過：狀態分類、production bundle、activation 與 fail-closed projection 已驗證 |
| AC-002 | EVID-009, EVID-010, EVID-013, EVID-015, EVID-016 | 通過：zero/one/multiple/closed work 與明確 selection projection 已測試 |
| AC-003 | EVID-015 | 通過：phase、G1/G2/G3、next action 與 approval warning 完成 code review |
| AC-004 | EVID-010, EVID-015 | 通過：所有 ActionIntent 產生 deterministic preview |
| AC-005 | EVID-010, EVID-015 | 通過：preview → confirm → clipboard copy，無 execute/write path |
| AC-006 | EVID-010, EVID-014, EVID-015 | 通過：malformed/unsupported source、無 process/shell/write/network 邊界 |
| AC-007 | EVID-010, EVID-015 | 通過：artifact、trace、task dependency、evidence 與 open-file projection |
| AC-008 | EVID-010, EVID-015 | 通過：Wiki-first、health、G3 knowledge 與 prompt-only actions |
| AC-009 | EVID-010, EVID-015 | 通過：verification/acceptance matrix、baseline、waiver 與 governance preview |
| AC-010 | EVID-010, EVID-015 | 通過：filesystem snapshot、engine-observed freshness 與 refresh warning |
| AC-011 | EVID-014, EVID-015 | 通過：既有 Python suite 62 tests 全部 OK |
| AC-012 | EVID-010, EVID-013, EVID-015 | 通過：theme tokens、CSP、focus/ARIA、high-contrast/reduced-motion code review 與 host smoke |
| AC-013 | EVID-010, EVID-014, EVID-015 | 通過：deterministic repo-relative prompt、secret/raw-log/absolute-path sanitization |
| AC-014 | EVID-008, EVID-010, EVID-012, EVID-013, EVID-014, EVID-015 | 通過：TypeScript、vanilla Webview、seams、unit、package、smoke 與 regression checks |

TASK-001 至 TASK-006 的早期 EVID-001 至 EVID-006 因最後 source revisions 被 engine 正確標記 stale；TASK-007 至 TASK-009 以 EVID-008、EVID-010、EVID-012、EVID-013、EVID-014、EVID-015 重新覆蓋目前 source。EVID-007 與 EVID-011 是修正前的失敗紀錄，分別反映 Windows `npm` 入口與 sandbox esbuild 限制，後續以 `npm.cmd`、TAP runner 與 elevated package/smoke verify 取代。

## Profile 證據

本 work item 為 high-risk feature，required profile 已由 DevWeave `command set` 設定：

- `extension-typecheck`：`vscode-extension` / `npm.cmd run typecheck`，EVID-008，passed。
- `extension-tests`：`vscode-extension` / `node.exe --import tsx --test --test-reporter=tap test/unit/core.test.ts test/unit/security.test.ts`，EVID-010，13 tests passed；修正前 `npm.cmd test` 的 EVID-009 亦為 current/pass，僅因 cp950 capture 改用 TAP runner 作為正式 profile。
- `extension-package`：`vscode-extension` / `npm.cmd run package`，EVID-012，production host/Webview bundle passed。
- `extension-smoke`：`vscode-extension` / `npm.cmd run test:smoke`，EVID-013，VS Code 1.131.0 Extension Host activation passed。
- `unit-tests`：repository root / `python -B -m unittest discover -s tests -v`，EVID-014，62 tests passed。
- High-risk independent review：EVID-015，passed，涵蓋安全、相容性、rollback、scope、CSP、accessibility 與 no-side-effect boundary。
- Acceptance preparation cross-check：EVID-016，passed；G3 仍等待明確 human approval。

## 基線更新

已透過 DevWeave CLI 宣告 target `.devweave/baseline/architecture.md`，並在 verification 更新 accepted architecture boundary：

- Extension 位於 `vscode-extension/`，只讀取 filesystem snapshot、呈現 TreeView/Webview，並透過 `PromptComposer` 產生 Codex Chat prompt。
- Python DevWeave engine、JSON/JSONL ledgers、hook、Wiki、baseline 與人工 gates 保持 authoritative。
- Extension 不啟動 Python/shell/Git、不寫入 repository、不管理 branch/commit/push/PR/release/version compare；唯一 side effect 是使用者確認後寫入 VS Code clipboard。
- 更新 provenance：`20260803-090218-feature-devweave-control-center-vs-code-extensio`，待 G3 核准。

## Wiki 知識提升

無變更。`knowledge status` 顯示本 work item `affected_pages: []`、`pending_refresh: []`、無 planned upsert/delete/coupled index/log；既有 `wiki/overview.md` placeholder warning 保留，因本 work item 沒有 source-bound Wiki page 影響，不建立空的 knowledge plan，也不修改 Wiki。

## 殘餘風險

- Accessibility 的完整 light/dark/high-contrast、字體放大、keyboard-only 與 reduced-motion 矩陣仍需在實際使用者工作站做人工視覺確認；本次已完成 theme/CSP/focus/ARIA/reduced-motion code review 與 activation smoke，未新增 waiver。
- Production esbuild package 在本受限 agent sandbox 需 elevated execution；EVID-012 已以同一 command profile 完成 passed verification，這不改變 Extension runtime 的 read-only boundary。
- Repository 現有 `wiki/overview.md` placeholder 是既有 knowledge warning，未被本 work item 影響；後續由獨立 Wiki work item 處理。
- 無 migration、database、remote coordination 或 rollback data risk；停用/移除 Extension 即可回復，不改變既有 Python engine/state/Wiki。

## 驗收結論

DevWeave Control Center 已完成 approved scope：VS Code Activity Bar/TreeView、Dashboard、Work Item detail、Wiki-first、verification/acceptance projection、全 ActionIntent prompt entry、Action Preview/copy-only flow、snapshot freshness、CSP/accessibility 與完整 test/package/smoke seams 均已落地。所有 mutation 仍由使用者在 Codex Chat 送出，Extension 不直接執行或修改 repository。

目前 G1 Scope 與 G2 Build 已核准，所有 9 個 tasks completed，current passing evidence、feature regression、high-risk review 與 declared baseline update 已具備；G3 Acceptance 尚未核准。請使用者檢閱上述 residual risks 與 verification matrix 後，以 `$devweave approve 20260803-090218-feature-devweave-control-center-vs-code-extensio` 明確核准 G3，或提出 revise。

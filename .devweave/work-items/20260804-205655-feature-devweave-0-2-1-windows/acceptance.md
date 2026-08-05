# 功能驗收：DevWeave 0.2.1 Windows 公開版發布強化

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260804-205655-feature-devweave-0-2-1-windows -->

## 驗證矩陣

目前 product source fingerprint：`ffd341e10a596ee21933e6209f19905ae3f1e8c53be59b201177710d0f486526`；Git HEAD：`868be0912a5b4a218d27bed01b4162e2f344a0dd`。

| AC | 結果 | Current evidence | 對應 task |
| --- | --- | --- | --- |
| AC-001 | passed | EVID-046（PreviewGate matching ticket 與未 preview 不得 copy） | TASK-001、TASK-004、TASK-007 |
| AC-002 | passed | EVID-046（one-shot consume、panel/intent/revision mismatch reject，含 delimiter collision regression） | TASK-001、TASK-004、TASK-007 |
| AC-003 | passed | EVID-046（refresh/selection/bootstrap/snapshot stale invalidation） | TASK-001、TASK-003、TASK-004、TASK-007 |
| AC-004 | passed | EVID-046（clipboard failure safe retry contract） | TASK-001、TASK-004、TASK-007 |
| AC-005 | passed | EVID-045、EVID-046（actionPreview intent parity、protocol、trusted smoke） | TASK-001、TASK-002、TASK-004、TASK-007 |
| AC-006 | passed | EVID-045、EVID-046、EVID-048（legacy command、single/multi/zero work） | TASK-002、TASK-004、TASK-007 |
| AC-007 | passed | EVID-046（Wiki `#wiki-results` DOM mount、Enter/filter/show-all contract） | TASK-003、TASK-004、TASK-007 |
| AC-008 | passed | EVID-046、EVID-048（multi-work next explicit selection 與 status `--all`） | TASK-002、TASK-003、TASK-004、TASK-007 |
| AC-009 | passed | EVID-046、EVID-047（tabpanel ARIA、方向鍵/Home/End、focus/forced-colors） | TASK-003、TASK-004、TASK-007 |
| AC-010 | passed | EVID-046、EVID-047、EVID-050（繁中 CTA/modal/error/readiness 與文件 contract） | TASK-003、TASK-006、TASK-007 |
| AC-011 | passed | EVID-044（0.2.1 package/version provenance、57 bootstrap files、117 VSIX entries） | TASK-005、TASK-007 |
| AC-012 | passed | EVID-044（0.2.0/0.1.0 regular-file、size、fixed SHA-256 retention） | TASK-005、TASK-007 |
| AC-013 | passed | EVID-050、EVID-054（documentation、VSIX install/handoff/Refresh/legacy 與 final diff check） | TASK-006、TASK-007 |
| AC-014 | passed | EVID-046、EVID-047、EVID-048（Extension/Python public contract regression） | TASK-004、TASK-007 |
| AC-015 | passed | EVID-044、EVID-045、EVID-046、EVID-047、EVID-048、EVID-049、EVID-050、EVID-051、EVID-052、EVID-053、EVID-054（high profile、doctor、四條 walkthrough、acceptance/regression matrix 與 final diff check） | TASK-007 |
| AC-016 | passed | EVID-055（唯一 router 啟動的 isolated read-only Independent Review；result=passed、severity=none、findings=[]） | TASK-007 |

Current source-bound passing evidence 為 EVID-044～EVID-055；EVID-001～EVID-043 是 source stabilization 或歷次 high-risk review 前的 historical/stale evidence，不作為 G3 current coverage。EVID-018、EVID-033 與 EVID-043 的 critical/advisory findings 均已因 revision stale；EVID-043 所列 status-all、PreviewGate delimiter collision 與 error-display issues 已在同一批准 scope 內修正並由 current tests/package/evidence 覆蓋。

## Profile 證據

本 work 是 `feature` high-risk，已完成 required `acceptance` 與 `regression` evidence。DevWeave high profile 五項 current command 均 passed：`extension-package`、`extension-smoke`、`extension-tests`、`extension-typecheck`、`unit-tests`。`doctor`、documentation、Extension bounded walkthrough、Python targeted walkthrough、current acceptance matrix、regression summary、final diff check 與 Independent Review 另有 EVID-046、EVID-048～EVID-055。

Python full suite：`Ran 94 tests in 215.890s`、`OK (skipped=1)`；該 skipped 是既有 Windows symlink privilege case。Extension suite：`73/73` passed。

版本與 artifact：`vscode-extension/devweave-control-center-0.2.1.vsix` 已由 trusted Windows package verifier 驗證；最終檔案為 `270480` bytes、`117` VSIX entries、`57` bootstrap files，SHA-256 `A6DF4F520E97A555AA548F94B0AD342035ADF711D639E8C099E2EBBACC22F0EE`。`devweave-control-center-0.2.0.vsix` 保留 `255162` bytes / `3E3610D3FCC888DD5B1F94F73360C3023BA51336018E14DBC67C2E664C218917`；`devweave-control-center-0.1.0.vsix` 保留 `258106` bytes / `75FBAD761C6A8C6DB1997F5A6ED56DEE2FF5A9D95A17F9329E5B6A8BFA2FB357`。

## 基線更新

已透過 baseline CLI 宣告並更新：

- `.devweave/baseline/product.md`：Windows 0.2.1 支援與 artifact boundary、preview-first handoff、legacy `copyNextAction`/multi-work、初始化 semantic adoption/fail-closed 與繁中 Control Center 能力。
- `.devweave/baseline/architecture.md`：PreviewGate host enforcement、actionPreview intent/revision、Wiki result mount、ARIA/keyboard seam、package version provenance 與 no Marketplace release boundary。
- `.devweave/baseline/quality.md`：Preview/copy fail-closed、Windows release support、73/94 test counts、57/117 package verification、四條 walkthrough bar 與 high-risk review bar。

所有 baseline changed paths 都已由本 work 的 target 宣告涵蓋，沒有 undeclared baseline change。

## Wiki 知識提升

Knowledge Review disposition 為 `promote`，rationale 是本次形成可跨工作重用的 PreviewGate/host copy safety、`status --all` multi-work handoff、`wikiBootstrap` preview routing、穩定五區 tabpanel accessibility、Wiki DOM mount、繁中 error/detail boundary、multi-work 與 Windows VSIX release boundary。

- Affected pages：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`。
- Upsert：上述四頁；delete：無。
- Coupled：`wiki/index.md`、`wiki/log.md`；既有本 work `promote` heading 追加 critical-review-hardening bullet，保持 append-only。
- `knowledge seal` 已封存六個頁面；Knowledge health `healthy`、bootstrap `complete`、critical/uncovered/stale/unsealed warnings 均為空。
- Knowledge fingerprint：`0fcb3977a4c6e75c21c6afe0d60e8301ec97ca228141b6d53e0c18f76c7372e7`。

## 獨立 Review

本 work 為 high-risk。產品 source、Wiki、baseline、scope、diff 與 current evidence 已穩定；必須由唯一 DevWeave router 啟動 exactly one isolated、read-only Independent Review Agent，且只以 machine-only `review record` 寫入結果。G3 需要 current `passed` 且沒有 unresolved advisory；`unavailable`、timeout、critical 或 scope finding 不得直接放行。

EVID-018 是第一次 review 的 historical critical result，EVID-033 是第二次 review 的 historical advisory result，EVID-043 是第三次 review 的 historical critical result；三者均已因 revision stale。Current review 為 EVID-055：reviewer `019fcd81-ca2a-7171-9051-a8b3e092927a`、context `isolated_read_only`、result `passed`、severity `none`、source fingerprint `ffd341e10a596ee21933e6209f19905ae3f1e8c53be59b201177710d0f486526`、report SHA-256 `859cc7ee357d3727fe42b2bcef3f9870fb24174fd40f956e67d83a67620bc0b1`、covers AC-001～AC-016、findings `[]`、waivers 無；因此沒有 unresolved advisory。

## 殘餘風險

- 正式支援限 Windows、VS Code 1.90+、Python 3.11+、Git 與 Codex；不包含 Marketplace、macOS/Linux 或外部部署承諾。
- Python full suite 的一項既有 Windows symlink privilege case 仍 skipped；其餘 94 tests passed，未以寬泛 waiver 取代。
- VS Code smoke log 含 VS Code/Node 的環境 deprecation 與 mermaid extension API proposal warning；smoke exit code 0，未觀察到 DevWeave failure。
- Independent Review 已 current passed 且沒有 unresolved advisory；仍尚未取得 G3 human approval，在產品負責人明確核准前不得 close 或對外宣稱完成。
- Waivers：無。

## 驗收結論

目前實作、文件、baseline、Wiki promote/seal、high profile verification、Windows walkthrough 與唯一 Independent Review 已完成，AC-001～AC-016 均有 current passing evidence，且 review 無 unresolved advisory。此 acceptance artifact 只呈現核准範圍的 conformance，不取代產品負責人的 G3 approval；請由產品負責人明確核准 G3，再執行 `close`。

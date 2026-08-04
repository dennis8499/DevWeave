# 功能驗收：修正 VS Code Extension 效能、Wiki 搜尋與完整初始化

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260804-102428-feature-vs-code-extension-wiki -->

## 驗證矩陣

本次 current source fingerprint 為 `4458c47b88ab4c648bec8728c21cbe4ca7dfb77c6ec573b621144b813c07a400`。下表只以 current/passed evidence 作為 G3 判定依據；較早的 stale 或 sandbox 診斷 evidence 保留於 ledger，不作為唯一證據。

| 驗收條件 | 結果與證據 | 任務 |
| --- | --- | --- |
| AC-001 Wiki 輸入不倒序 | 通過；`WikiSearchModel` 將 draft 與 applied query 分離，輸入期間不重建 input，50 個 Extension tests 與 acceptance review 通過。EVID-010、EVID-011 | TASK-001、TASK-005 |
| AC-002 Wiki 包含式查詢 | 通過；Enter 才套用大小寫不敏感的 title/path/body preview `includes` 查詢，type 仍精確篩選。EVID-010、EVID-011 | TASK-001、TASK-005 |
| AC-003 Webview 局部 render | 通過；結果與 metrics 使用 stable DOM seam，render scheduler 合併 local render，不重建 Knowledge section。EVID-010、EVID-011、EVID-012 | TASK-001、TASK-005 |
| AC-004 Refresh burst 合併 | 通過；watcher/manual refresh 共用 single-flight coordinator，burst 只保留最新 pending read。EVID-010、EVID-011、EVID-012 | TASK-002、TASK-005 |
| AC-005 最新 snapshot 優先 | 通過；coordinator 不允許重疊 read，latest publish 不被舊結果回退。EVID-010、EVID-011、EVID-012 | TASK-002、TASK-005 |
| AC-006 平行讀取保持 projection contract | 通過；instrumented snapshot test 驗證獨立 reads 平行化、固定排序與診斷順序；Repository regression 亦通過。EVID-010、EVID-008、EVID-011 | TASK-002、TASK-005 |
| AC-007 空 workspace 完整 bootstrap | 通過；bundle manifest/installer 覆蓋六組 skills、AGENTS、lock、hook、project、baseline 與 Wiki starter，排除非控制內容。EVID-005、EVID-010、EVID-011 | TASK-003、TASK-004、TASK-005 |
| AC-008 Manifest allowlist 完整 | 通過；0.2.0 package verifier 檢查每個 entry 的 destination、byte length、SHA-256 與六組 skills。EVID-005、EVID-011、EVID-012 | TASK-003、TASK-005 |
| AC-009 Partial bootstrap repair | 通過；inspection 與 installer 只建立缺少且無 conflict 的檔案，Dashboard projection 顯示 missing/partial。EVID-010、EVID-011 | TASK-004、TASK-005 |
| AC-010 Conflict 不覆寫 | 通過；不同 bytes 保留原檔並列 conflict，其他獨立缺檔仍可建立，root contract test 通過。EVID-010、EVID-008、EVID-011、EVID-012 | TASK-004、TASK-005 |
| AC-011 Bootstrap rollback | 通過；write failure 會 rollback 本輪新增 files/directories，既有內容不變。EVID-010、EVID-008、EVID-011、EVID-012 | TASK-004、TASK-005 |
| AC-012 Bootstrap completeness UI | 通過；`WorkspaceSnapshot.bootstrap` 投影 expected/missing/conflicts/complete，Dashboard 不再只看 project 存在。EVID-010、EVID-011 | TASK-004、TASK-005 |
| AC-013 Embedded help | 通過；help content 只在 Extension bundle 內 lazy render，包含初始化、workflow/Gate、Wiki、companions 與安全邊界，無 workspace write/network seam。EVID-010、EVID-007、EVID-011、EVID-012 | TASK-001、TASK-005 |
| AC-014 Versioned package verification | 通過；產出 `devweave-control-center-0.2.0.vsix`，manifest/VSIX inspection 通過，既有 dirty `0.1.0.vsix` 保留。EVID-005、EVID-007、EVID-011、EVID-012 | TASK-003、TASK-005 |
| AC-015 Regression baseline | 通過；typecheck、Extension 50 tests、package、VS Code smoke 與 Repository unittest 84 tests 全部 exit code 0，security boundary regression 通過。EVID-007、EVID-008、EVID-009、EVID-010、EVID-011、EVID-012 | TASK-001、TASK-002、TASK-003、TASK-004、TASK-005 |

## Evidence 摘要

- EVID-005（regression，passed，current）：`extension-package` exit code `0`；`0.2.0` bundle/manifest 與 VSIX verifier 通過，59 bootstrap files、108 VSIX entries。
- EVID-007（regression，passed，current）：`extension-smoke` exit code `0`；VS Code Extension Host 使用既有 1.131.0 安裝成功載入。
- EVID-008（regression，passed，current）：`unit-tests` exit code `0`；Repository Python unittest `84/84` 通過。
- EVID-009（regression，passed，current）：`extension-typecheck` exit code `0`。
- EVID-010（regression，passed，current）：`extension-tests` exit code `0`；Extension `50/50` 通過。
- EVID-011（acceptance，passed，current）：完成 final acceptance review，核對搜尋、refresh、bootstrap、Dashboard/help、package 與既有 artifact 保留。
- EVID-012（review，passed，current）：完成 high-risk independent review，核對 allowlist、hash/path、non-overwrite、rollback、CSP/no process/no network 與 legacy compatibility。
- EVID-001～EVID-003 是版本同步前或較早 source fingerprint 的歷史 evidence；EVID-004、EVID-006 是 sandbox esbuild ACL 診斷失敗，之後以同一宣告命令升權重跑為 EVID-005、EVID-007 成功，均不代表產品驗證失敗。

## Profile 證據

- `feature` profile 所需的 `acceptance` 與 `regression` 均有 current/passed evidence；high-risk 額外完成 `review`。
- 第一個 vertical slice 由 Wiki 搜尋 model/render seam、Extension host refresh、bootstrap contract 與 package smoke 串接驗證；沒有新增 CLI、machine schema 或 public command。

## 基線更新

不更新 `.devweave/baseline/**`。本次是 Extension 效能、搜尋、bootstrap contract 與 local help 的 additive implementation，既有治理基線與品質門檻沒有改變；變更以本 Work Item evidence、package verifier、Wiki promote/seal 與 G3 reconciliation 留存。

## Wiki 知識提升

Knowledge Review 為 `promote`，rationale 是保存 WikiSearchModel、RefreshCoordinator、deterministic snapshot、0.2.0 allowlisted bootstrap/partial repair、embedded help 與 runtime security 的可重用知識。affected pages 為 `wiki/modules/knowledge-engine.md`、`wiki/overview.md`；covered changed paths 完整，uncovered 為空。

- upsert：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`。
- coupled：`wiki/index.md`、`wiki/log.md`；新增 module 導覽並 append 一筆 work-attributed promote log。
- 六個頁面均由 `knowledge seal` 以 current source fingerprint 與 `verified_by: 20260804-102428-feature-vs-code-extension-wiki` 完成；Knowledge status 為 healthy，critical/stale/unsealed/uncovered warnings 為 0。
- 沒有 delete、baseline update 或未宣告 Wiki diff；promote content targets 為 4，未超過上限。

## 殘餘風險

- 大型 Wiki 的實際體感仍取決於 VS Code Webview 與磁碟 I/O；本次以 deterministic unit/concurrency seam 與 smoke 驗證，不加入 production telemetry。
- `devweave bind` CLI 只能回報 `awaiting_hook`，無法觀察 Codex session hook；本次 guard write 未被拒絕，G3 仍會重新檢查完整 Wiki diff 與 plan coupling。
- 無 waiver、無 critical diagnostic、無未覆蓋 changed path；實際使用者 workspace 的內容衝突仍需由使用者處理後重跑補齊。

## 驗收結論

實作與 release-level verification 已完成：Wiki 搜尋改為 Enter 套用的大小寫不敏感包含式查詢，輸入與結果 DOM 穩定；watcher/snapshot 具 debounce、single-flight、latest-pending 與 deterministic parallel projection；bootstrap 擴充為完整 0.2.0 DevWeave control suite，支援安全 partial repair、conflict 保留、completeness Dashboard 與 embedded help。`0.2.0.vsix`、Extension tests、smoke、typecheck 與 Repository tests 均通過，Wiki promote/seal 亦完成。本 artifact 現可提交 G3 acceptance review，等待使用者明確核准或拒絕。

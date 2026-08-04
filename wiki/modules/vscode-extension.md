---
title: DevWeave VS Code Extension
type: module
sources: [vscode-extension/esbuild.mjs, vscode-extension/package.json, vscode-extension/scripts, vscode-extension/src, vscode-extension/webview]
last_updated: 2026-08-04
tags: [module, vscode, control-center]
status: active
source_fingerprint: "sha256:a134e32d7f2d5a9e04c21d5a71b801bc6706aba3a6c7d2c686b24589906ebb69"
verified_by: 20260804-183511-feature-g1-g2-wiki-extension-bundle
---

# DevWeave VS Code Extension

## Responsibility

`devweave-control-center` 是 DevWeave repository 的唯讀 Control Center。Extension host 將 project、Work Item、Wiki、evidence、diagnostics 與 bootstrap completeness 投影給 Webview；workflow decision 仍以 prompt handoff 回到 Codex Chat，Extension 不執行 DevWeave engine、CLI、shell、Git 或 network。

## Webview interaction

- Knowledge 搜尋由 `WikiSearchModel` 保存 `draftQuery` 與 `appliedQuery`。輸入期間只更新 draft，因此 input DOM、focus、selection 與字元順序穩定；按 Enter 才套用查詢。
- 套用後以大小寫不敏感的 `includes` 搜尋 title、path 與 body preview；拼字錯誤不保證命中。type 是精確分類篩選，show-all 只控制可見頁數。
- 結果與 metrics 使用 stable DOM seam，`RenderScheduler` 合併連續 local updates；搜尋不重建整個 Knowledge section，也不觸發 workspace scan。
- Help 是 Extension-local 的 lazy section，內容包含初始化、workflow/Gate、Wiki、companion skills 與安全邊界；不寫入 target workspace，也不依賴網路。
- Verification projection 對 high-risk acceptance 增加 `Independent Review` readiness：current passed 是 ready，missing/unavailable/advisory 是 attention，critical finding 是 not-ready；raw evidence 展開區顯示 result、severity、reviewer、report hash 與 findings。

## Refresh and snapshot

Workspace watcher 保留自動 refresh，事件經 250ms debounce 後交給 `RefreshCoordinator`。Coordinator 只允許一個 read in flight，burst 中只保留最新 pending request；成功 publish 的 snapshot 不會被較舊結果覆蓋。`WorkspaceSnapshotReader` 對獨立的 project、Wiki、Work Item artifacts、evidence 與 events 讀取平行化，最後依固定 path/id 排序合併 diagnostics 與 projection。

## Bootstrap contract

Production bundle `0.2.0` 使用 manifest 固定完整控制套件：`devweave`、`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling`、`tdd` 六組 skills，加上通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter。README、docs、產品 source、tests、fixtures、work item 與 history 不會成為 target workspace 的 bootstrap files；使用手冊只留在 Extension help。Project、三份 baseline 與三份 Wiki starter 明確宣告 `adopt-compatible` contract，其餘 controls 宣告 `exact`。

`BootstrapInstaller.inspect()` 先驗證 manifest path、byte length 與 SHA-256，再依 `bootstrap-compat.ts` shared validator 檢查 semantic identity。合法 evolved project/baseline/Wiki bytes 會 adopted；AGENTS、skills、hook、lock 與其他 controls 仍以 exact bytes 判定。初始化或修復只建立 missing paths，不同或不合法內容永不覆寫並列為 conflict；只要仍有 missing 或 conflict，report 與 Dashboard 就標示 partial；若中途寫入失敗，僅 rollback 本輪新增內容，既有檔案保持不變。重跑完整 bundle 是 idempotent。

## Security and compatibility

Runtime 維持 CSP、no process、no shell、no external network 與 preview-first public command boundary。所有 workspace write 都集中在使用者確認後的 allowlisted bootstrap installer；snapshot、搜尋、help、prompt composition 與 Independent Review readiness 都是 Extension-local/read-only。Extension 不啟動 Review Agent、不呼叫 Python engine、不判定或核准 gate；0.2.0 VSIX 另行產出，既有 dirty `0.1.0.vsix` 保留不覆寫；public commands 與 legacy snapshot projection 維持相容。

## Verification seams

`WikiSearchModel`、`RenderScheduler`、`RefreshCoordinator`、instrumented snapshot reader、`bootstrap-compat.ts` 與 `BootstrapInstaller.inspect()` 是不依賴 VS Code UI 的測試 seams。package verifier 會檢查 manifest 每個 entry 的 destination、byte length、SHA-256、policy/kind 與 VSIX version/entries；smoke test 再確認 Extension Host 可載入 bundle。

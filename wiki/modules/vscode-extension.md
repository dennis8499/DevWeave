---
title: DevWeave VS Code Extension
type: module
sources: [vscode-extension/esbuild.mjs, vscode-extension/package.json, vscode-extension/scripts, vscode-extension/src, vscode-extension/webview]
last_updated: 2026-08-04
tags: [module, vscode, control-center]
status: active
source_fingerprint: "sha256:c56661602db690c56357aa89738a9f8405fad4115b9e41dcdc3d17dd84115d74"
verified_by: 20260804-102428-feature-vs-code-extension-wiki
---

# DevWeave VS Code Extension

## Responsibility

`devweave-control-center` 是 DevWeave repository 的唯讀 Control Center。Extension host 將 project、Work Item、Wiki、evidence、diagnostics 與 bootstrap completeness 投影給 Webview；workflow decision 仍以 prompt handoff 回到 Codex Chat，Extension 不執行 DevWeave engine、CLI、shell、Git 或 network。

## Webview interaction

- Knowledge 搜尋由 `WikiSearchModel` 保存 `draftQuery` 與 `appliedQuery`。輸入期間只更新 draft，因此 input DOM、focus、selection 與字元順序穩定；按 Enter 才套用查詢。
- 套用後以大小寫不敏感的 `includes` 搜尋 title、path 與 body preview；拼字錯誤不保證命中。type 是精確分類篩選，show-all 只控制可見頁數。
- 結果與 metrics 使用 stable DOM seam，`RenderScheduler` 合併連續 local updates；搜尋不重建整個 Knowledge section，也不觸發 workspace scan。
- Help 是 Extension-local 的 lazy section，內容包含初始化、workflow/Gate、Wiki、companion skills 與安全邊界；不寫入 target workspace，也不依賴網路。

## Refresh and snapshot

Workspace watcher 保留自動 refresh，事件經 250ms debounce 後交給 `RefreshCoordinator`。Coordinator 只允許一個 read in flight，burst 中只保留最新 pending request；成功 publish 的 snapshot 不會被較舊結果覆蓋。`WorkspaceSnapshotReader` 對獨立的 project、Wiki、Work Item artifacts、evidence 與 events 讀取平行化，最後依固定 path/id 排序合併 diagnostics 與 projection。

## Bootstrap contract

Production bundle `0.2.0` 使用 manifest 固定完整控制套件：`devweave`、`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling`、`tdd` 六組 skills，加上通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter。README、docs、產品 source、tests、fixtures、work item 與 history 不會成為 target workspace 的 bootstrap files；使用手冊只留在 Extension help。

`BootstrapInstaller.inspect()` 先驗證 manifest path、byte length 與 SHA-256。初始化或修復只建立缺少且無衝突的檔案：同 bytes 會 adopted，不同 bytes 永不覆寫並列為 conflict。只要仍有 missing 或 conflict，report 與 Dashboard 就標示 partial；若中途寫入失敗，僅 rollback 本輪新增內容，既有檔案保持不變。重跑完整 bundle 是 idempotent。

## Security and compatibility

Runtime 維持 CSP、no process、no shell、no external network 與 preview-first public command boundary。所有 workspace write 都集中在使用者確認後的 allowlisted bootstrap installer；snapshot、搜尋、help 與 prompt composition 都是 Extension-local/read-only。0.2.0 VSIX 另行產出，既有 dirty `0.1.0.vsix` 保留不覆寫；public commands 與 legacy snapshot projection 維持相容。

## Verification seams

`WikiSearchModel`、`RenderScheduler`、`RefreshCoordinator`、instrumented snapshot reader 與 `BootstrapInstaller.inspect()` 是不依賴 VS Code UI 的測試 seams。package verifier 會檢查 manifest 每個 entry 的 destination、byte length、SHA-256 與 VSIX version/entries；smoke test 再確認 Extension Host 可載入 bundle。

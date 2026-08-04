# 工作摘要：修正 VS Code Extension 效能、Wiki 搜尋與完整初始化

<!-- DEVWEAVE:artifact=brief version=1 work=20260804-102428-feature-vs-code-extension-wiki kind=feature -->

## 問題與目標

DevWeave VS Code Extension 的實際使用者回報三項問題：Control Center 操作明顯 Lag、Wiki 搜尋輸入字元會倒序，以及初始化後只得到 `devweave` skill，無法在新 workspace 直接具備完整 DevWeave 治理能力。

本工作目標是讓 Extension 在大型或快速變更的 workspace 中維持可操作，讓 Wiki 搜尋結果可預期且不破壞輸入焦點，並讓初始化／部分初始化修復產生完整且可驗證的 DevWeave 控制套件。

## 現況證據

### Wiki facts

- `wiki/index.md` 指向 overview 與 knowledge workflow；目前沒有專用的 VS Code Extension module page。
- `wiki/modules/knowledge-engine.md` 的 source fingerprint stale；已記錄 gap，current source behavior 以程式碼為準。
- Wiki 說明 Extension 是 filesystem projection，且 bootstrap 應涵蓋 hook、project、baseline、Wiki 與 skill 的 lifecycle 邊界。

### Source-backed facts

- `webview/main.ts` 在每次 `wiki-query` input event 呼叫 `renderKnowledgeOnly()`，該函式替換整個 Knowledge section；搜尋使用大小寫不敏感的 `includes`，輸入框因此可能失去原游標位置。
- `extension.ts` 為多個 workspace glob 建立 watcher，所有事件都進入 250ms debounce，但 refresh 沒有 single-flight 或最新結果淘汰機制。
- `snapshot.ts` 的 baseline、Wiki、work item、artifact 與 evidence 讀取多處逐一 await，存在可平行化的獨立 filesystem reads。
- `esbuild.mjs` 現行 manifest 包含 hook、project、baseline、Wiki starter 與完整 `devweave` skill，但不包含 `AGENTS.md`、`skills-lock.json` 或五個核准 companion skills；`initialize()` 在 project.json 存在時直接回報 already initialized。
- 現有 typecheck、39 個 Extension unit tests 與 84 個 Repository unittest 通過；工作樹既有 `vscode-extension/devweave-control-center-0.1.0.vsix` 修改必須保留。

### Inferences

- 倒序輸入與搜尋 Lag 共享同一個 DOM replacement 根因；先讓輸入 draft 與已套用 query 分離並只更新結果區，可同時修正兩者。
- refresh 合併與 snapshot read parallelism 可降低 watcher storm 的重複成本，不改變 filesystem snapshot 的非權威語意。
- 完整初始化需要可檢查的 manifest contract 與 partial repair，而不是只以 project.json 是否存在判定完成。

### Unresolved gaps

- 尚未有大型 Wiki 的現場效能量測；以 deterministic call-count/concurrency tests 與手動大型 fixture 驗證，暫不加入 production telemetry。
- VSIX package 內容需在實作後重新建立並檢查；現有 0.1.0 artifact 不覆寫。

## 範圍

本工作涵蓋 `vscode-extension/**` 的 Webview interaction、snapshot refresh、bootstrap installer／manifest、embedded help、tests、package metadata 與 0.2.0 artifact 驗證；`wiki/**` 僅在 verification 依 Knowledge Review 更新受影響頁面及 index/log。

公開行為固定為：Wiki 搜尋按 Enter 套用大小寫不敏感的包含式查詢；workspace 變更保留自動 refresh 但合併重複事件；bootstrap 包含核心 skill、五個核准 companion skills、通用 AGENTS、skills lock、hook、project、baseline 與 Wiki starter；既有不同內容永不覆寫。

## 非目標

- 不導入 typo-tolerant fuzzy ranking、向量資料庫、全文索引或外部搜尋服務。
- 不讓 Extension 執行 Python／shell／Git／Codex CLI，也不新增公開 machine command 或修改 DevWeave engine schema。
- 不把 README/docs、產品 source、tests、fixtures、work item 或歷史紀錄寫入被初始化的 workspace；使用手冊只嵌入 Extension 說明分頁。
- 不覆寫既有 AGENTS、skills、project、baseline、Wiki 或其他使用者檔案；不建立 branch、worktree、commit、push、PR 或 deployment。

## 風險

風險等級：high

風險來自 public VSIX package contract、workspace bootstrap writes、Webview render lifecycle 與高頻 filesystem events 的交互作用。所有 bootstrap writes 經 manifest integrity、path safety、non-overwrite preflight 與 rollback；既有 0.1.0 VSIX 保留，0.2.0 另行產出。以 Extension unit/security/typecheck/package/smoke 與 Repository unittest 作為回歸基線，並以 high-risk independent verification evidence 驗證 package 與 repair 行為。

## Profile 補充

本 work 採 feature profile：保留既有 public command、filesystem-only projection、CSP 與 no-network/no-process 邊界；新增的 `WikiSearchModel`、`RefreshCoordinator` 與 bootstrap inspection 會成為可測試 seam。G1 後由 G2 固定 task order、failure modes、rollback 與 package acceptance，再開始產品 source implementation。

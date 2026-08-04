# 工作摘要：修正 G1/G2 問答、Wiki 初始化與 Extension bundle 相容性

<!-- DEVWEAVE:artifact=brief version=1 work=20260804-183511-feature-g1-g2-wiki-extension-bundle kind=feature -->

## 問題與目標

本工作服務使用 DevWeave 進行需求與設計確認的 repository maintainer，以及使用 VS Code Control Center 初始化或檢視 workspace 的 maintainer。

目前有三個相互關聯的問題：G1/G2 的 material decision 仍以自由文字對話呈現；Wiki 初始化在檢查既有內容前已開始建立 `.devweave` 控制檔；Extension 把 bootstrap template 的 exact hash 當成既有 project、baseline 與 Wiki starter 的唯一合法內容，導致已完成第一個需求、內容已合法演進的 workspace 仍顯示「補齊 DevWeave control bundle」。

目標是保留單一 DevWeave lifecycle、三道人工作業 Gate、no-overwrite 與 fail-closed 安全邊界，同時：

1. 讓 G1/G2 優先使用 Codex host 的原生選項問答；無原生能力時使用相同選項、推薦與自訂欄位的結構化 fallback。
2. 讓 Wiki 初始化先完成唯讀 preflight；非保留自訂內容可被保留並採用，保留 starter path 的真正型別/frontmatter 衝突仍阻擋且不留下半套控制檔。
3. 讓 Extension 對符合現行 contract 的 evolved project、baseline 與 Wiki starter 做 semantic adoption，只建立缺檔、不覆寫既有內容，真正不相容的檔案仍 fail closed。

成功訊號是：G1/G2 問答規則可由 repository contract 驗證；Wiki conflict 不會先產生 `.devweave` partial state；合法 evolved workspace 的 snapshot/bootstrap inspection 不再把上述檔案列為 conflict；所有既有 high-risk verification commands 通過。

## 現況證據

### Wiki facts

- G1 context 已依序記錄 `wiki/index.md`、`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`；每頁均保存 status、content hash 與 stored/computed source fingerprint。
- `wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md` 與 `wiki/modules/vscode-extension.md` 的 source fingerprint stale，已在 context 中先記錄 gap；因此不把它們描述的舊 exact-byte/bootstrap 或 chat-only 行為直接當作現行真相。
- Wiki architecture、knowledge engine 與 Extension module 都記錄目前沒有 pending-question engine state/CLI/schema，且 Extension 不執行 engine、shell、network；這些邊界保留，新的問答能力放在 router/host interaction contract。

### Source-backed facts

- `knowledge_core.inspect_wiki()` 對非空但沒有 `wiki/index.md` 的內容回報 conflict；`bootstrap_wiki()` 由 `init_project()` 在 `.devweave` 目錄、project 與 baseline 建立後才呼叫，因此 Wiki conflict 可能留下 partial control state。
- `BootstrapInstaller` 會驗證 bundle source integrity，對既有檔案只接受完全相同 bytes；`WorkspaceSnapshotReader.readBootstrapCompleteness()` 也以 manifest byte length/SHA-256 直接判斷 conflict。
- `vscode-extension/esbuild.mjs` 的 project/baseline/Wiki starter 是最小 bootstrap templates，而現有 workspace 的 accepted project、baseline 與 Wiki 內容已加入 commands、provenance、G1/G2/G3 與既有知識。
- 現有工程已配置 high profile：Extension package、smoke、unit/typecheck 與 root Python unittest；不需新增 verification command。
- `new` 與 `feature` 已是兩個既有 entry profile；本工作保留兩者，不新增 hard eligibility guard。

### Inferences

- Extension 顯示的「補齊」主要是 template hash 與合法 evolved content 被錯誤視為同一類 conflict，而不是 project.json 本身無效。
- Wiki 初始化問題同時來自 compatibility 規則過窄與寫入順序；只放寬規則而不先 preflight，仍可能在真正保留 path conflict 時留下 partial state。
- Bootstrap compatibility 必須是目的地明確的 semantic validator；任意不同 bytes 不能全面採用，否則會削弱 skills、hook、lock 等 exact control files 的 fail-closed 保護。

### Unresolved gaps

- Codex Chat/CLI 的 native question facility 不是此 repository 可直接控制的公開 engine API；實作須 capability-detect host，並保留 deterministic structured fallback，不假設未記錄的統一 API。
- Gate 是否也改用 native question 未被明確選定；本 Work Item 採保守假設，只替換 G1/G2 material decisions，`$devweave approve` 保持既有明確人工 Gate。

## 範圍

### Router 與文件

- 更新 DevWeave router、requirements/design phase guidance、root/target `AGENTS.md`、README 與使用手冊，定義 native-first、逐題、推薦選項、Other/freeform 與 structured fallback contract。
- 在 G1 guidance 提示 `new` 適合第一個 vertical slice、`feature` 適合既有產品，但不阻擋使用者選擇。

### Python engine

- 調整 Wiki reserved starter compatibility 與 `init_project()` preflight/順序；保留既有 `knowledge_conflict` code、no-overwrite 與 `knowledge bootstrap` 的獨立 lifecycle。
- 補齊 Python regression tests，覆蓋自訂 Wiki、保留 path conflict、no-partial-init 與 bootstrap advisory flow。

### VS Code Extension

- 在 manifest/file contract 增加 exact 或 destination-specific compatible existing-file policy。
- 讓 installer 與 snapshot 共用 project、baseline、Wiki starter validators；合法 evolved bytes 採用，missing 才寫入，invalid/path/type/integrity conflict 仍 fail closed。
- 更新 build manifest、package verifier、UI projection 與 unit/package/smoke tests。

### Verification knowledge

- G3 依實際 diff 更新或涵蓋 product、architecture、quality baseline。
- 只在 verification 依 knowledge plan promotion 更新受影響的 overview、workflow、knowledge engine、Extension 等 source-bound Wiki pages 與 coupled index/log。

## 非目標

- 不新增第二套 router、question engine、pending-question state、CLI command、JSON schema、VS Code question UI 或 question ledger。
- 不修改 companion skill contents、`skills-lock.json`、DevWeave JSON/JSONL ledger，不自動覆寫既有 target workspace 的 exact policy/skill/hook/lock 檔案。
- 不改變 `$devweave approve`、G1/G2/G3 Gate semantics、Wiki verification write guard、Knowledge Review 或 high-risk isolated reviewer contract。
- 不讓 Extension 執行 Python、CLI、shell、Git、network、Codex Agent 或 live Wiki mutation。
- 不把任意 Wiki custom content、managed:false project、錯誤 frontmatter、錯誤 baseline identity 或 malformed manifest 視為可採用內容。

## 風險

風險等級：high

- native question 能力無法由 repository 保證，因此 fallback 必須維持單題、選項順序、推薦與自訂答案的可驗證 contract。
- Wiki init 與 bootstrap compatibility 都涉及檔案寫入邊界；所有 conflict、symlink/type/path、integrity、malformed data 均需在寫入前拒絕，既有 bytes 不得覆寫。
- semantic adoption 若過寬可能掩蓋損壞的 project/baseline/Wiki；validator 必須依 destination contract 限定，並以 negative regression tests 保護。
- 高風險基線是現有 83 項 Python suite、Extension unit/typecheck/package/smoke 與既有 high verification profile；G3 需 current Independent Review。

## Profile 補充

本工作採 `feature`：產品已有完整 workflow、Python engine 與 VS Code Extension，需求是基於現況修正互動、初始化與相容性能力；驗收必須包含功能 acceptance 與 regression evidence。`new`/`feature` 的選擇提示屬文件與 G1 guidance 變更，不新增硬性 admission rule。

<!--
- new：願景、限制、roadmap 與第一個 vertical slice。
- feature：現況、價值、影響面與相容性。
- refactor：行為契約、技術問題、安全接縫與基準。
- bug：expected/actual、重現證據與 root-cause 假設。
-->

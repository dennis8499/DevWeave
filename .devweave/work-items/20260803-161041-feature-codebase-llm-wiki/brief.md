# 工作摘要：整合 Codebase LLM Wiki 閉環

<!-- DEVWEAVE:artifact=brief version=1 work=20260803-161041-feature-codebase-llm-wiki kind=feature -->

## 問題與目標

DevWeave 已具備 Wiki skeleton、source fingerprint、lint、affected-page refresh 與 seal，但 Codebase LLM Wiki 尚未形成可持續使用的閉環。`assets/wiki/starter` 只在缺檔時採用，九種 page templates 沒有 machine scaffold 入口；當既有頁面沒有 sources 時，G3 也無法由 affected-page 機制推動 Wiki 成長。結果是 agent 雖被要求 Wiki-first，實際探索仍經常回到 raw source，無法穩定縮小讀取範圍。

目標是讓 DevWeave 使用者與執行 Work Item 的 agent 能先透過一個受 gate 管理的 bootstrap 建立核心知識，之後每次 G1 固定從 index 與最多五個內容頁定位資訊，每次 G3 都完成 knowledge review，並只把可長期重用的知識提升到 Wiki。成功訊號是 bootstrap、query、review、coverage、scaffold、seal 與 VS Code Extension 入口都具有可執行、可追溯、向後相容的契約。

## 現況證據

- `wiki/index.md` 只列出 `wiki/overview.md`，而 overview 是無 sources 的 placeholder；G1 已記錄此 gap 後才回查 raw sources。
- `knowledge_core.py` 的 `STARTER_FILES` 與 `bootstrap_wiki()` 只建立缺少的 starter files；`assets/wiki/templates/` 的 overview、architecture、module、entity、pattern、decision、dependency、guide、synthesis 沒有被 CLI 或 engine 呼叫。
- `devweave.py` 目前只路由 `knowledge status/context/plan/seal`；`devweave_core.py` 的新 work state 只有 `base_knowledge`、簡化的 `knowledge_context` 與 `knowledge_updates`，沒有 bootstrap profile 或 review disposition。
- `work_knowledge_status()` 只計算既有 `affected_pages`；`_validate_knowledge_acceptance()` 只強制刷新 source overlap 命中的既有頁面，因此無 sources 的空白 Wiki 不會累積新頁。
- G1 已限制 index 加最多五頁，但 context state 不保存逐頁 content hash/status/source fingerprint，無法精確表達查閱時的知識快照。
- VS Code Extension 的 `PublicCommandIntent`、fail-closed protocol、prompt composer、下拉 UI 與 Command Palette 只支援既有八個 public verbs；Knowledge projection 也沒有 bootstrap、coverage 或 review 欄位。Extension 現有安全邊界是只預覽/複製 mutation prompt，不直接執行 engine。
- `.devweave/baseline/` 已接受 Wiki-first、獨立 knowledge fingerprint、single-router 與 Extension no-execution 邊界，本工作項須在這些邊界內擴充能力。

## 範圍

- 擴充 Python engine、machine CLI 與 additive work state，加入 idempotent Wiki bootstrap、逐頁 context records、knowledge review、coverage projection、五頁 plan 上限與 template scaffold。
- 強化 G3 validation 與 seal，讓 promote/no-update、bootstrap 完成條件、placeholder/token 拒絕、index/log coupling 與 currentness 都可被 machine 驗證。
- 將九種 canonical templates 接上 scaffold，同時保留 configured Wiki root、repo-relative sources、原子寫入與 guard 最小授權。
- 更新 DevWeave router、phase references、contracts、root policy、README 與繁體中文使用手冊。
- 擴充 VS Code Extension 的 public intent、protocol、prompt、snapshot、Knowledge panel、下拉選單與 Command Palette；三個入口都只產生 `$devweave wiki bootstrap` prompt。
- 新增 Python、CLI、guard、repository contract、Extension unit/smoke 與 lifecycle regression tests；G3 更新受影響 baseline 與 knowledge pages。

## 非目標

- 不導入 RAG、向量資料庫、全文索引、Tree-sitter cache、外部服務或第三方 Python runtime dependency。
- 不量測或宣稱精確 Token 節省比例。
- 不新增獨立 ADR、Guide、Synthesis public workflow，也不建立第二個 Wiki skill/router；九種 page type 只由 scaffold 共用。
- Bootstrap 不接受 repository 子路徑 scope，也不要求使用者先互動選模組。
- 不強迫每個 Work Item 都產生 Wiki diff；只強迫新式 Work Item 完成 current Knowledge Review。
- Extension 不執行 Python、shell、Git、network 或直接 Wiki write；不改變既有 workspace bootstrap installer 的唯一 write seam。
- 不建立 branch、commit、push、PR、release 或 deployment。

## 風險

風險等級：high

此變更會擴充 public chat surface、machine CLI/state、G1/G3 fingerprint 與 gate validation，若 currentness 或 legacy 判斷錯誤可能阻擋既有 Work Item，若 scaffold/guard 邊界錯誤可能寫到未授權路徑。採 additive schema v1、missing-field legacy bypass、fail-closed path/type/source validation、原子 page writes、固定五頁上限與完整 lifecycle/Extension security regression 降低風險。現有 Python unit suite及 Extension package、smoke、unit、typecheck 都是可重跑基線；沒有資料 migration 或不可逆外部副作用。

## Profile 補充

- Profile：feature。
- 第一個可驗證成果是：在暫存 managed repository 中，`knowledge bootstrap` 能建立/續接 bootstrap Work Item；完成 G1/G2 後，可由 review、plan、scaffold、seal 與 G3 建立 3–5 個核心頁，之後一般 Work Item 能以 index 加最多五頁探索，並在 G3 選擇 promote 或合法 no-update。
- 使用者介面影響：新增 `$devweave wiki bootstrap` 及 VS Code 三個安全入口；既有八個 verbs、JSON envelope、gate names 與 Extension preview/copy 行為保持相容。
- 資料影響：只新增 additive work-state fields；既有 state 缺少 `knowledge_review_required` 時不追溯阻擋，既有 Wiki 與使用者內容不被 bootstrap/scaffold 覆寫。

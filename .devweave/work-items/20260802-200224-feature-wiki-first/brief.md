# 工作摘要：整合 Wiki-first 探索與知識提升

<!-- DEVWEAVE:artifact=brief version=1 work=20260802-200224-feature-wiki-first kind=feature -->

## 問題與目標

DevWeave 目前能保存 work item 的需求、設計、任務、驗證證據與三道核准，但探索階段仍需每次從 raw sources 重新建立 codebase 脈絡。目標是把 Codebase LLM Wiki 的可追溯 Markdown 知識模型整合進單一 DevWeave router，使 Codex 在 G1 先使用持久知識導覽，遇到缺失、陳舊或矛盾時才回溯 raw sources，並只在 G3 將已驗證事實提升為長期知識。

主要使用者是以 Codex 操作語言中立 repository 的開發者。成功訊號是：新專案能非破壞性建立 `wiki/` 骨架；每個新 work item 留下 Wiki-first 探索脈絡；實作造成的相關知識陳舊會阻擋 G3；刷新後不會使 source-bound evidence 無故失效；原本公開 chat verbs、三道 gate 與單一 skill 契約保持不變。

## 現況證據

- `tests/test_repository_contract.py` 明確要求 `.agents/skills/` 下只有 `devweave`，所以不能直接安裝第二個 `codebase-wiki` router。
- `.agents/skills/devweave/scripts/devweave_core.py` 的 `init_project()` 目前只建立 `.devweave/` project、work items 與三份 baseline，沒有持久 codebase knowledge layer。
- `.agents/skills/devweave/references/requirements-phase.md` 要求直接檢查 live repository 與 accepted baseline，尚未定義 Wiki-first context、查閱頁面上限或 gap 紀錄。
- `.agents/skills/devweave/scripts/guard.py` 只識別 work artifacts、living baseline 與 G2 後的 scope paths，沒有 verification-only Wiki target 授權。
- `git_snapshot()` 目前排除 `.devweave/`、DevWeave skill 與 `.codex/`；若直接加入根目錄 `wiki/` 而不建立獨立 fingerprint，Wiki 提升會使 source evidence stale。
- 來源專案 `dennis8499/code-base-llm-wiki` main commit `5391fd0fca2eff9ebb9c8d242c4d3cf4bedc11e3` 提供 frontmatter parser、Wiki lint、index、stale check 與頁面模板；使用者已確認具備重用權利。
- 變更前基線：DevWeave 48 項 unit tests 全數通過；來源專案 34 項 tests 全數通過；現有 `devweave` skill 通過 `quick_validate.py`。

## 範圍

- 在既有 `devweave` skill 內加入 Wiki bootstrap、frontmatter、內容指紋、health/lint、index/log coupling 與 knowledge snapshot 能力。
- 擴充 engine CLI 與 state，支援 `knowledge status/context/plan/seal`，但不新增公開 chat verb。
- 將 G1 探索、G3 驗證、acceptance fingerprint、status/instructions 與 guard 接上 knowledge lifecycle。
- 保持 schema version 1，以 additive defaults 支援既有 project 與 active work item；相容 Wiki 漸進 seal，不相容內容只報 conflict。
- 更新 Codex-only skill metadata、phase references、contracts、templates、AGENTS、README、fixtures 與 tests。
- 目標程式路徑為 `.agents/skills/devweave/`、`.codex/hooks.json`、`AGENTS.md`、`README.md`、`tests/` 與 `fixtures/`；本工作項不在 framework repo 根目錄建立實際 `wiki/`。

## 非目標

- 不加入第二個 `$codebase-wiki` skill、GitHub Copilot surface、獨立 installer/updater、release assets 或 custom agents。
- 不加入 RAG、向量資料庫、Tree-sitter/source index、MCP 搜尋服務、SQL Server live evidence或自動全庫 ingest。
- 不改變 `$devweave new/feature/refactor/bug/next/status/revise/approve` 的公開入口，不跳過 G1/G2/G3 人工核准。
- 不以 Wiki 取代 `.devweave/baseline/`；前者保存細緻探索知識，後者仍是已驗收的治理真相。
- 不替既有不相容 `wiki/` 自動搬移、覆寫或刪除內容，也不自行建立 branch、commit、push 或 release。

## 風險

風險等級：high

本變更會修改所有 managed repositories 共用的 project 初始化、work state、gate fingerprint 與 PreToolUse 寫入邊界。主要風險是舊 state 無法載入、Wiki 變更錯誤污染 source fingerprint、guard 過度允許或過度阻擋、append-only log 被改寫，以及目錄 hashing 在大型 repo 的成本。設計必須採 additive compatibility、精確路徑驗證、verification-only plan/seal、獨立 knowledge fingerprint、標準函式庫實作與完整回歸測試。回滾可移除新 knowledge contract；舊 project/state 的既有欄位與公開命令不得被破壞。

## Profile 補充

此項為 feature：目前可觀察行為是 DevWeave 只使用 work artifacts 與 baseline，沒有 Wiki-first 探索或 G3 knowledge promotion。預期價值是跨 session 重用已驗證的 codebase 理解，同時以 source fingerprint 與 gate 保持可追溯性。相容性要求是未初始化 repo 仍不隱式啟動；既有 schema v1 project 可在下一次 `init/start` 非破壞性補齊；舊 active work item 不被追溯新增 G3 blocker；既有 48 項測試與 JSON CLI envelope 保持相容。

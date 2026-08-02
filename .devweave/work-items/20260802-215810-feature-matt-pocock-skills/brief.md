# 工作摘要：導入 Matt Pocock 核心工程 Skills 作為階段內方法

<!-- DEVWEAVE:artifact=brief version=1 work=20260802-215810-feature-matt-pocock-skills kind=feature -->

## 問題與目標

DevWeave 目前只提供單一 repository skill，缺少可重複使用的需求訪談、module/interface 設計、系統化除錯與 TDD 方法。目標是在不建立第二套 SDLC 的前提下，將 Matt Pocock 的 `grill-me`、`grilling`、`codebase-design`、`diagnosing-bugs` 與 `tdd` 安裝為 Codex project-local companion Skills，供 DevWeave 目前階段選用。

主要使用者是透過 Codex 執行 DevWeave-managed work item 的開發者。成功訊號是五個 Skills 可被 Codex 發現、既有 DevWeave gate 與 artifact ownership 不變、衝突行為受到 repository policy 約束，且 repository contract 與完整測試套件通過。

## 現況證據

- Wiki-first context 依序讀取 `wiki/index.md` 與 placeholder `wiki/overview.md`；後者尚未記錄 Skill router、companion precedence 或安裝佈局，因此已登錄 gap 後才回溯 raw sources。
- `AGENTS.md`、`.agents/skills/devweave/SKILL.md` 與 README 將 DevWeave 定義為單一 router，並禁止它自行建立 branch、commit、push、PR 或部署。
- `tests/test_repository_contract.py` 目前硬性斷言 `.agents/skills/` 只有 `devweave`；新增 companion Skills 必須同步把契約改為「唯一 router + 精確允許的 companion set」。
- `.devweave/baseline/product.md` 目前記錄「不提供第二套 skill、agent、installer」；驗收時必須更新為不提供第二套 router／orchestrator，但允許受治理的 project-local companion Skills。
- `.devweave/project.json` 已有 `unit-tests` standard verification command；不需要新增 runtime dependency 或改變命令介面。

## 範圍

- 以 project-local copy 安裝五個上游 Skill 目錄及其相依參考檔，並保留安裝器產生的 provenance/lock metadata。
- 在 `AGENTS.md` 定義 DevWeave precedence、階段／寫入／知識／Git／remote tracker 邊界，以及衝突時的 `revise` 規則。
- 在 README 記錄安裝、階段對應、日常呼叫、驗證與手動更新方式。
- 更新 repository contract test，使其驗證唯一 `devweave` router、精確五個 companion Skills，以及不會引入第二套 orchestration surface。
- G3 更新受影響的 product、architecture 與 quality baseline；若 knowledge status 判定需要提升 Wiki，僅依 declared knowledge plan 更新。

## 非目標

- 不安裝或執行 `setup-matt-pocock-skills`、`to-spec`、`to-tickets`、`implement`、`triage`、`wayfinder`、`domain-modeling`、`research`、`prototype` 或 `code-review`。
- 不修改上游五個 Skill 的內容；相容性由 repository-level precedence policy 提供。
- 不新增 DevWeave chat verb、CLI command、state schema、hook、agent、installer、issue tracker 或 runtime dependency。
- 不由 DevWeave 或 companion Skills 建立 branch、commit、push、PR、issue 或部署。
- 不在 G2 或 implementation 階段修改 Wiki。

## 風險

風險等級：standard

主要風險是 model-invoked Skill 可能與 DevWeave gate 或知識讀寫規則衝突。緩解方式是以 `AGENTS.md` 明確定義 precedence、只安裝無第二套 tracker/spec/commit orchestration 的核心集合，並以 contract test 固定允許清單。變更不觸及 runtime、schema 或公開 CLI，且可透過移除 project-local 目錄與 policy 區塊回復，因此維持 standard risk。

## Profile 補充

此 feature 影響 Codex 的 Skill discovery surface、repository guidance 與 contract tests；不影響 DevWeave machine CLI、JSON state、產品資料或其他 agent。第一個可驗證成果是：新 Codex session 可發現精確五個 companion Skills，而任何寫入、artifact、gate、Wiki、Git 與 remote tracker 行為仍由 DevWeave policy 控制。既有公開 verbs 與所有 runtime tests 必須保持相容。

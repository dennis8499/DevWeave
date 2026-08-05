# 工作摘要：優化專案 Skills 可預測性（排除 writing-great-skills）

<!-- DEVWEAVE:artifact=brief version=1 work=20260805-081842-feature-skills-writing-great-skills kind=feature -->

## 問題與目標

DevWeave 目前有六個需要長期維護的 project-local Skills。它們大致可用，但部分內容把觸發、步驟、參考資料與治理邊界混在一起，存在重複、模糊完成條件、過時的不存在 Skill 連結，以及未明確表達 DevWeave phase 限制的情況。repository contract 也會把本次明確排除的 `writing-great-skills` 誤判為 companion 集合成員。

目標使用者是透過 Codex 使用 DevWeave 的開發者與維護者。目標是依 `writing-great-skills` 的 predictability、progressive disclosure、single source of truth、positive steering 與 completion criterion 原則，優化下列六個 Skill 套件：`devweave`、`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling`、`tdd`。

成功訊號是：每個目標 Skill 都有清楚的觸發分支、可執行的步驟或參考入口、可檢查的完成條件；DevWeave 仍是唯一 router；既有 phase/Gate/CLI/schema/Hook 與五個上游 lock provenance 保持相容；`writing-great-skills` 完全未被修改；repository、Extension bundle 與完整驗證均通過。

## 現況證據

### Wiki facts

- 已先讀 `wiki/index.md`，再讀 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md` 與 `wiki/modules/knowledge-engine.md`；四頁均為 active，且 current source fingerprints 已由 `knowledge context` 記錄。
- Wiki 已確認 DevWeave 是唯一 SDLC router，companion Skills 只提供 phase 內方法，G1/G2/G3、Wiki-first、Knowledge Review 與 high-risk review 均由既有 lifecycle 管理。

### Source-backed facts

- `.devweave/project.json` 存在且 `managed: true`；既有 verification profile 已配置 Python unit tests 與 Extension package/smoke/tests/typecheck。
- `.agents/skills/` 有六個目標 Skill，以及本次明確排除且尚未追蹤的 `writing-great-skills`。
- `skills-lock.json` 只記錄五個上游 companion；本次保留其 source、skillPath 與 computedHash，不把 local optimization 寫回 upstream lock。
- `diagnosing-bugs` 含不存在的 `/improve-codebase-architecture` 依賴與 commit/PR 語句；`tdd` 含不存在的 `code-review` 依賴；`grilling`、`tdd` 與 DevWeave phase policy 的互動契約需要明確化。
- `tests/test_repository_contract.py` 目前以 `.agents/skills/*/SKILL.md` 建立精確集合，因此會因 `writing-great-skills` 存在而失敗。

### Inferences

- 這是受治理的 local Skill instruction overlay，不是上游 companion update；因此不應修改 lock provenance，也不應引入新的 router 或 lifecycle。
- 受影響的 Wiki 至少包括以 `devweave` Skill/AGENTS/README 為 source 的 overview 與 workflow architecture；G3 需依 Knowledge Review 刷新並 seal。

### Unresolved gaps

- 已記錄的 Wiki gap：目前 Wiki 尚未描述 local Skill optimization overlay、maintenance-only exclusion 與 completion-criteria 驗證；G1 後只回查必要的 Skill、root policy、lock 與 contract test source。
- PreToolUse binding 目前回報 `awaiting_hook`，因此不能宣稱 guard 已可信；G3 需以完整 scope、diff、fingerprint 與驗證證據補強。

## 範圍

### 目標內容

- 優化六個目標 Skill 的 `SKILL.md`、既有 Markdown references 與必要的 `agents/openai.yaml`。
- 強化 description triggers、phase routing、positive steering、progressive disclosure、completion criteria、相對連結與 stale-reference 清理。
- 保留 `devweave` 的 machine contract、Wiki-first、G1/G2/G3、Knowledge Review、review-record 與 human approval 邊界。
- 更新 `tests/test_repository_contract.py`，將 `writing-great-skills` 視為 maintenance-only exclusion，並補上 metadata/invocation policy 檢查。
- 僅同步必要的 `AGENTS.md`、`.devweave/baseline/architecture.md`、`.devweave/baseline/quality.md`；G3 依 declared knowledge plan 刷新受影響 Wiki 頁面及 coupled index/log。

### 介面與 provenance

- Skill 名稱、主要觸發方式、`devweave` implicit invocation、`grill-me` user-only invocation、公開 chat verbs、CLI、JSON schema、Hook 與 Extension bootstrap 的六個 Skill 集合保持不變。
- `skills-lock.json` 僅作 upstream provenance baseline，source/path/hash 不變。

## 非目標

- 不修改 `.agents/skills/writing-great-skills/` 的任何檔案。
- 不修改 DevWeave Python engine、templates、runtime scripts、HITL template、Extension source 或公開 CLI/schema/Hook。
- 不安裝或引入新的 Skill、router、orchestrator、agent lifecycle、state ledger、tracker、database 或 runtime dependency。
- 不改寫 `skills-lock.json` 的 upstream provenance/hash；不廣泛重寫 README 或使用手冊。
- 不建立 branch、worktree、commit、push、PR、issue、deployment 或 production instrumentation。

## 風險

風險等級：standard

本次只改變 agent instruction、reference hierarchy、治理文字與 contract test，不改產品 runtime、資料、公開 CLI 或安全邊界。主要風險是 Skill wording 改變可能造成 agent 過早完成、跨 phase 寫入或誤觸發；以 explicit completion criteria、保留既有 hard guardrails、G1/G2/G3 驗證、forward-test、完整 unit tests 與 Extension package verification 緩解。變更可由單一 work-item diff 回復，無資料 migration。

## Profile 補充

本工作是 feature profile：第一個可驗證成果是六個目標 Skill 的 instruction/reference 契約完成整理，且新的 Codex session 可依既有 phase 使用它們。G3 必須同時證明 Skill allowlist、frontmatter、relative links、lock provenance、Extension bootstrap、DevWeave runtime 與完整 repository verification 均維持相容。

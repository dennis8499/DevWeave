# 需求與驗收條件：導入 Matt Pocock 核心工程 Skills 作為階段內方法

<!-- DEVWEAVE:artifact=requirements version=1 work=20260802-215810-feature-matt-pocock-skills -->
## 假設與限制

- 目標 agent 為 Codex，採 repository project scope，不進行 global install。
- 上游 Skills 以安裝時取得的原始 copy 使用；DevWeave-specific 規則只寫入 `AGENTS.md`。
- 安裝與更新需要 Node.js、`npx` 與網路，但 DevWeave runtime 仍維持 Python standard library only。
- Codex 需要在安裝後開啟新 session 才能可靠重新掃描 Skills。
- Git 與 remote tracker 操作不在本工作項授權範圍。

## 需求與驗收條件

## REQ-001: 安裝精確的核心 companion Skills
- Priority: must
- Acceptance: AC-001, AC-004
- Description: Repository 必須以 project-local copy 提供 `grill-me`、`grilling`、`codebase-design`、`diagnosing-bugs` 與 `tdd`，且不得額外安裝 Matt Pocock 的 orchestration 或 repository-writing Skills。

## REQ-002: DevWeave precedence 必須保持唯一且明確
- Priority: must
- Acceptance: AC-002, AC-004
- Description: Repository policy 必須規定 DevWeave 擁有 phase、gate、artifact、scope、evidence、Wiki 與 Git／remote 邊界；companion Skills 的衝突指令不得執行。

## REQ-003: Companion Skills 必須依 DevWeave 階段使用
- Priority: must
- Acceptance: AC-002, AC-003
- Description: Requirements 使用 grilling、G2 design 使用 codebase-design、bug discovery 使用非 tracked reproduction loop、G2 後 implementation 使用 tdd；任何核准後決策變更必須走 `devweave revise`。

## REQ-004: DevWeave 公開介面必須保持相容
- Priority: must
- Acceptance: AC-003, AC-005
- Description: 整合不得新增或改變 DevWeave chat verbs、CLI commands、JSON schema、hook contract 或 runtime dependency。

## REQ-005: 上游更新必須是人工受管變更
- Priority: must
- Acceptance: AC-006
- Description: Repository 必須記錄安裝來源，禁止自動更新；每次更新須建立新的 DevWeave feature work item、檢閱 instruction diff 並重新驗證。

## NFR-001: 整合必須可追溯且可回復
- Priority: must
- Acceptance: AC-001, AC-006
- Description: 安裝結果與上游 provenance 必須可檢閱；移除 companion directories 與 policy 文件變更即可回復，不需資料 migration。

## NFR-002: 整合不得擴張執行副作用
- Priority: must
- Acceptance: AC-002, AC-005
- Description: Companion Skills 不得自行建立 issue、branch、commit、push、PR、部署或在未允許階段寫入 source、tests、Wiki、CONTEXT/ADR。

## AC-001: Codex 可發現精確的 Skill 集合
- Requirement: REQ-001, NFR-001
- Scenario: Given 安裝完成的 repository，When 列舉 `.agents/skills/*/SKILL.md` 並檢查 Skill metadata，Then 集合必須等於唯一 router `devweave` 加上五個指定 companion Skills，且每個 Skill 的相依參考檔存在。

## AC-002: Repository policy 阻止 companion Skill 越權
- Requirement: REQ-002, REQ-003, NFR-002
- Scenario: Given 任一 companion Skill 的指令與 DevWeave 衝突，When agent 讀取 `AGENTS.md`，Then DevWeave phase/gate/scope/artifact/evidence/Wiki/Git 規則優先，且 policy 明列 G2 前寫入、Wiki、tracker、Git 與 `revise` 邊界。

## AC-003: 文件提供可直接使用的階段對應
- Requirement: REQ-003, REQ-004
- Scenario: Given 開發者閱讀 README，When 依 feature、design、implementation 或 bug 情境操作，Then 可取得對應的 `$devweave` 與 companion Skill 呼叫範例，且沒有第二套 work-item lifecycle。

## AC-004: Repository contract 自動驗證允許清單
- Requirement: REQ-001, REQ-002
- Scenario: Given repository test suite，When 執行 repository contract tests，Then 測試會拒絕遺漏、額外或冒充 router 的 Skill，並確認五個 companion Skills 的角色與禁止項目由 policy 覆蓋。

## AC-005: DevWeave runtime 與公開 surface 無回歸
- Requirement: REQ-004, NFR-002
- Scenario: Given 完整 repository，When 執行既有 `unit-tests` verification command，Then 所有測試通過，公開 chat verbs、CLI/schema/hook contract 與 standard-library-only runtime 均未改變。

## AC-006: 更新流程可稽核且不會自動套用
- Requirement: REQ-005, NFR-001
- Scenario: Given 上游發布新版，When 維護者查閱 README 與安裝 metadata，Then 文件要求以新的 DevWeave feature 執行 project-scope update、檢閱差異並完成 G3，且 repository 不含自動更新機制。

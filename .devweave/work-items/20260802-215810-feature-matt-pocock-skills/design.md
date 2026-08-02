# 系統設計：導入 Matt Pocock 核心工程 Skills 作為階段內方法

<!-- DEVWEAVE:artifact=design version=1 work=20260802-215810-feature-matt-pocock-skills -->

## 設計摘要

採用「唯一 DevWeave router + 未修改的 project-local companion Skills + repository precedence policy」架構。`devweave` 繼續解析公開 work-item verbs、控制 G1/G2/G3、artifact、scope、evidence、Wiki 與 state；五個 companion Skills 只能在目前 phase 內提供訪談、module/interface 設計、除錯或 TDD 方法。

關鍵不變量如下：

- `.agents/skills/devweave/` 是唯一 SDLC router；其他五個目錄不得建立平行 lifecycle。
- Companion Skills 維持上游原始內容，所有 DevWeave-specific 適配集中在 root `AGENTS.md`，避免 fork drift。
- 寫入產品 source/tests 前必須有 current G2；Wiki 只在 verification 依 knowledge plan 寫入。
- Companion Skills 不得直接寫 DevWeave JSON/JSONL ledger，不得建立 issue、branch、commit、push、PR 或部署。
- 公開 chat verbs、Python CLI、schema version、hook 與 runtime dependency graph完全不變。

## 選項比較

1. **選定：project-local 原始 copy + AGENTS precedence。** 優點是 Codex 可直接發現、團隊可共同版本控制、上游內容易於比對，且 DevWeave 適配集中於單一高優先級 policy。缺點是每次上游更新都需重新檢閱衝突。
2. **拒絕：修改五個上游 SKILL.md。** 可把階段規則寫得更貼近各 Skill，但會形成 fork、增加更新 merge 成本，並違反已核准的「上游原始 copy」限制。
3. **拒絕：安裝完整 Matt Pocock workflow。** `setup-matt-pocock-skills`、`to-spec`、`to-tickets` 與 `implement` 會引入 tracker/spec/commit 等第二套 orchestration，與 DevWeave canonical artifacts 和 Git 邊界衝突。
4. **拒絕：global install。** 無法由 repository 固定版本與 policy，其他專案也會非預期看到相同 Skills。

## 介面與資料流

### Skill discovery interface

安裝命令固定為 project scope、Codex target、explicit allowlist 與 copy mode；implementation 使用 `--yes` 避免互動式 prompt：

```powershell
npx skills@latest add mattpocock/skills --agent codex --skill grill-me --skill grilling --skill codebase-design --skill diagnosing-bugs --skill tdd --copy --yes
```

Installer 只能新增五個對應目錄及其完整相依檔；若產生 `skills-lock.json` 則保留原始內容作為 provenance，不自行發明或修改其 schema。若沒有 lock file，README 的來源、選取集合與手動更新命令加上 committed file diff 即為 provenance。

### Prompt 與 artifact 資料流

```text
使用者意圖
  -> DevWeave status / bind / instructions
  -> 目前 phase 與 approved artifacts
  -> 選用 companion Skill 的方法
  -> 結果回寫 DevWeave artifact 或 CLI evidence
  -> DevWeave validate / human gate
```

- Requirements：明確呼叫 `grill-me`，由 `grilling` 逐題釐清；結論只進入 `brief.md`／`requirements.md`。
- G2 design：`codebase-design` 的 module、interface、seam、adapter vocabulary 用於 `design.md`／`plan.md`；repository glossary 或 approved artifacts 衝突時，以後者為準。
- Bug discovery：`diagnosing-bugs` 先使用既有命令或 `.devweave/cache`／temp harness 建立 failing loop；G2 前不建立 tracked regression test。
- Implementation：current G2 後才使用 `tdd`，一個 TASK 一個 red → minimal green vertical slice，結果透過 DevWeave evidence 對應 AC/TASK。
- Verification：完整 command、cleanup、baseline 與 knowledge promotion 均回到 DevWeave；companion Skills 不新增 phase。

沒有新的 API、資料 schema 或 state transition。新增的公開使用介面只有 README 中可選的 `$grill-me`、`$codebase-design`、`$diagnosing-bugs` 與 `$tdd` 組合範例。

## 失敗模式與回復

- **Node／網路／registry 失敗：** Task 停留在 installing，保留完整錯誤輸出；確認精確目錄後才重試，不手工拼湊部分 Skill。
- **Installer 產生額外 Skill：** repository contract test 失敗；只接受 allowlist 中五個目錄，額外項不得進入驗收 diff。
- **上游 metadata 或相對連結不完整：** targeted contract test 失敗並阻擋 G3；不在本工作項修補上游內容，改為固定可用版本或回到 G2 revise。
- **Companion instruction 與 DevWeave 衝突：** `AGENTS.md` precedence 覆蓋；若仍需改 requirement/design/task，執行 `devweave revise` 回到最早受影響階段。
- **Codex 尚未重新掃描：** filesystem 與 contract tests 可先驗證；manual acceptance 要求新 session 以 `npx skills list -a codex` 或實際 skill discovery 確認。
- **Rollback：** 由明確授權的 Git workflow 回復本 work item diff，移除五個 companion 目錄、lock metadata 與 policy/docs/tests 更新；無資料 migration 或 runtime rollback。
- **Observability：** 使用 allowlist contract test、relative-link integrity、`npx skills list -a codex`、完整 unit tests、`git diff --check` 與 DevWeave G3 evidence。

## 高風險分析

本工作項為 standard risk。沒有資料 migration、認證／隱私邊界、network runtime、公開 API 或 performance path。相容性風險集中於 agent instruction precedence，已由 exact allowlist、root policy、contract tests 與可逆的 project-local copies 處理。Session binding 仍只觀察到 `awaiting_hook`；在 guard confirmation 缺席時，不把 hook 視為可信，G3 必須以完整 diff 與 scope reconciliation 補強驗證。

## 設計決策

## DEC-001: 決策名稱
- Requirements: REQ-002, REQ-003, REQ-004, NFR-002
- Decision: DevWeave 保持唯一 lifecycle router；companion Skills 僅能提供目前 phase 內的方法。
- Rationale: 保留既有 gate、artifact、fingerprint 與 human approval contract，避免平行狀態來源。
- Consequences: 使用者必須先以 `$devweave` 建立／繼續 work item；companion Skill 不能單獨授權寫入或完成工作。

## DEC-002: 採 project-local copy 與精確 allowlist
- Requirements: REQ-001, REQ-005, NFR-001
- Decision: 使用 skills CLI 的 Codex project scope、`--copy`、五個 `--skill` 與 `--yes`，不使用 global 或 `--all`。
- Rationale: Repository 可檢閱、分享與回復安裝內容，且非互動執行不會選入額外 Skills。
- Consequences: Repository 會增加上游 Markdown／script 檔；更新必須由維護者主動執行。

## DEC-003: 以 AGENTS policy 適配，不修改上游 Skill
- Requirements: REQ-002, REQ-003, REQ-004, NFR-002
- Decision: 將 phase、write、knowledge、Git、tracker 與 revise precedence 寫在 root `AGENTS.md`，README 提供人類操作說明。
- Rationale: Root repository policy 可同時約束所有 Skills，且避免維護五個 fork。
- Consequences: Upstream 原文中的 `CONTEXT.md`、ADR、commit 或 review 建議若衝突，一律不執行並改記錄於 DevWeave artifact/evidence。

## DEC-004: Repository contract 驗證唯一 router 與 companion 完整性
- Requirements: REQ-001, REQ-002, REQ-004, NFR-001, NFR-002
- Decision: 測試精確 Skill directory allowlist、folder/frontmatter name、companion relative links 與必要 precedence policy。
- Rationale: 單純把既有「只有一個 Skill」斷言放寬會允許日後無意加入第二 router 或不完整 copy。
- Consequences: 上游新增／移除 Skill 內部參考檔時，更新 work item 必須同步檢閱並調整期待值。

## DEC-005: 上游更新採新的 DevWeave feature
- Requirements: REQ-005, NFR-001
- Decision: 不提供自動更新；維護者使用 project-scope `npx skills update`，在獨立 work item 內檢閱 instruction diff、重跑驗證並完成 G3。
- Rationale: Skill instruction 會改變 agent 行為，應視為受治理的 executable policy change。
- Consequences: 更新不是即時的，但每個版本都有可追溯的人工作業關卡。

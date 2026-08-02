# 系統設計：整合 Wiki-first 探索與知識提升

<!-- DEVWEAVE:artifact=design version=1 work=20260802-200224-feature-wiki-first -->

## 設計摘要

在既有 `.agents/skills/devweave/` 內加入一個標準函式庫-only 的 `knowledge_core.py`，負責 Wiki bootstrap、frontmatter parse/update、source fingerprint、tree snapshot、health/lint 與 index/log contract。`devweave_core.py` 保持唯一 lifecycle orchestration source of truth，將 knowledge context 納入 G1 material、將 knowledge promotion 納入 G3 material，並由 `guard.py` 依 machine state 控制 verification-only 寫入。

核心不變量如下：

- 公開 chat surface 與單一 router 不變；`knowledge` 只是 engine machine namespace。
- `wiki/` 是 tracked、可讀、Obsidian-compatible 的細緻知識；`.devweave/baseline/` 仍是 G3 接受的治理真相。
- Wiki-first 是讀取順序；source behavior 與核准中的 DevWeave artifacts 才是衝突時的裁決依據。
- G1/G2 不修改 Wiki；只有 current G2 下的 verification/acceptance 可以 plan、edit、seal 或 delete。
- Product source、living baseline、knowledge tree 使用獨立 fingerprint domain；一種 material 的變更只讓正確的 gate/evidence stale。
- 新 work state 使用完整 knowledge contract；缺少 `base_knowledge` 的舊 active state 視為 legacy，不追溯新增 gate blocker。

## 選項比較

### 選項 A：直接安裝第二個 `codebase-wiki` skill 與 hooks

優點是移植量最低。缺點是違反 repository 單一 skill contract，兩個 PreToolUse guard 的授權模型互斥，也會讓使用者面對兩套 lifecycle。拒絕。

### 選項 B：把所有知識壓入 `.devweave/baseline/`

優點是 fingerprint 與 G3 已存在。缺點是 baseline 適合精煉治理真相，不適合大量模組、實體、依賴與 wikilink；也破壞 Codebase Wiki 的可讀性與 Obsidian 相容性。拒絕。

### 選項 C：root `wiki/` 作獨立 knowledge domain，由單一 DevWeave router 協調

優點是保留 Wiki-first 體驗與細緻知識模型，同時可用 G1/G3、state 與單一 guard 管理授權；代價是需要新增 knowledge snapshot、CLI 與相容層。採用。

### 選項 D：自動在每次探索或 source edit 後立即更新 Wiki

優點是內容較即時。缺點是未核准推論會進入長期知識，source verification 期間反覆使內容 stale，且會擴張 hook 權限。拒絕；改採 G3 promotion。

## 介面與資料流

### 模組邊界

- `knowledge_core.py`：不 import `devweave_core`，只使用 Python 標準函式庫。公開純函式與窄幅 mutation primitives，並以 `KnowledgeError` 回報 domain diagnostics。
- `devweave_core.py`：包裝 knowledge errors 為既有 `ValidationError/ExecutionError`，持有 project/work locks，更新 state/events，整合 gate validation 與 fingerprints。
- `devweave.py`：加入 `knowledge` subparser；stdout/exit code 繼續沿用單一 JSON envelope。
- `guard.py`：只讀 project/state 決定 edit boundary，不自行修改 knowledge state。
- `assets/wiki/`：保存 starter 與 page templates；不在 framework repository 建立實際 root Wiki。

### Project 與 work state

`project.json` 新增 additive default：

```json
{
  "knowledge": {
    "enabled": true,
    "root": "wiki"
  }
}
```

Root 固定驗證為 repo-relative `wiki`，不得為絕對路徑、`.`、`.devweave` 或 repository 外路徑。既有 project 缺少此 block 時，`load_project()` 在記憶體套用預設；只有顯式 `init` 或下一次 `start` 才原子寫回，避免 read-only `status` 產生 mutation。

新 work state 增加：

```json
{
  "base_knowledge": {
    "fingerprint": "sha256",
    "files": {"wiki/page.md": "sha256"},
    "pages": {
      "wiki/page.md": {
        "type": "module",
        "status": "active",
        "sources": ["src/module/"],
        "source_fingerprint": "sha256:..."
      }
    },
    "log_body_length": 0,
    "log_body_prefix_sha256": "sha256"
  },
  "knowledge_context": {
    "pages": [],
    "gaps": [],
    "recorded_at": null
  },
  "knowledge_updates": {
    "upserts": [],
    "deletes": [],
    "coupled": [],
    "rationale": "",
    "sealed": {},
    "recorded_at": null
  }
}
```

`base_knowledge.pages` 保存 work 開始時的 sources，避免 agent 先改 frontmatter 再逃避 affected-page 判定。缺少 `base_knowledge` 的 state 是 legacy：可載入、可顯示 warning、可完成既有 gate，但不套用新的 G1/G3 knowledge blocker。

### Wiki bootstrap 與 adoption

`init_project()` 與 `create_work()` 在 snapshot 前呼叫 idempotent bootstrap：

1. `wiki/` 不存在或為空時，由 assets 建立 `index.md`、`overview.md` placeholder、`log.md` 與 typed directories。
2. 已有 `index.md` 且 frontmatter `type: index` 時視為相容；只建立缺少的 directories/files，不改任何既有 Markdown。
3. 非空 Wiki 缺少可辨識 index，或既有同名 starter file schema 不相容時，回報 `knowledge_conflict` 並停止，不搬移、不覆寫。
4. Starter 使用 project locale，日期取 UTC calendar date；index/log/placeholder 使用 `source_fingerprint: none` 與 `verified_by: bootstrap`。

Typed directories 包含 `architecture/`、`modules/`、`entities/`、`patterns/`、`decisions/`、`dependencies/`、`guides/`、`synthesis/`。空目錄以 `.gitkeep` 保存。

### Page model 與 source fingerprint

所有 Markdown pages 需要 `title`、`type`、`sources`、`last_updated`、`tags`、`status`；新建或 seal 的頁面另需 `source_fingerprint` 與 `verified_by`。合法 status 為 `active/stale/placeholder`。既有頁缺少新增欄位時標示 `unsealed` warning；只要該頁被本 work 影響或修改，就必須 seal。

Fingerprint algorithm：

1. 正規化並排序 1–5 個 repo-relative sources；拒絕 absolute、`..`、`wiki/`、`.devweave/` 與不存在路徑。
2. 檔案以 normalized path、目前 bytes hash；symlink 以 link target hash。
3. 目錄以單次 Git listing 展開 tracked 與 non-ignored untracked regular files，依 normalized path 排序並串接各 content hash；ignored build artifacts 不參與。
4. Canonical JSON 後計算 SHA-256，表示為 `sha256:<64 hex>`；空 sources 固定為 `none`。
5. 以 chunked reads 控制大型檔案記憶體，且不經 shell 解譯。

### Machine CLI

- `knowledge status [--work ID]`：read-only；回傳 initialized/conflict、type/status counts、critical/warning、stale/unsealed/placeholder paths、work-specific affected/remaining/planned/sealed summary。輸出路徑清單有固定上限，不輸出 page bodies。
- `knowledge context --work ID --page PATH... [--gap TEXT...]`：只允許 requirements/scope_review。完整取代 context；必須包含 `wiki/index.md`，總頁數最多六個（index 加五個相關頁），command 會保存當下 page hash/status/freshness。任何非 fresh page 都必須至少有一項 gap。
- `knowledge plan --work ID [--upsert PATH...] [--delete PATH...] --rationale TEXT`：只允許 current G2 的 verification/acceptance_review。完整取代 plan；content targets 不得是 index/log，upsert/delete 不得重複。只要有 target，自動設定 `coupled` 為 `wiki/index.md` 與 `wiki/log.md`。
- `knowledge seal --work ID --page PATH...`：只允許 planned upserts；原子更新 `last_updated`、`source_fingerprint`、`verified_by`，保留 body 與未知 frontmatter fields，並把實際 fingerprint 記入 `knowledge_updates.sealed`。

沒有 affected pages、new-profile overview obligation 或實際 Wiki diff 時，不要求呼叫 `knowledge plan`，也不要求「無更新」rationale。

### Gate 與 fingerprint 資料流

G1：`instructions` 回傳 Wiki health 與 index pointer。Agent 讀 index、最多五頁與必要 raw sources，再執行 `knowledge context`。Scope fingerprint 包含 context ledger 的 immutable snapshot，不動態重讀頁面，因此日後 G3 promotion 不會倒打 G1。

G2：Wiki 維持唯讀；design/plan 正常核准。重大決策只在 G3 後選擇提升為 decision page。

Implementation：product source 依既有 tasks 修改。`wiki/` 加入 source fingerprint exclusion，故未授權或授權 Wiki diff 都不改變 source-bound evidence identity。

G3：

1. 以 `changed_paths_since(base_source)` 與 `base_knowledge.pages[*].sources` 的 exact/prefix overlap 計算 affected pages。
2. 比對 base/current knowledge tree；所有 Wiki diff 必須等於 planned upserts/deletes/coupled paths，planned target 也必須實際改變。
3. Affected page 必須是 sealed current active upsert，或 planned 且已不存在的 delete；`new` profile 額外要求 active/current `wiki/overview.md`。
4. Content change 必須有完整 index 與 log coupling。Log 只允許修改 frontmatter 並在既有 body 後追加；新增區塊恰有一個含 current work ID 的 `promote` heading。
5. Lint Critical 形成 validation error；Warning 加入 report。Acceptance fingerprint 包含 current knowledge tree、update ledger、baseline、evidence 與 source fingerprint。

G3 核准後再修改 Wiki，acceptance fingerprint mismatch 只使 G3 stale；不使 G1/G2 或 source evidence stale。

### Guard 與授權

維持 `.codex/hooks.json` 的單一 DevWeave PreToolUse hook。Edit tools 的路徑規則：

- G2 前：只允許目前 work artifacts，拒絕 `wiki/`。
- implementation：只允許 approved product scope，仍拒絕 `wiki/`。
- verification/acceptance_review：只允許 `knowledge_updates.upserts/deletes/coupled` 中的 Wiki 路徑；baseline 仍依原規則。
- Wiki root 外、path traversal、未宣告 target 或 legacy work 的 Wiki edit 均 fail closed。

DevWeave CLI 仍是受信任的 machine mutation surface；arbitrary shell 在 hook/sandbox 外的間接寫入無法被保證阻擋，因此 README 與 AGENTS 保留「hook 不是 OS sandbox」聲明，G3 tree/plan validation 作為第二道偵測。

### Skill 與文件載入

`SKILL.md` 只增加必要的 G1/G3 engine protocol 與 trigger 描述，維持低 token router。詳細 page/state/CLI contract 放入 `contracts.md`；requirements/verification phase reference 只保留該階段必做步驟。Wiki templates 放 assets，不把長模板複製到 SKILL。`agents/openai.yaml` 重新產生與 SKILL 一致的 display text，公開 prompt 仍只提 `$devweave`。

## 失敗模式與回復

- Bootstrap conflict：回報既有 paths 與原因，不寫任何 starter；使用者先搬移或修復後重試。
- Frontmatter parse/schema error：status/lint 列為 Critical；seal 不修改頁面或 state。
- Source 缺失、逃逸或 recursive knowledge source：seal fail closed；G3 不接受 stale affected page。
- Partial seal/state failure：page 與 state 都以 temporary file + replace；若 state commit 失敗，下一次 status 會把 undeclared/unsealed diff 報為 blocker，可重新 plan/seal。
- Index/log 遺漏或 log rewrite：G3 阻擋並指出 exact path；不自動重建以免覆蓋 user-authored notes。
- Knowledge warning：不中止 G3，但 acceptance 必須揭露；Critical 不可 waiver 成泛用通行證。
- 舊 project/state：缺欄位時套用 legacy read path；不自動改 active state。下一個 `start` 取得新 contract。
- Rollback：可回復 engine/skill code；additive JSON fields 會被舊 loader 忽略，root Wiki 保留為普通 tracked Markdown，不自動刪除使用者知識。

## 高風險分析

### Migration／遷移

保持 `schema_version: 1`，只加入 optional keys。顯式 `init` 或下一次 `start` 才持久化 project knowledge config 與 starter；既有 active work 不遷移 state、不新增 knowledge gate obligation。相容 legacy Wiki 漸進 seal，不做 bulk rewrite。

### Rollback／回復

新 state/project fields 對舊 code 是 unknown keys，現有 validators 不拒絕；回滾 code 後 work artifacts、baseline 與舊流程仍可讀。`wiki/` 不屬 machine ledger，回滾時保留，由使用者自行決定是否繼續追蹤。

### Security／安全

所有 target/source paths 經 resolve-within-repo、root boundary 與 traversal 檢查；source 不得引用 Wiki 或 `.devweave` 避免自我指紋與 machine-state disclosure。Guard 採 phase + planned exact path allowlist；engine commands 在 lock 內驗證 current gate。Hook 無法取代 OS sandbox，G3 diff reconciliation 捕捉外部 edits。

### Compatibility／相容性

公開 chat verbs、CLI JSON envelope、exit codes、artifact grammar、三道 gate、既有 commands 與 schema version 不變。新 CLI 是 additive。Windows/POSIX path 在進入 hash與比對前統一為 repo-relative POSIX。只有 Codex surface 變更，不新增 Copilot files。

### Performance／效能

一次 status/lint 共用 Git file listing，directory fingerprints 使用 sorted paths 與 streaming hash；health payload 只輸出 bounded summaries。Wiki 頁面預期只有 1–5 個核心 sources，避免全庫重複 hash。初版不建立 cache，優先確保正確性；若大型 repo profiling 顯示瓶頸，再以可再生 `.devweave/cache/` 加速，不改 tracked contract。

### 觀測與殘餘風險

State summary、instructions、validation diagnostics 與 append-only events 顯示 initialized/conflict、health counts、affected/remaining、planned/sealed targets。殘餘風險是語意矛盾仍需 Agent/人類判斷、目錄 source 過大可能變慢、外部編輯器可繞過 hook；以 gap、bounded source selection、G3 lint/tree reconciliation 與人類 G3 核准緩解。

## 設計決策

## DEC-001: 維持單一 DevWeave router

- Requirements: REQ-012, NFR-001
- Decision: 將授權來源的 Wiki primitives 改造到既有 skill，以 `knowledge_core.py` 與 assets/references 分層，不建立第二個 skill 或 hook stack。
- Rationale: 保持 repository contract、使用者心智模型與 progressive disclosure。
- Consequences: 需自行整合 lifecycle，但只有一份授權與狀態真相。

## DEC-002: 將 root Wiki 建模為獨立 living-knowledge domain

- Requirements: REQ-001, REQ-005, REQ-011
- Decision: 目標 repo 使用 root `wiki/`；baseline 與 knowledge 各自 snapshot、各自驗證。
- Rationale: 同時保留細緻導航與 G3 治理邊界。
- Consequences: G3 需協調兩種 tracked living truth，但不互相污染。

## DEC-003: 以目前內容而非日期判定 source freshness

- Requirements: REQ-005, REQ-006, NFR-001
- Decision: Page seal 保存 canonical SHA-256；directory 展開 Git tracked/non-ignored files。
- Rationale: 日期與 commit time 會誤判 dirty、rename 或同日修改，內容指紋可重現。
- Consequences: Status 需讀取 source bytes；以 bounded sources、single listing 與 streaming 降低成本。

## DEC-004: 以 machine context/plan/seal 管理 G1 與 G3

- Requirements: REQ-002, REQ-003, REQ-004, REQ-008
- Decision: 新增四個 machine-only knowledge operations；context 在 G1，plan/seal 僅在 verification/acceptance。
- Rationale: 可追溯使用過的知識與精確寫入授權，同時不增加公開命令。
- Consequences: Agent 多幾個 deterministic steps；錯誤可由 JSON diagnostics 修復。

## DEC-005: 分離 product、baseline 與 knowledge fingerprints

- Requirements: REQ-009
- Decision: `wiki/` 不進 product source snapshot；current Wiki tree與 update ledger只進 G3 acceptance fingerprint。
- Rationale: Wiki promotion 不應讓已在同一 source 上通過的測試失效。
- Consequences: 需獨立 diff reconciliation；G3 後 Wiki edit 仍會正確使 acceptance stale。

## DEC-006: Guard 使用 phase 與 exact planned paths

- Requirements: REQ-010, NFR-002
- Decision: verification 前拒絕 Wiki edit，之後只允許 upsert/delete/coupled allowlist。
- Rationale: 避免 Wiki 模式覆蓋原本 G2 product authorization，維持最小權限。
- Consequences: 必須先 plan 才能 edit；外部工具繞過 hook 仍由 G3 偵測。

## DEC-007: Critical 阻擋、Warning 揭露、log append-only

- Requirements: REQ-003, REQ-004, REQ-007
- Decision: 結構、來源、link、index、plan與 log 完整性為 Critical；orphan、legacy unsealed與 semantic review 為 Warning，除非頁面被本 work 影響。
- Rationale: 保持知識可信又不讓無關歷史問題阻斷每個 work item。
- Consequences: Acceptance 必須列出 warning；受影響頁面的門檻更嚴格。

## DEC-008: Schema v1 採 additive opt-in migration

- Requirements: REQ-011, NFR-002, NFR-003
- Decision: Loader 接受缺欄位；init/start 才補 project/starter；舊 active state 不回填 `base_knowledge`。
- Rationale: 避免 read-only command mutation與追溯 gate 變更。
- Consequences: Legacy active work 只有 health visibility，完整 contract 從下一個 work 開始。

## DEC-009: 將詳細規格下沉至 contracts 與 deterministic assets

- Requirements: REQ-012, NFR-003
- Decision: SKILL 保持 router 級摘要，phase references 保存階段動作，contracts 保存 schema/CLI，templates 保存 page shape，openai metadata 同步更新。
- Rationale: 符合 skill-creator 的 concise/progressive-disclosure 原則。
- Consequences: 實作與測試必須驗證 references、assets、metadata 沒有漂移。

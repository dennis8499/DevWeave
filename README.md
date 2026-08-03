# DevWeave

DevWeave 是一套以 repository 為中心、由 Codex 操作的語言中立 SDLC workflow。它把需求探索、
系統設計、任務、驗證證據與三道人工作業 gate 放在同一個可追溯的 work item 中，讓每次變更
都有清楚的範圍、決策、驗證結果與驗收紀錄。

內建的 Codebase LLM Wiki 是可重建、source-bound 的知識快取：探索先從固定索引與最多五個內容頁開始，只有遇到知識缺口才回查最小原始碼範圍。

本專案的詳細操作請閱讀 [繁體中文使用手冊](docs/使用手冊.md)。

## DevWeave 解決什麼問題

一般的 AI coding session 容易在「開始修改」前缺少範圍、設計、測試與人工確認。DevWeave 以
單一 `$devweave` router 將工作固定在以下流程：

```text
需求探索與 Wiki-first context
          │
          ▼
G1 範圍核准：brief、requirements、risk、scope
          │
          ▼
G2 開發核准：design、plan、immutable tasks
          │
          ▼
實作、逐項任務驗證與 evidence
          │
          ▼
G3 功能驗收：acceptance、回歸測試、scope、Wiki／baseline
          │
          ▼
        Closed
```

只要已核准的 artifact、source、evidence 或知識內容發生變化，engine 會透過 fingerprint
標記受影響的 gate 或 evidence 過期，要求回到最早需要重新確認的階段。

## 前置需求

- Git repository。
- Python 3.11 或更新版本。
- Codex CLI 或 VS Code Codex Extension。
- 在 Codex 中信任 repository 的 `.codex/hooks.json` hook。
- UTF-8 環境；runtime 不需要第三方 Python package。

DevWeave 不是 pip package，也沒有另一套安裝型 router。它由 repository 內的 skill、CLI、
hook、project state、Wiki 與 baseline 一起運作。

## 快速開始

### 1. 確認 repository 狀態

在 repository root 執行：

```powershell
python -B .agents\skills\devweave\scripts\devweave.py --repo . doctor
```

`doctor` 會檢查 Python、Git、`.devweave/project.json`、DevWeave skill、Codex hook、驗證
命令與 Wiki compatibility。

### 2. 初始化未管理的 repository

如果 repository 尚未有 `.devweave/project.json`，可以明確執行：

```powershell
python -B .agents\skills\devweave\scripts\devweave.py --repo . init
```

`init` 會非破壞性建立 `.devweave/`、三份 baseline、work-item 目錄與 root `wiki/` starter。
既有相容 Wiki 會被採用，不會覆寫使用者內容；不相容內容會回報 `knowledge_conflict`。

在未初始化 repository 中，Codex 不會自行隱式啟動 DevWeave。請在對話中明確使用：

```text
$devweave new 建立第一個可驗證的交付切片
$devweave feature 新增一項功能
$devweave refactor 重構指定模組並維持行為
$devweave bug 描述可重現的錯誤
$devweave wiki bootstrap
```

### 3. 使用 Codex 完成一個 work item

常用的公開對話命令如下：

```text
$devweave feature 新增 CSV 匯出能力
$devweave status
$devweave next
$devweave approve <work-id>
$devweave wiki bootstrap
```

`next` 會依目前 phase 提供下一步；`approve` 只應在對應的人工作業完成後使用。若有多個
active work item，請先使用 `$devweave status` 找到 work ID，再明確指定它。

### 4. 直接使用 machine CLI

DevWeave CLI 永遠輸出 UTF-8 JSON，適合 Codex 與其他自動化工具：

```powershell
python -B .agents\skills\devweave\scripts\devweave.py --repo . status --all
python -B .agents\skills\devweave\scripts\devweave.py --repo . project
python -B .agents\skills\devweave\scripts\devweave.py --repo . instructions --work <work-id>
```

公開 chat surface 與 machine CLI 的完整差異、參數及範例，請見 [使用手冊](docs/使用手冊.md)。

## 三道人工 gate

### G1：Scope／需求核准

G1 確認問題、使用者、成功條件、非目標、risk、scope 與 feature profile discovery。新 work
item 還必須完成 Wiki-first context：先讀 `wiki/index.md`，再讀最多五個相關頁面；只有
placeholder、stale、缺漏或矛盾被記錄為 gap 後，才回溯 raw source。

G1 artifacts：

- `brief.md`
- `requirements.md`
- risk 與 scope machine state
- feature／refactor／bug 對應的 discovery evidence
- `knowledge_context`

### G2：Design／開發核准

G2 確認設計選擇、介面、資料流、失敗模式、回復方式與 immutable task plan。G2 通過前，Codex
不能修改 scope 內的產品文件或程式；只能修改該 work item 的 Markdown artifacts。

G2 artifacts：

- `design.md`
- `plan.md`
- `DEC-*` 與 `TASK-*` traceability
- 高風險工作所需的額外分析

### G3：Verification／Acceptance 核准

G3 會檢查完整 diff、所有 required verification commands、current source-bound evidence、
AC/TASK 覆蓋、scope、baseline 與 current Knowledge Review。不同 work kind 的 evidence 要求不同：

| Work kind | G3 必要 evidence |
| --- | --- |
| `new` | acceptance，以及架構 baseline 更新 |
| `feature` | acceptance + regression |
| `refactor` | equivalence + regression |
| `bug` | regression；G1 前需有 failing reproduction 或窄幅 waiver |
| `high` risk | 上述 evidence + current independent review |

G3 通過且取得人工核准後，才能關閉 work item。

## 核心安全規則

- DevWeave 是唯一 SDLC router；companion Skills 不擁有 lifecycle、artifact、evidence 或 gate。
- Managed repository 的寫入必須有 active work item 與 session binding。
- G2 未核准前不能修改產品文件、程式、測試或其他 scope 外內容。
- G2 核准後，寫入仍限於 approved scope；移動檔案也會檢查目的地。
- Wiki 在 G2 與 implementation 期間唯讀；verification 只允許已規劃頁面與 coupled
  `wiki/index.md`／`wiki/log.md`。
- 不可直接編輯 `state.json`、`events.jsonl`、evidence summaries 或 `project.json`；使用
  Python engine CLI 更新 machine state。
- Hook 是 Codex guardrail，不是作業系統 sandbox。外部 editor 或停用 hook 的修改，會在 G3
  完整 diff reconciliation 時被檢查。
- DevWeave 不會自行建立 branch、worktree、commit、push、PR 或 deployment。

## Wiki-first 與知識生命週期

每個新 work item 在 G1 以 `wiki/index.md` 作為第一個讀取入口。Wiki page 使用 frontmatter、
repo-relative sources、current source SHA-256 fingerprint 與 `verified_by` provenance。

首次建立核心 Wiki 可使用：

```text
$devweave wiki bootstrap
```

命令會先判斷 active、sourced 的 overview、architecture 與 module 是否已齊全；完整時不建立 work item，否則建立或續接一般 `feature` bootstrap work item，沿用 G1/G2/G3。Bootstrap 探索整個 repository，不接受子路徑 scope，也不修改產品程式碼。

G2 與 implementation 期間 Wiki 唯讀；在 verification：

1. 執行 `knowledge status --work <work-id>` 找出 affected pages。
2. 每個新式 work item 都做 Knowledge Review：`promote` 或 `no-update`，並留下 rationale。
3. `promote` 以一個 plan 宣告 1–5 個內容頁；新頁可由九種 canonical template scaffold，完成編輯後改為 active。
4. `no-update` 只適用於非 bootstrap、沒有 affected page、沒有 Wiki diff 的情況，而且不建立 plan。
5. 更新宣告頁面與自動 coupled 的 `wiki/index.md`、`wiki/log.md`，再以 `knowledge seal` 封存。
6. G3 檢查 append-only promotion log、source fingerprint、coverage、review currentness、index 與 lint；placeholder 或未替換 token 不能 seal。

「每個 Work Item 更新 Wiki」指每次都做 Knowledge Review，不代表每次強迫產生 Wiki diff。原始碼與核准 artifacts 仍是最終事實來源；本功能不使用向量資料庫、全文索引或精確 Token 計量。

## Repository 結構

```text
.agents/skills/devweave/       DevWeave router、engine、references、templates
.agents/skills/<companion>/    project-local engineering methods
.codex/hooks.json              Codex PreToolUse guard
.devweave/project.json         locale、verification commands、knowledge policy
.devweave/work-items/<id>/     artifacts、state、events、evidence
.devweave/baseline/            accepted product、architecture、quality truth
.devweave/cache/               session bindings 與 raw verification logs（gitignored）
wiki/                          source-bound codebase knowledge、index、promotion log
tests/                         Python unittest 與 repository contract tests
fixtures/devweave/             new、feature、refactor、bug fixture scenarios
AGENTS.md                      repository precedence 與 side-effect policy
skills-lock.json               companion skill provenance 與 hashes
README.md                      專案入口
docs/使用手冊.md                詳細繁體中文操作手冊
```

## Companion Skills

本 repository 的 project-local companions 是：

- `grill-me`／`grilling`：G1 requirements interview。
- `codebase-design`：G2 module、interface、seam 與 adapter 設計。
- `diagnosing-bugs`：bug discovery 與可重現 feedback loop。
- `tdd`：G2 後 implementation 的 red → green slice。

它們不能建立第二套 work-item lifecycle，也不能直接操作 machine ledger、Git 或 remote tracker。
更新 companion Skills 必須建立新的 DevWeave feature work item，檢閱 upstream diff 與
`skills-lock.json`，再完成 repository verification。

## 驗證與測試

完整測試只使用 Python standard library：

```powershell
python -B -m unittest discover -s tests -v
```

其他常用檢查：

```powershell
python -B .agents\skills\devweave\scripts\devweave.py --repo . doctor
python -B .agents\skills\devweave\scripts\devweave.py --repo . project
python -B .agents\skills\devweave\scripts\devweave.py --repo . command list
git diff --check
```

維護者若需要驗證 skill package，可使用 skill-creator 提供的 `quick_validate.py`；安裝或
更新 companion Skills 才需要 Node.js／npx 與 network，DevWeave runtime 不依賴它們。

## 延伸閱讀

- [完整使用手冊](docs/使用手冊.md)
- [Repository policy](AGENTS.md)
- [DevWeave contracts](.agents/skills/devweave/references/contracts.md)
- [Requirements phase](.agents/skills/devweave/references/requirements-phase.md)
- [Design phase](.agents/skills/devweave/references/design-phase.md)
- [Implementation phase](.agents/skills/devweave/references/implementation-phase.md)
- [Verification phase](.agents/skills/devweave/references/verification-phase.md)
- [Companion skill provenance](skills-lock.json)

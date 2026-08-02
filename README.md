# DevWeave

DevWeave 是一套 repo 內建、AI-driven、語言中立的 SDLC workflow。它讓 Codex CLI 與 VS Code Codex Extension 共用同一組工作項、需求、設計、任務、驗證證據與三道人工作業關卡，不依賴 OpenSpec CLI、schema 或 artifact 格式。

## 核心流程

```text
new / feature / refactor / bug
              │
              ▼
   Wiki-first 探索與 AC ── G1 範圍核准
              │
              ▼
       系統設計與計畫 ── G2 開發核准
              │
              ▼
       逐項實作、驗證與知識提升
              │
              ▼
         功能驗收報告 ── G3 驗收核准 ── Closed
```

上游 artifact、核准後計畫或驗證後程式碼發生變化時，引擎會依 fingerprint 將受影響的 gate 與 evidence 標成過期，回到最早需要重新確認的階段。

## 使用條件

- Git repository
- Python 3.11 以上
- Codex CLI 或 VS Code Codex Extension
- 第一次使用專案 hook 時，需在 Codex 中信任 repo 的 `.codex/hooks.json`

未初始化的 repo 不會隱式啟動 DevWeave。請先在 Chat 中明確呼叫：

```text
$devweave new <目標>
$devweave feature <需求>
$devweave refactor <目標與預期結果>
$devweave bug <症狀>
```

後續操作：

```text
$devweave next [work-id]
$devweave status [work-id]
$devweave revise [work-id] <決策變更>
$devweave approve [work-id]
```

Codex 會把這些對話命令路由到 `.agents/skills/devweave/scripts/devweave.py`。初始化後，產品程式、測試、schema、dependency、build 或 CI 相關修改必須先綁定 active work item，且實作前必須具備仍有效的 G2 核准。

## Companion engineering Skills

DevWeave 是唯一 SDLC router；repository 另以 project-local copies 提供五個階段內方法：

- `grill-me` 與 `grilling`：逐題釐清需求與決策。
- `codebase-design`：以 module、interface、seam 與 adapter 設計可測試邊界。
- `diagnosing-bugs`：建立可重現、可最小化的除錯 feedback loop。
- `tdd`：在已核准 task 上執行 red → minimal green 的垂直切片。

它們不擁有 work item、artifact、gate、Wiki、evidence 或 Git 操作。若 companion Skill 與 `AGENTS.md` 或目前的 DevWeave phase 衝突，一律以 DevWeave 為準。

### 安裝與確認

從 repository root 安裝精確 allowlist；不要使用 `--all`，也不要執行 `setup-matt-pocock-skills`：

```powershell
npx skills@latest add mattpocock/skills --agent codex --skill grill-me --skill grilling --skill codebase-design --skill diagnosing-bugs --skill tdd --copy --yes
npx skills@latest list -a codex
```

安裝結果與 upstream hashes 記錄在 `skills-lock.json`。安裝後請開啟新的 Codex session，讓 project skills 重新被掃描。

### 階段對應

| DevWeave 階段 | Companion Skill | 寫入與產出邊界 |
| --- | --- | --- |
| G1 requirements | `$grill-me` / `grilling` | Wiki-first 探索後逐題釐清；結論只寫入 `brief.md` 與 `requirements.md`。 |
| Bug discovery | `diagnosing-bugs` | G2 前使用既有 command 或 cache/temp harness；tracked regression test 留到 G2 後。 |
| G2 design | `codebase-design` | interface 與 test seam 決策寫入 `design.md`，immutable tasks 寫入 `plan.md`。 |
| Implementation | `tdd` | 僅在 current G2 後，對單一 TASK 進行 red/green slice 並記錄 AC/TASK evidence。 |
| Verification | DevWeave | 執行完整驗證、清理 instrumentation、更新 baseline／Wiki、產生 acceptance，最後等待 G3。 |

範例：

```text
$devweave feature 新增 CSV 匯出；G1 使用 $grill-me 釐清需求
$devweave next <work-id>；G2 使用 $codebase-design 定義 interface 與 test seams
$devweave next <work-id>；對目前 TASK 使用 $tdd
$devweave bug 偶發重複扣款；使用 $diagnosing-bugs 建立可重現 feedback loop
```

Companion Skill 若發現 approved requirement、design、scope 或 task 必須改變，應執行 `$devweave revise` 回到最早受影響階段；不得直接偏離核准內容。它也不得自行建立 issue、branch、worktree、commit、push、PR、部署、`CONTEXT.md`、ADR 或第二份 spec。

### 更新與回復

禁止自動更新。上游版本變更必須建立新的 DevWeave feature work item，再執行 project-scope update、檢閱 instruction 與 lock diff、重跑 G3 驗證：

```powershell
npx skills@latest update codebase-design diagnosing-bugs grill-me grilling tdd --project
```

需要回復時，由明確授權的 Git workflow 回復 companion directories、`skills-lock.json`、policy、文件與 tests；DevWeave 不會自行 commit 或 reset。

## Wiki-first 知識生命週期

`init` 或下一次 `start` 會在目標 repo 根目錄非破壞性建立 `wiki/` 骨架。既有相容 Wiki 會被採用，任何同名內容都不會被覆寫；不相容內容由 `doctor` 回報 `knowledge_conflict`。DevWeave framework repository 本身不必為了提供此能力建立 root Wiki。

G1 固定先讀 `wiki/index.md`，再讀最多五個相關頁面。只有頁面缺失、placeholder、stale 或與現況矛盾時才回溯 raw source，並把查閱頁面與 gap 記入 work state。G2 與 implementation 期間 Wiki 唯讀；新的設計決策先留在 `design.md`。

進入 verification 後，引擎會依本 work item 的 product source diff 與 work 起始時各頁 `sources` 判斷真正受影響頁面。這些頁面必須刷新並 seal，或明確刪除；若沒有受影響頁面且 Wiki 無變更，不要求「無更新」理由。任何知識提升都要同步 index、在 append-only log 加入包含 work ID 的單一 `promote` entry，並通過 frontmatter、source fingerprint、wikilink、孤島、index 與 log lint。`new` 類型另須將 overview 提升為有來源的 active page。

Wiki-first 只決定讀取順序，不改變事實優先權：目前 source behavior 與已核准 DevWeave artifacts 優先，矛盾會留下 gap。`.devweave/baseline/` 保存 accepted governance truth；`wiki/` 保存較細的模組、實體、依賴、模式、決策、guide 與 synthesis。

## 內部 CLI

CLI 永遠輸出 UTF-8 JSON，適合 Codex 與其他自動化讀取：

```powershell
python .agents/skills/devweave/scripts/devweave.py --repo . init
python .agents/skills/devweave/scripts/devweave.py --repo . start --kind feature --title "新增查詢能力" --rationale "標準風險"
python .agents/skills/devweave/scripts/devweave.py --repo . status --all
python .agents/skills/devweave/scripts/devweave.py --repo . instructions --work <work-id>
python .agents/skills/devweave/scripts/devweave.py --repo . validate --work <work-id> --gate scope
python .agents/skills/devweave/scripts/devweave.py --repo . knowledge status --work <work-id>
```

設定多個 scope 路徑時要在同一次呼叫重複 `--path`；每次 `scope` 呼叫都會取代完整集合：

```powershell
python .agents/skills/devweave/scripts/devweave.py --repo . scope `
  --work <work-id> --path src --path tests --rationale "產品程式與測試"
```

語言中立的驗證命令以 argv array 儲存，不經 shell 解譯：

```powershell
python .agents/skills/devweave/scripts/devweave.py --repo . command set `
  --id full-tests --cwd . --timeout 900 `
  --required-for standard high -- project-test-command --all
```

初始化時 Codex 應從 README、manifest、CI 與既有 scripts 提議實際的 build、test、lint 或 typecheck 命令。缺少必要命令時 G3 會被阻擋，除非留下範圍明確且有核准人的 waiver。

## Repository contract

```text
.agents/skills/devweave/       standalone router、references、templates、engine
.agents/skills/<companion>/    五個 project-local、非 router 的工程方法
.codex/hooks.json              Codex PreToolUse guard
AGENTS.md                      repo activation 與治理規則
.devweave/project.json         專案設定與語言中立驗證命令
.devweave/work-items/<id>/     state、events、artifacts、evidence summaries
.devweave/baseline/            accepted product、architecture、quality、capabilities
.devweave/cache/               session bindings 與 raw logs（gitignored）
wiki/                           source-bound 詳細知識、索引與 append-only promotion log
```

Router-only knowledge CLI 提供 `status`、G1 的 `context`，以及 verification 的 `plan`／`seal`。`context` 與 `plan` 都是完整取代；`plan` 會自動授權 index/log coupling。公開 chat verbs 維持 `new/feature/refactor/bug/next/status/revise/approve`，沒有第二套 router、orchestrator、agent、runtime installer、RAG 或資料庫；companion Skills 不擁有 lifecycle 或 machine state。

DevWeave 只觀察 branch、HEAD 與 diff，不會自行建立 branch、worktree、commit、push、PR 或部署。Hook 是 Codex guardrail，不是作業系統 sandbox；停用 hook 或使用外部編輯器時，它無法阻止修改。

`bind` 由 PreToolUse hook 取得真正的 Codex session ID。若 CLI 顯示 `status: awaiting_hook`，且 Codex 沒有回傳已綁定的 additional context，就只能視為「已提出綁定請求」，不可宣稱 guard 已生效；請先確認 repo hook 已信任且未被停用。

詳細 machine contract 請見 [contracts.md](.agents/skills/devweave/references/contracts.md)。

## 驗證框架

全部測試只使用 Python 標準函式庫：

```powershell
python -B -m unittest discover -s tests -v
python C:\path\to\skill-creator\scripts\quick_validate.py .agents\skills\devweave
```

`fixtures/devweave/` 提供 `new`、`feature`、`refactor`、`bug` 四種端到端情境；測試也涵蓋 bootstrap/adoption/conflict、source 與 knowledge fingerprints、affected-page promotion、append-only log、非法 transition、核准失效、timeout、log 截斷、多工作項歧義與 guard allow/deny。

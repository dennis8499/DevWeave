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

- 技術門檻是 VS Code 1.90+、Python 3.11+、Git 與 Codex；這些是安裝／執行條件，不代表所有組合都已完成本次認證。
- Git repository。
- Python 3.11 或更新版本。
- Codex CLI 或 VS Code Codex Extension。
- 在 Codex 中信任 repository 的 `.codex/hooks.json` hook。
- UTF-8 環境；runtime 不需要第三方 Python package。

DevWeave 不是 pip package，也沒有另一套安裝型 router。它由 repository 內的 skill、CLI、
hook、project state、Wiki 與 baseline 一起運作。

## Windows 公開版 0.2.3

本次提供 0.2.3 VSIX，交付檔為 `vscode-extension/devweave-control-center-0.2.3.vsix`，並保留既有 0.2.2 與 0.2.1 artifact。VSIX 可在 VS Code 的 Extensions 視窗使用「Install from VSIX…」安裝；安裝後開啟 DevWeave repository，即可從 Activity Bar 進入 Control Center。完整流程請看[繁體中文使用手冊](docs/使用手冊.md)與 [Control Center README](vscode-extension/README.md)。

本次認證環境是 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host；本次實際基準為 Python full suite 111 項（1 項因 symlink 權限 skipped）與 Extension unit tests 88 項。VS Code 1.90+ 與 Python 3.11+ 只是技術門檻，不是本次已認證組合的宣告。這個 release 不包含 Marketplace 上架，也不對 macOS/Linux 做支援承諾。

發布流程先建立同目錄唯一 candidate，再以 provenance verifier 驗證，成功後才以 atomic rename promotion current VSIX；verify、promotion 或 cleanup 失敗都保留 current 與 retained artifact bytes，candidate 只做 best-effort cleanup。若發生發布事故，立即停止散布並停用或解除安裝 0.2.3；這些操作不會自動刪除 `.devweave`、Wiki 或 workspace 資料。應保留 workspace snapshot 與 logs，以新版本修復，並保留已發布的 0.2.2 與 0.2.1 artifact。

Control Center 的公開操作都遵循「預覽 → 你確認複製 → Codex Chat 審閱並送出 → Refresh」；Refresh、切換 work 或 workspace snapshot 更新後，舊 prompt 必須重新預覽。若 mutation prompt 顯示 Plan Mode handoff，請先切換 Plan Mode，再貼到 Codex Chat；Extension 仍可複製 prompt，但不會嘗試切換 host mode。`devweave.copyNextAction` 仍保留，但現在會開啟 Control Center；多個 active work 時必須先明確選取 work。

## 快速開始

### 1. 確認 repository 狀態

在 repository root 執行以下單行命令；這一行可直接用於 CMD、Windows PowerShell 5.1、PowerShell 7，以及 VS Code terminal：

`py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . doctor`

`doctor` 會檢查 Python、Git、`.devweave/project.json`、DevWeave skill、Codex hook、驗證命令與 Wiki compatibility；在 Windows 也會檢查 `py -3`、`cmd.exe`、Windows PowerShell 5.1、PowerShell 7、hook schema 與 root／nested launcher probe。若是 launcher failure，先修復 PATH、Python launcher、Git 或缺少的 shell；若 launcher 成功但工具被拒絕，則是 DevWeave gate、scope 或 Wiki policy deny。

`.codex/hooks.json` 的 `PreToolUse` 只匹配 `^(Bash|apply_patch|Edit|Write)$`，並同時提供 POSIX `command` 與 Windows `commandWindows`。Windows handler 使用 `powershell.exe -NoLogo -NoProfile -NonInteractive`，先以不依賴 shell variable 的 .NET UTF-8 console input/output 設定保護中文路徑，再呼叫 `py -3 -X utf8 -B` 從 Git root 定位 `guard.py`；hook 是 Codex guardrail，不是 OS sandbox，也不保證 hosted、global 或 plugin-owned tool path。

### 2. 初始化未管理的 repository

如果 repository 尚未有 `.devweave/project.json`，可以明確執行：

```powershell
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . init
```

`init` 會非破壞性建立 `.devweave/`、三份 baseline、work-item 目錄與 root `wiki/` starter。
既有相容 Wiki 會被採用，不會覆寫使用者內容；不相容內容會回報 `knowledge_conflict`。

初始化順序是：先以 read-only preflight 檢查 Wiki，再取得 project lock 並重新檢查，接著補齊 Wiki 缺檔，最後才建立 project、baseline、cache 與 work-item control state。因此 `wiki/` 只有自訂 `notes.md` 時會保留內容並補齊 starter；若 reserved `index.md`、`overview.md`、`log.md` 或 starter directory 的型別／frontmatter 不相容，會在任何本次控制檔寫入前停止，不會留下半套 `.devweave/`。

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
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . status --all
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . project
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . instructions --work <work-id>
```

公開 chat surface 與 machine CLI 的完整差異、參數及範例，請見 [使用手冊](docs/使用手冊.md)。

#### 依變更範圍執行驗證

驗證命令可在 `.devweave/project.json` 宣告 `affected_paths`、`writes`、`outputs`、`release_only` 與 `depends_on`。針對已知變更可只選取相關命令：

```powershell
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . verify --work <work-id> --profile standard --path vscode-extension/src --kind regression
```

選擇結果會回報 `selected`、`skipped` 與 dependency closure；沒有 metadata 的 legacy command 只在明確的完整 profile 中保留。`high` profile 即使指定 `--path` 仍執行完整集合，release-only package/smoke 不會被 low/standard 的依賴閉包偷偷帶回來。

每個 verification evidence 都可帶 bounded `metrics`：duration、context pages/bytes/chars、tool counts、selection/cache 與 usage。engine 目前限制 metrics canonical payload 為 250,000 bytes、數值欄位為非負且最多 10,000,000；Codex host 未提供 exact token/cost 時，CLI 會保存 `usage.status=unavailable` 與 null 欄位，不以 context bytes 推算 Token，也不保存 prompt 或 secret。

#### Verification Policy v2：命令與證據可信度

`.devweave/project.json` 的 `command_policy_version: 2` 由
`.agents/skills/devweave/scripts/command_policy.py` 統一評估。Guard、`verify`、Doctor、
command mutation 與 G3 不得各自重建命令規則。Configured command 只能經過
`devweave verify` 執行：固定 argv/cwd、`shell=False`、bounded timeout、trusted
executable、repository snapshot 與 declared-output reconciliation；直接 Bash 即使
argv 相同也會被拒絕。

G2 會凍結 Work Item 的 `verification_plan`，保存 project policy digest、command
definition digests、required/selected set、dependency closure、skip/not-applicable
理由、stage、writes/outputs 與成功 exit policy。Profile runner 與 G3 只讀同一份 plan。
`command set|remove` 在 G2 後會由 Router 讓 plan、相關 evidence 與 downstream gates
deterministically stale。

Evidence 的 `gate_eligible` 由 engine 計算，不能由 caller 指定。只有 current、zero
exit、plan/command/source fingerprint 相符、受控 executor 執行且沒有 undeclared
write 的證據可供 G3 使用；`expect=nonzero`、`expect=any`、reproduction、diagnostic、
failed、timeout、execution error、stale 或 undeclared writes 永遠不能通過 G3。
有寫入行為的 command 依 stage serial 執行；只有 `writes=none` 可以平行。

Read-only Bash 採跨 POSIX/CMD/PowerShell 形狀一致的 argv allowlist；shell operator、
command substitution、redirection、output-producing flag 與 unknown flag 一律
fail closed。Release-only command 需明確傳入 `verify --release-context <stage>`。

## 三道人工 gate

### G1：Scope／需求核准

G1 確認問題、使用者、成功條件、非目標、risk、scope 與 feature profile discovery。新 work
item 還必須完成 Wiki-first context：先讀 `wiki/index.md`，再讀最多五個相關頁面；只有
placeholder、stale、缺漏或矛盾被記錄為 gap 後，才回溯 raw source。

G1 的逐題決策流程是：先由 Codex 查證 repository facts，再使用 `grill-me`／`grilling` 確認
會影響目標、範圍、風險、相容性或驗收的 material decisions。G1/G2/Gate 的正式入口是
Plan Mode；Codex host 暴露 `request_user_input` 時，題目使用兩至三個互斥選項、第一項標記
`(Recommended)`、選項說明與 host `Other` 自訂答案。每次只問一題，等待使用者回答後才回流
artifact；普通模式在 G2 前若看不到工具，先要求回到 Plan Mode，只有無法切換或明確選擇相容性時
才使用同格式的 structured numbered fallback。可由 repository 查出的 facts 不重複詢問。

所有會在 pre-G2 建立或修改 Work Item 的入口都有 initial Plan Mode preflight：`new`、`feature`、
`refactor`、`bug`、`$devweave wiki bootstrap`，以及回到 G1/G2 的 `revise`。Router 會在
`start`、`bind`、`revise` 或 bootstrap Work Item mutation 前確認 host 是否真的暴露
`request_user_input`；看不到時只提示「請切換 Plan Mode」並停止，不會建立新的 Work Item。只有
使用者明確選擇 compatibility，才會使用 shared contract 的 structured numbered fallback；Extension
不會偽造或切換 host mode。

G1 artifacts：

- `brief.md`
- `requirements.md`
- risk 與 scope machine state
- feature／refactor／bug 對應的 discovery evidence
- `knowledge_context`

### G2：Design／開發核准

G2 確認設計選擇、介面、資料流、失敗模式、回復方式與 immutable task plan。G2 通過前，Codex
不能修改 scope 內的產品文件或程式；只能修改該 work item 的 Markdown artifacts。

G2 使用 `codebase-design` 在 Plan Mode 逐題確認會影響 module、interface、seam、data flow、failure mode、
rollback、compatibility、observability 或 verification 的設計決策。G2 approval 前不會自行
補上未決選擇，也不會開始 implementation 或 TDD。

G2 核准後普通模式只執行 approved tasks；若實作或 Skill 發現新的 material decision，必須停止並
使用 `$devweave revise` 回到最早受影響 phase。`request_user_input` 是否出現在普通/Skill context
是 Codex host capability，repository policy 不會偽造或宣稱已支援。

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

High-risk G3 的 Independent Review 是既有 DevWeave router 在 final artifacts 穩定後固定啟動的 1 個 isolated、read-only reviewer；Python engine 只接收 machine-only `review record` 結果並保存 `kind: review` evidence。`passed` 正常通過，`unavailable`／advisory 只顯示 warning，critical security、data-loss、不可回復性或 scope finding 會阻擋 G3，除非有針對具名 finding ID 的窄幅 `review-critical` waiver。G2 的 `Design It Twice` 仍是條件式 3+ sub-agents 的設計比較，兩者不是同一功能。

G3 通過且取得人工核准後，才能關閉 work item；人類 approval 仍是最後關卡。Reviewer 不得修改 source、Wiki、ledger 或執行 approve/revise/close，Extension 只投影 readiness，不會自行啟動 Agent。

每道 Gate 都是 validation 後的 Double Check：摘要已回答的 decisions、assumptions、scope、
驗收與 residual risk，等待明確的人類 approval。沉默、模糊同意或 agent 自己的判斷不算核准；
若 Gate 發現新需求或設計決策，必須使用 `revise` 回到最早受影響階段。

## 核心安全規則

- DevWeave 是唯一 SDLC router；companion Skills 不擁有 lifecycle、artifact、evidence 或 gate。
- High-risk G3 的 reviewer 由唯一既有 router 啟動；不新增第二套 lifecycle、router 或 orchestrator。G2 alternative-design agents 與 G3 independent reviewer 分開管理。
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

- `grill-me`／`grilling`：G1 material requirements interview；Plan Mode 使用 `request_user_input`，否則依 shared contract structured fallback，一次一題並等待使用者回答。
- `codebase-design`：G2 Plan Mode 的 module、interface、seam 與 adapter 設計，一次一題確認 material trade-off。
- `diagnosing-bugs`：bug discovery 與可重現 feedback loop。
- `tdd`：G2 後 implementation 的 red → green slice。

它們不能建立第二套 work-item lifecycle，也不能直接操作 machine ledger、Git 或 remote tracker。
更新 companion Skills 必須建立新的 DevWeave feature work item，檢閱 upstream diff 與
`skills-lock.json`，再完成 repository verification。

## 驗證與測試

完整測試只使用 Python standard library：

```powershell
py -3 -X utf8 -B -m unittest discover -s tests -v
```

其他常用檢查：

```powershell
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . doctor
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . project
py -3 -X utf8 -B .agents\skills\devweave\scripts\devweave.py --repo . command list
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

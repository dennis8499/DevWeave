# 系統設計：建立 Plan-first 原生問答流程

<!-- DEVWEAVE:artifact=design version=1 work=20260805-094544-feature-plan-first -->

## 設計摘要

選定「共用 native-question policy/reference + Plan-first router guidance」方案。Module 是 DevWeave phase router；Interface 是目前 phase/gate、host tool visibility、structured question、user answer 與 Gate action 的完整聊天協定。Seam 放在 router 的互動決策規則，而不是 Python engine 或 VS Code Extension。

這個 Interface 隱藏三件事：原生工具是否由 host 暴露、原生問題如何正規化、host 不可用時如何產生等價 fallback。既有 `brief.md`、`requirements.md`、`design.md`、`plan.md` 與 CLI gate state 是唯一 durable output；不建立 question state、ledger、第二 router 或 Extension dialog。

關鍵不變量：

- G1/G2 未取得 current approval 前，不修改 product source 或 tracked tests。
- G1/G2/Gate 需要使用者選擇時，Plan Mode 是目前正式入口；工具可見時使用 canonical `request_user_input`，每次只問一題。
- 普通模式 pre-G2 若需要 material decision，先要求回到 Plan Mode；無法切換或 host/tool 不可用時，才使用明確標示的 structured fallback。
- G2 後普通模式只能執行 approved task；新 material decision 透過 `revise` 回到最早受影響 phase。
- Native answer 不直接改變 Gate；只有通過既有 validation 並轉成合法 `approve`/`revise` action 才能呼叫 CLI。

## 選項比較

### Option A：共用 policy/reference seam（選定）

在 `AGENTS.md`、DevWeave router/phase references 與 project-local Skills 建立同一份 native-question contract，新增一份 repository-local reference 作為共用規格。Router 依 host tool visibility 選擇 native path、Plan-first return 或 structured fallback；answers 回流既有 artifacts。

- 優點：符合現有 single-router、artifact、Gate 與 G2 write boundary；不需要自然語言 question persistence；Plan Mode 可立即落地，普通 host capability 之後可接入同一 seam。
- 代價：host ordinary-mode tool exposure 仍是外部 prerequisite；實際 UI round-trip 必須用 host/manual evidence 驗證，不能由 Python engine 完全強制。

### Option B：Python engine pending-question state

把 pending question、answer、mode 與等待狀態加入 engine state/CLI。

- 不採用：新增 schema、migration、ledger、session binding 與第二套 lifecycle；不能讓 Codex Chat 顯示真正的 native UI，也違反 NFR-002 的 no-new-state 邊界。

### Option C：VS Code Extension 或 Skill 自有 question adapter

讓 Extension 或每個 Skill 自己呼叫 Codex API、維護 dialog 或注入工具。

- 不採用：Extension 明確是唯讀 projection/prompt handoff，Skills 不是 lifecycle owner；會產生多個 shallow adapters、造成 UI/answer/Gate 分歧，且無法解決 Codex host 普通模式未暴露工具的根因。

### Routing choice：Plan-first with explicit fallback

不採用「普通模式一律嘗試並默默 fallback」作為預設，因為使用者會誤以為已取得原生 dialog。選定 pre-G2 先要求回到 Plan Mode；當 host 無法切換或使用者明確選擇相容路徑時，才以同一份問題資料渲染 structured fallback。G2 後才開放普通模式進入 approved implementation loop。

## 介面與資料流

### Host seam

Canonical host interface 使用現有 `request_user_input` tool；repository 不建立 fake API 或 `requestUserInput` alias。Router 傳送的概念資料為：

```text
QuestionRequest {
  questions: [
    {
      header: string,       // host 的短標題
      id: string,           // 目前 decision/answer identity
      question: string,
      options: [
        { label: string, description: string },
        { label: string, description: string }
      ]
    }
  ]
}
```

Invariant 是 `questions` 長度為一；options 長度為二或三；第一個 label 必須包含 `(Recommended)`；`Other` 由 host 提供；每個選項包含 trade-off/description。Host result 先由 router 正規化成 `QuestionAnswer { id, selectedOption|customText, status }`，取消、逾時、空值或 malformed result 不可被當成答案。

### Router decision flow

1. Router 讀取 current work phase、gate、approved artifacts 與 pending task，先解決可由 Wiki/source 查出的 facts。
2. 若沒有 material user decision，繼續既有 phase work，不顯示 question dialog。
3. 若需要 decision 且 native tool visible，使用 Plan Mode native path；future ordinary/Skill host exposure 也使用同一 request/result contract。
4. 若 pre-G2 在 ordinary mode 且 native tool 不可見，停止目前 decision，提示切換 Plan Mode；若切換不可用或使用者選擇 compatibility path，將同一 request 格式化為單題 numbered fallback。
5. 有效回答回流 G1 `brief.md`/`requirements.md` 或 G2 `design.md`/`plan.md`；不建立 question ledger。
6. G1/G2 validation 通過後，Gate native answer 只轉成 `approve`、`revise` 或 pending/stop intent；router 仍透過既有 CLI contract 執行。
7. G2 approved 後，普通模式依 task ledger 實作；新 decision 使相關 Gate/evidence stale，透過 `revise` 回到最早 phase。

### Adapters、depth 與 test surface

- `HostNativeQuestionAdapter`：host-provided seam；目前 Plan Mode 是已觀察 implementation，ordinary/Skill exposure 是 future host implementation。Repository 只驗證可見性與人工 round-trip，不假裝擁有 host implementation。
- `StructuredFallbackAdapter`：repository policy formatter，使用相同 QuestionRequest，輸出推薦順序、description、自訂答案入口與等待規則。
- `GateActionAdapter`：既有 router/CLI `approve`/`revise` interface，不新增 public command。

Router policy 是較深的 module：Skills 只需要遵守一個問題契約，複雜的 mode/capability/fallback/Gate ordering 集中在 router guidance；各 Skill 不重複實作自己的 UI 或 state。Contract tests 直接跨越這個 policy interface，host integration/manual tests 跨越 native adapter seam。

## 失敗模式與回復

- Native tool 不可見：pre-G2 顯示回到 Plan Mode 的明確 blocker；若允許 compatibility path，使用 structured fallback，不使用無界自由問句。
- Host tool 呼叫失敗、逾時或 malformed：不猜答案、不寫 artifact、不 approve；保留目前 phase，提示 fallback 或重新提問。
- 使用者取消或輸入 ambiguous answer：保持 Gate/decision pending；需要時只重新提出同一題窄化問題。
- Native answer 與已核准 requirement/design 衝突：使用 `revise`，使受影響 Gate/evidence stale，重新走 G1/G2。
- 普通模式在 G2 前嘗試 implementation：停止 mutation；G2 不 current 時不開始 tracked product/test change。
- 既有 non-native host：保留 deterministic fallback，既有 CLI/artifacts/state schema 不變。
- Rollback：移除新增 policy/reference/docs/test contract diff 即可；不需 state conversion、migration 或 Extension rollback。

觀測透過 contract test logs、host/manual evidence、artifact fingerprints、Gate events 與 G3 diff reconciliation；不記錄完整對話、不新增 production instrumentation 或 secrets logging。

## 高風險分析

本 work 為 standard，不涉及資料 migration、runtime security boundary、product API、資料刪除或 production performance。Migration 不適用；rollback 是可逆的 policy/document/test diff；相容性由 fallback、既有 CLI/state/Gate 與 Extension handoff 保證。若未來 host integration 需要修改 Codex host，必須另有 host-side release/compatibility approval，不得由本 repo scope 推定完成。

## 設計決策

## DEC-001: 以 router policy/reference 作為 native question seam

- Requirements: REQ-001, REQ-002, REQ-006, NFR-001
- Decision: 將 canonical `request_user_input` contract、Plan-first routing、fallback 與 answer normalization 定義在共用 repository reference、DevWeave router 與 phase guidance；不新增 engine question state、CLI 或 Extension UI。
- Rationale: native UI 是 host capability，聊天層 policy 是本 repository 可控制且可測的 seam；既有 artifacts/Gate contract 已足以保存 durable decisions。
- Consequences: 多個 Skills 共用同一規則並提高 locality；普通模式 native support 需要外部 host evidence，不能由 engine 單獨保證。

## DEC-002: G1/G2/Gate 採 Plan-first，G2 後才進 ordinary implementation

- Requirements: REQ-001, REQ-003, REQ-004, REQ-005
- Decision: pre-G2 material decision 優先要求 Plan Mode；普通模式在工具不可見時不得默默自由提問，切換不可用才允許 structured fallback；current G2 後普通模式執行 approved task。
- Rationale: 目前 host 只可靠暴露 Plan Mode；把模式邊界明確化可避免使用者誤認 native UI 已使用，同時保留舊 host 相容性。
- Consequences: 使用者可能需要切換對話模式；fallback 仍可完成工作，但不宣稱原生問答；新 decision 需 `revise`。

## DEC-003: 所有 project-local Skills 使用一份共用 contract

- Requirements: REQ-002, REQ-006, NFR-003
- Decision: 新增 `native-question-contract.md` 作為 local reference，並由 `devweave`、五個 companion Skills、root policy、README/使用手冊與 contract tests 引用；不讓每個 Skill 自訂 request/result/state。
- Rationale: 一個 deep shared interface 取代六份近似但可能漂移的文字規則；保留既有 companion allowlist 與 upstream provenance。
- Consequences: local Skill 文件需要同步更新；外部 plugin Skills 只能透過 host-level policy/capability contract 相容，不能由本 repo 修改其 cache。

## DEC-004: Native Gate answer 仍經既有 CLI adapter

- Requirements: REQ-005, NFR-002
- Decision: native answer 只產生合法 Gate intent；validation、`approve`、`revise`、fingerprint 與 human approval semantics 維持既有 engine contract。
- Rationale: UI 變更不能改變 approval safety 或產生第二套 Gate lifecycle。
- Consequences: 原生工具回答與 machine state 之間有明確 adapter；取消/ambiguous 結果保持 pending。

## DEC-005: Host ordinary-mode exposure 是外部 prerequisite

- Requirements: REQ-003, NFR-001, NFR-003
- Decision: repository 以 tool registry visibility 判斷 capability；目前只宣稱 Plan Mode native evidence，普通/Skill native support 需 host integration/manual evidence，否則使用 Plan-first/fallback。
- Rationale: repo 無法註冊 Codex host tool，也不應以 policy text 冒充 runtime capability。
- Consequences: rollout 分為 repository policy 與 host capability 兩階段；未支援 host 仍可用 fallback。

# 工作摘要：建立 Plan-first 原生問答流程

<!-- DEVWEAVE:artifact=brief version=1 work=20260805-094544-feature-plan-first kind=feature -->

## 問題與目標

目前 DevWeave 的互動問答契約只要求「host 提供時優先使用原生 question facility」，沒有明確定義 Plan Mode 是 G1/G2 的入口，也沒有規範普通 Skill 對話在未完成 G2 時如何停止、回到 Plan Mode 或明確降級。現有 repository 搜尋不到 `request_user_input`/`requestUserInput` adapter；原生工具由 Codex host 注入，不能由 Skill 或 VS Code Extension 自行註冊。

目標是把 Plan Mode 定為目前可保證的 G1/G2/Gate 問答入口：工具可見時一次只呼叫一題 `request_user_input`，回答完成後才回流 artifact 或執行既有 Gate 命令；G2 核准後普通模式只執行已批准任務；實作期間發現新的 material requirement/design decision 時停止並回到 Plan Mode。未支援的 host 保留明確、等價的 structured fallback，且不新增 question state、CLI、ledger 或 Extension 問答 UI。

## 現況證據

### Wiki facts

- `wiki/index.md`、`wiki/overview.md` 與 `wiki/architecture/devweave-knowledge-workflow.md` 已記錄 single router、G1/G2 one-question、native-first/fallback、既有 artifact 回流與 Gate Double Check。
- `wiki/modules/knowledge-engine.md` 記錄 Python engine 沒有 pending-question state、CLI 或第二套 ledger；`wiki/modules/vscode-extension.md` 記錄 Extension 只做 filesystem projection 與 prompt handoff，不呼叫 Codex API。

### Source-backed facts

- `.agents/skills/devweave/SKILL.md` 目前使用「Prefer」native question facility；host 不可用時允許 structured numbered fallback，尚未定義 Plan-first 或普通模式 pre-G2 stop/return contract。
- G1/G2 phase references 與五個 companion Skills 將問答視為聊天層 policy；`tests/test_repository_contract.py` 目前驗證文字契約，而非實際 host tool round-trip。
- `vscode-extension/src/prompt.ts` 與 Extension README 的行為是產生/複製 prompt 交回 Codex Chat；它沒有 host question adapter。
- 本次 session 的 host tool schema 暴露 `request_user_input`，且限於 Plan Mode；repository exact API scan 沒有找到同名 implementation。

### Inferences

- 只把 Skill wording 改成「強制使用」不能使普通模式取得未被 host 注入的工具；Plan-first 必須是 router 的操作規則，普通模式原生問答則是外部 host capability。
- 目前安全且可驗證的 fallback 是：pre-G2 普通模式先要求切換 Plan Mode；切換不可用時才以標示清楚的 structured fallback 繼續，不能自由問句、猜答案或推進 Gate。

### Unresolved gaps

- Codex host 何時或以何種版本把 `request_user_input` 暴露到普通/Skill context 不由本 repository 控制；需以 host integration/manual evidence 驗證，不能在 repo 內宣稱已完成。

## 範圍

本工作修改 repository policy、DevWeave router/phase references、project-local companion Skill guidance、README/使用手冊與 repository contract tests，明確定義：

- Plan Mode 是 G1/G2/Gate native question 的目前正式入口。
- canonical host seam 是 `request_user_input`；router 每次傳一題、兩至三個互斥選項、推薦選項置前、描述與 host `Other`。
- 所有 project-local Skills 共用相同問答規則；Skills 不建立第二 router、pending state 或 question ledger。
- G2 前普通模式若需要 material decision，先要求回到 Plan Mode；host/tool 不可用時使用等價 structured fallback。
- G2 後普通模式只執行 approved task；新 material decision 必須 `revise`/回到最早 phase 並重新取得 Gate。
- G1/G2/G3 Gate 的原生回答仍由既有 `validate`、`approve`、`revise` 流程執行。

Codex host 本身的工具暴露列為外部 prerequisite/驗收項，不由本 repository 直接實作；VS Code Extension 維持 prompt handoff。

## 非目標

不新增或修改：

- Python engine pending-question state、CLI command、JSON/JSONL schema、ledger 或 session question persistence。
- Codex host、Codex CLI、VS Code Codex integration 或外部 plugin cache 的 runtime implementation。
- VS Code Extension 自有 question dialog、Codex API 呼叫、普通模式工具注入或另一套 UI。
- 讓未支援 host 在沒有 native tool 的情況下聲稱原生問答已完成。
- product runtime、branch/worktree、commit、push、PR、deployment 或 production instrumentation。
- Wiki 內容在 G3 verification 前的更新；新的 durable knowledge 只依 Knowledge Review promotion plan 處理。

## 風險

風險等級：standard

主要風險是 instruction wording 可能讓 agent 過度要求切換模式、或錯誤宣稱普通模式具有原生工具。以 capability-visible、Plan-first、明確 fallback、未回答不推進與 manual host evidence 限制風險。變更主要是政策/文件/contract test，既有 CLI、artifact、Gate、Wiki fingerprint 與 Extension handoff 保持相容；若 host 不支援普通模式，既有 fallback 仍可用。

驗證基線包含 root Python unit/contract suite、Extension typecheck/tests/package/smoke、`git diff --check`，以及實際 Plan Mode 的 native tool round-trip 和普通/Skill context 的 capability/manual evidence。現有 `vscode-extension/devweave-control-center-0.2.1.vsix` dirty change 不屬於本工作 scope，必須保留並在 G3 scope reconciliation 中排除。

## Profile 補充

本 feature 以聊天層 policy composition 為主要變更，Module 是 DevWeave phase router，Interface 是目前 phase、host tool visibility、structured question、user answer 與 Gate action 的協定；host-native adapter 與 fallback formatter 是外部/內部 seams。既有 artifacts 是唯一 durable answer output，G2 是開始 tracked implementation 的邊界。

# 系統設計：初始 Plan Mode 導流

<!-- DEVWEAVE:artifact=design version=1 work=20260805-184040-feature-plan-mode -->

## 設計摘要

選定「mutation seam 前的 Router preflight + Extension optional projection metadata」方案。Router 在任何可能建立或修改 pre-G2 Work Item 的路徑前，先依 shared native-question contract 判斷 `request_user_input` host capability；可見時才繼續既有 lifecycle，不可見時提示回到 Plan Mode 並停止。只有明確 compatibility 選擇才進入同一題序的 structured numbered fallback。

這個方案把未來 host mode 行為的責任留在 Codex host，把 lifecycle 與安全順序留在 DevWeave router，把使用者看得到的 handoff 留在 Control Center。Extension 只從 filesystem snapshot 與既有 prompt intent 推導 optional `PlanModeGuidance`，不宣稱能讀取或切換 host mode。

關鍵不變量：

- `new`、`feature`、`refactor`、`bug`、`wiki bootstrap` 及回到 G1/G2 的 `revise` 在 preflight 通過前不執行 `start`、`bind`、`revise` 或 bootstrap Work Item mutation。
- 初始未初始化 repository 的 `init` Wiki preflight/write exception 保留；進入 `start` 仍需先完成 Plan Mode preflight。
- native question 一次只送一題；取消、timeout、malformed 或 ambiguous result 不會寫 artifact、建立/修改 Work Item 或通過 Gate。
- `PlanModeGuidance` 是 `PromptBundle` 與 `SnapshotGuidance` 的 optional additive metadata；`chatText`、既有 Webview protocol envelope、PreviewGate 與 CLI 不變。
- Control Center 的 handoff 是提示，不是 checkbox、host command 或阻擋 copy 的第二個 approval；copy 仍沿用 current preview ticket。

## 選項比較

### 選項 A：讓 Python engine 或 Extension 偵測／切換 Plan Mode

這會在 engine、CLI 或 Extension 新增 host adapter、mode state 或 command，讓 repository 嘗試判斷 host 是否切換成功。它看似可以自動化 round-trip，但沒有可驗證的 host API 證據，會違反 host capability boundary，並引入不必要的 machine state、相容性與安全責任。淘汰。

### 選項 B：先建立 Work Item，再在 G1/G2 問題出現時提醒 Plan Mode

這保留現有 mutation 順序，改動小，但無法滿足「第一次 mutation 前導流」；普通模式仍會先留下 Work Item、binding 或 bootstrap state，且取消時難以安全回復。淘汰。

### 選項 C：Router mutation seam preflight，Extension 使用 optional metadata（選定）

Router 在 `start`／`bind`／`revise`／bootstrap 的最前面完成 capability gate；Extension 只在既有 `PromptBundle`／`SnapshotGuidance` 上增加 `PlanModeGuidance`，Webview 直接渲染 handoff，不新增訊息型別。這把複雜度集中在唯一 router 與純 presentation helper，具有較高 Depth、較佳 Locality，且維持既有 CLI、chatText、PreviewGate 與 copy 行為。取捨是 host 切換仍需使用者完成，無法由 repository 自動確認。

### UI 介面取捨：新增 host action 或專用 question state vs. 純 handoff block

新增 host action／question state 會把 Control Center 變成第二個問答 router，也會讓 stale、copy 與 Extension version contract 複雜化。選定純 handoff block：總覽、preview、copy result 都顯示同一個可讀訊息，仍保留原始 prompt 與 copy action；所有決策仍回到 Codex Chat 與既有 Router。

## 介面與資料流

### Router 與 native-question contract Module

Module：DevWeave router 的 Initial Plan Mode Preflight。Interface 是一個在 mutation 前使用的順序契約，而非新的 CLI 或 state：輸入公開 intent、repository 初始化狀態與可能的 target phase；輸出 `continue`、`stop-and-request-plan-mode` 或在使用者明確選擇 compatibility 後的 `structured-fallback`。

Seam 位於 work-item resolution／`knowledge bootstrap` assessment 可能造成 mutation 之前。Router 先判斷 host 是否真的暴露 canonical `request_user_input`；未暴露時不能呼叫 `start`、`bind`、`revise` 或建立 bootstrap Work Item。`wiki bootstrap` 的 `already_complete` read-only 判斷可以沿既有 command，但不得在 preflight 前進入可能 create/resume 的 engine path。

對 `revise`，Router 先辨識 requested target phase；只有回到 `requirements`／G1 或 `design`／G2 的 revise 需要初始 preflight。post-G2 approved implementation revise 仍受既有 approved-task／`revise` policy 管理，不被誤標成 initial blocker。G1/G2 `approve` 仍遵守既有 Gate 的 Plan-first native contract；Extension 可顯示相應 handoff，但不改變 Gate CLI。

Native path 使用 shared `QuestionRequest`：一次一題、二至三個互斥選項、第一項 `(Recommended)`、trade-off description 與 host `Other`。若 ordinary context 沒有 host tool，Router 先停止並要求切換 Plan Mode；只有 mode switch 不可用或使用者明確選擇 compatibility，才可渲染相同選項順序的 numbered fallback。兩條 path 都等待有效答案，並經既有 CLI validation 後才繼續。

### PlanModeGuidance Module

在 `vscode-extension/src/model.ts` 定義小型 Interface：

```text
PlanModeStage = initial | g1 | g2 | post-g2
PlanModeGuidance = { required: boolean; stage: PlanModeStage }
```

`PromptBundle.planModeGuidance?` 與 `SnapshotGuidance.planModeGuidance?` 都是 optional。`required` 只表示目前 handoff 是否為 pre-G2 必要下一步；`stage` 是顯示與測試用的 machine key，不代表 host 已切換成功。

phase mapping：無 active work 或新建／bootstrap intent 使用 `initial`；`requirements`、`scope_review` 使用 `g1`；`design`、`build_review` 使用 `g2`；`implementation`、`verification`、`acceptance_review` 使用 `post-g2`。`closed` 或 initialize/setup guidance 不強制附帶 Plan Mode metadata。

### PromptComposer Interface 與資料流

維持既有 `compose(intent, snapshot): PromptBundle` Interface。新增純 helper 依 command 與 snapshot work lookup 產生 metadata：

1. `new`／`feature`／`refactor`／`bug`／`wikiBootstrap` 回傳 `{ required: true, stage: "initial" }`。
2. `revise` 依 target work phase 回傳 `g1` 或 `g2` required；post-G2 revise 回傳 optional non-blocking `post-g2` metadata。
3. `approve` 若作用於 G1/G2 work 可回傳相應 required stage，讓 preview 明確提示既有 Gate 的 Plan Mode；read-only `next`／`status` 不新增 blocker metadata。
4. 先執行既有 warning、sanitization、mutationBlocked guard，再回傳原本完全相同的 `chatText`，只附加 optional metadata。

既有 `actionPreview`／`copyResult` envelope 會自然攜帶 optional bundle 欄位，不新增 protocol message 或 parser branch。`PreviewGate` 繼續以 panel、typed intent、revision 與 bundle 綁定 current preview；metadata 不改變 ticket consume/restore。

### Snapshot guidance 與 Webview Interface

`buildSnapshotGuidance(snapshot, selectedWork)` 依同一套 phase helper 產生 optional metadata。no-active managed workspace 的 `start` guidance 必須包含 `initial/required`；selected pre-G2 work 的 guidance 必須包含 `g1` 或 `g2/required`；post-G2 guidance 不顯示錯誤 blocker。

Webview 的 `renderGuidance`、`renderActionPreview` 與 `renderCopiedResult` 各渲染一個可辨識的 Plan Mode handoff block，文字固定表達「先切換 Plan Mode，再貼到 Codex Chat」。Preview 保留原始 prompt 與既有 warnings，copy result 保留 prompt 展開內容與 Refresh 指引；handoff 不禁用確認或 copy。沒有 Help 專用新增內容。

### Release／bootstrap Interface

`package.json` version 由 0.2.1 升至 0.2.2；`esbuild.mjs` 仍從 repository source 與 bootstrap asset 建立 manifest。更新 `vscode-extension/assets/bootstrap/AGENTS.md` 與被 bundle 的 DevWeave skill/native contract source，重新產生 `dist/bootstrap/manifest.json` 與 0.2.2 VSIX。0.2.1 VSIX 不覆寫或刪除，verifier 改檢查 current version、仍維持 58 bootstrap files／118 VSIX entries（若 source-derived bundle 結構變動則以實際 package contract 更新 evidence）。

## 失敗模式與回復

- Host capability 不可見：Router 回報切換 Plan Mode 的明確 handoff，停止在 mutation seam；workspace 不增加 Work Item、binding、revise 或 bootstrap ledger。使用者切換後重新提交即可沿既有 flow 繼續。
- Host 無法切換且使用者未明確選 compatibility：保持 pending，不能以沉默或一般同意推斷；不寫 G1/G2 artifact。
- compatibility fallback 的 cancel、timeout、malformed、empty 或 ambiguous result：回報未取得有效答案，停止且不通過 Gate；不新增 question state 或 ledger 欄位。
- Extension 無 metadata／舊 bundle consumer：optional 欄位缺失視為沒有額外 handoff，既有 chatText、warning、copy 與 protocol 仍可讀。
- Snapshot work phase 不明或 selected work stale：不猜 target；保留既有 snapshot/preview safety，必要時要求 Refresh 或以 status/next 重新取得 engine 權威結果。
- Preview stale 或 clipboard failure：沿用 `PreviewGate` 的 invalidate/restore；Plan Mode handoff 仍顯示，但不放寬 current revision 與 retry 限制。
- Package 或 smoke verifier 失敗：保留 0.2.1 artifact，不把 0.2.2 標成可交付；修復 source/build 後重新產生 current VSIX。無 repository runtime rollback 或自動發布。

Rollback 以版本與可逆 source diff 為界：移除 optional metadata/UI 變更即可回到 0.2.1 code path；不修改既有 workspace state、CLI schema 或 Wiki bytes。G3 前只以 accepted baseline/Knowledge Review 記錄最終 durable contract。

## 高風險分析

本 work item 為 standard risk，不涉及資料 migration、schema migration、不可回復操作、外部權限、secret handling 或 production performance path；high-risk reviewer 不適用。相容性仍以 additive optional TypeScript field、既有 protocol/chatText exact assertion、0.2.1 artifact 保留與 0.2.2 package verifier 驗證。安全性重點是 mutation boundary 與不偽造 host capability；效能只增加 snapshot/prompt 的常數級 phase lookup，不新增 IO、network、process 或 engine call。

## 設計決策

## DEC-001: 在唯一 Router 的 mutation seam 做 preflight

- Requirements: REQ-001, REQ-002, REQ-003, NFR-001
- Decision: 在 `start`、`bind`、pre-G2 `revise`、bootstrap Work Item mutation 前完成 host capability preflight；不可見時停止，只有明確 compatibility 才進 fallback。
- Rationale: 以單一順序契約保護所有初始入口，避免 Work Item mutation 先於 Plan Mode 導流；不需要 engine schema、CLI 或 state。
- Consequences: Router prompt 會在普通模式停止並等待使用者切換；host round-trip 仍是外部手動責任，不能由 repository 自動驗證。

## DEC-002: 使用最小 optional PlanModeGuidance

- Requirements: REQ-004, NFR-001, NFR-002
- Decision: 在 `PromptBundle` 與 `SnapshotGuidance` 各增加 optional `{ required, stage }` metadata，採 `initial/g1/g2/post-g2` stage keys。
- Rationale: 讓 UI 能按 command/phase 顯示導流而不改變既有 prompt/protocol；舊 consumer 可忽略新欄位。
- Consequences: phase mapping 必須由純 helper 與 tests 固定；metadata 不可被解讀為 host capability 已成功。

## DEC-003: Reuse existing preview/copy seam

- Requirements: REQ-005, NFR-002
- Decision: Webview 只在 overview、preview、copy result render handoff block，不新增 message、checkbox、host command、fake adapter 或 question state。
- Rationale: `PromptComposer` 與 `PreviewGate` 已經是 Extension 的 deep public seam；沿用它可維持 stale/multiple-work/copy safety 與良好 Locality。
- Consequences: 使用者仍須手動切換 Plan Mode 並送出 prompt；Extension 不能提供自動切換或確認回傳。

## DEC-004: Source-derived 0.2.2 package with 0.2.1 preservation

- Requirements: REQ-006, REQ-007, NFR-002
- Decision: 更新 policy、bootstrap asset、Wiki/baseline contract 與 package version，透過既有 esbuild/package verifier 產生 0.2.2 VSIX，保留 0.2.1。
- Rationale: release provenance 與 bootstrap source 必須同步；現有 verifier 已檢查 source hash、byte length、manifest 與 VSIX entries，能提供 deterministic evidence。
- Consequences: package/build verification 必須在文件/Wiki/baseline stabilization 後重新執行；0.2.1 仍是可回溯 artifact，不會被重建覆寫。

## DEC-005: 以明確 phase mapping 表達 pre-G2

- Requirements: REQ-004, REQ-005, NFR-002
- Decision: `requirements/scope_review` 映射 `g1`，`design/build_review` 映射 `g2`，post-G2 phases 映射 non-blocking `post-g2`；no-active/new mutation 映射 required `initial`。
- Rationale: phase 是 Extension 唯一可從 snapshot 觀察的 approved lifecycle signal；不新增 host state 或猜測 conversation mode。
- Consequences: stale/unknown phase 不得自動判定為已切換；測試需覆蓋 no-active、pre-G2、post-G2、multiple active 與 stale preview。

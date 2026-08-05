---
title: DevWeave Codebase Overview
type: overview
sources: [.agents/skills, AGENTS.md, README.md, docs/使用手冊.md, tests/test_repository_contract.py]
last_updated: 2026-08-05
tags: [overview]
status: active
source_fingerprint: "sha256:632edba0c9b7356506c1d6c4202366e96bed57efe0ec55db435f9f4d240c91ef"
verified_by: 20260805-184040-feature-plan-mode
---

# DevWeave Codebase Overview

DevWeave 是 repository-managed SDLC workflow。它以單一 `$devweave` router、可追溯 Work Item、G1/G2/G3 人工關卡、source-bound evidence、living baseline 與 Codebase Wiki 管理軟體變更。G1/G2 在 Gate 前採用互動式關鍵決策問答，讓需求與設計的未決事項先由使用者確認，再由 Gate 做一次可追溯的 Double Check。

## 核心流程

1. `new|feature|refactor|bug`、`wiki bootstrap` 與會回到 G1/G2 的 `revise` 先經 Router 的 Plan Mode preflight：只以 host 是否暴露 canonical `request_user_input` 作為 capability 證據；未暴露時先提示切換 Plan Mode 並在 `start`、`bind`、`revise` 或 bootstrap Work Item 建立前停止。只有使用者明確選擇 compatibility，才進入同一題序與結構的 numbered fallback。preflight 通過後才建立或續接一般 Work Item。
2. G1 先讀 `wiki/index.md`，再讀最多五個內容頁；只有先記錄 missing、placeholder、stale、矛盾或不足 gap，才回查最小必要 source。可由 repository 查出的事實由 router 自動整理，不重複問使用者。
3. G1 需求階段使用 `grill-me`/`grilling`，一次只問一個會影響目標、範圍、介面、風險、相容性或驗收的決策；Plan Mode 是目前正式入口，Codex host 可見時使用 canonical `request_user_input` 提供推薦在前的互斥選項、trade-off 與 `Other`，不可用時使用相同結構的 numbered fallback。回答回流 `brief.md`/`requirements.md`，完成 `validate` 後展示摘要並等待明確 G1 approval。
4. G2 使用 `codebase-design` 在 Plan Mode 逐題確認重要設計取捨，採用同一套 native-first/fallback 問答規則；回答回流 `design.md`/`plan.md`，完成 `validate` 後展示方案、介面、失敗處理、回復方式與 task plan，等待明確 G2 approval。G2 前的普通/Skill context 若看不到工具，必須先回到 Plan Mode；G2 後普通模式只執行 approved tasks，新的 material decision 必須用 `revise` 回到最早受影響 phase。Wiki 在 verification 前保持唯讀。
5. G3 驗證 current evidence、scope、baseline 與 Knowledge Review，確認實作符合已批准內容。新式 Work Item 必須選擇 `promote` 或 `no-update`；promote 最多變更五個內容頁並同步 index/log/seal。
6. High-risk Work Item 在 final artifacts 穩定後由唯一 DevWeave router 啟動一個 isolated、read-only Independent Review Agent。Python engine 只接收 machine-only `review record`，保存 source-bound `kind: review` evidence、redacted report hash 與 provenance；standard/low risk 不啟動此 reviewer。
7. 本次 0.2.2 Windows 公開版提供 `devweave-control-center-0.2.2.vsix`，並保留 `devweave-control-center-0.2.1.vsix`；認證環境限定為 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host，VS Code 1.90+／Python 3.11+ 僅為技術門檻。Control Center 的公開操作採 preview → 使用者確認複製 → Codex Chat handoff → Refresh；事故時停止散布並停用或解除安裝 0.2.2，保留 repository 資料與 0.2.1 artifact，以新版本修復，不提供舊版 binary rollback。

本次 release hardening 另固定幾個容易被使用者誤解的邊界：`devweave.wikiBootstrap` 與 legacy `devweave.copyNextAction` 都只開啟 Control Center 的 preview flow，host 的 `PreviewGate` 仍是最後 copy gate；多 active work 的 `next` 必須明確選取，未指定 work 的 `status` 明確交給 `$devweave status --all`；五個 section 的 tab/tabpanel 關聯在 inactive 狀態也保持有效 target，方向鍵/Home/End、focus restore 與 forced-colors contract 由 Extension-local seam 驗證。

Windows Codex hook 也有明確的兩層契約：`.codex/hooks.json` 的標準 `command` 使用 `powershell.exe -NoLogo -NoProfile -NonInteractive`，以 `python.exe -X utf8 -B` 和不含 shell variable 的 `(Join-Path (git rev-parse --show-toplevel) ...)` 從 Git root 執行 `guard.py`。同一 command 可由 Codex 的 `cmd.exe` 或 PowerShell 外層啟動；guard 直接以 UTF-8 bytes 讀寫 payload。launcher process failure 與 guard 回傳的 JSON `permissionDecision: deny` 不同，後者仍是正常 process exit 0 的 DevWeave policy result。Extension bootstrap 只產生來源一致的 hook；既有 workspace 的 exact hook 不會被 Extension 靜默覆寫。

## 互動式決策與 Gate

Router 只把有實質影響的決策交給使用者：先提供已查證的 context、建議選項、取捨與不作決定的後果，然後等待目前問題的回答，才進入下一題或改寫 artifact。沉默、模糊同意與 agent 自己的推斷都不能當作決策或 approval；低風險命名與檔案位置等細節才可列為假設自行處理。

原生 question facility 的題目包含兩至三個互斥選項，第一項標記 `(Recommended)`，並提供 host `Other` 自訂答案；host 不可用時，router 顯示相同的 structured numbered fallback。這只改變問答介面，不增加 question state、CLI、schema 或 ledger，Gate 仍由 explicit human approval 完成。

Plan Mode 是 G1/G2/Gate material decision 的目前可保證 native entry；canonical host tool 是 `request_user_input`，一次只送一題並等待 answer round-trip。普通模式與 Skill context 的 tool visibility 是外部 Codex host capability：未暴露時不可把 policy 當成支援，pre-G2 必須停止並回到 Plan Mode，只有無法切換或明確選擇 compatibility 才能使用 structured fallback。取消、逾時、malformed 或 ambiguous result 不能猜答案、寫 artifact 或推進 Gate。

Initial preflight 覆蓋 `new`、`feature`、`refactor`、`bug`、`wiki bootstrap` 與回到 G1/G2 的 `revise`；它位於任何 Work Item mutation 前，包含 start、bind、revise 與 bootstrap create。此順序只由 Router 契約保證，repository 不讀取或切換 host mode，也不以 fake adapter、question state 或 Extension UI 代替 host capability。

Companion Skills 是階段內的方法，不建立第二套 lifecycle：`grill-me`/`grilling` 負責 G1 問答，`codebase-design` 負責 G2 設計問答，`diagnosing-bugs` 與 `tdd` 仍受既有階段限制。Gate 是對已驗證 artifacts 的 Double Check；Gate 產生的新決策或使用者改變答案時，必須透過 `revise` 回到最早受影響階段。

## 架構

- Python engine 是 workflow 與 knowledge policy 的權威來源；JSON/JSONL ledger 只能經 CLI 更新。互動式問答規則位於 router、shared native-question contract 與 phase guidance，host seam 由 Codex 注入；不新增 pending-question engine、CLI、schema、fake adapter 或第二套 ledger。
- `knowledge_core.py` 負責 Wiki parser、source/content fingerprint、lint、coverage、reserved-starter preflight、bootstrap assessment、canonical scaffold 與 seal。`init` 先在 lock 外、再在 lock 內檢查 reserved paths，成功後才建立 `.devweave` control state。
- `devweave_core.py` 負責 Work Item state、gate currentness、review/plan invalidation、G3 reconciliation 與 evidence。
- High-risk G3 的 review result 分為 `passed`、`unavailable`、`critical`：unavailable/timeout/malformed fallback 與 advisory 是 warning，具名 critical security/data-loss/irreversible/scope finding 會阻擋 G3，只有 exact narrow `review-critical` waiver 可解除；human approval 仍是最後關卡。
- VS Code Extension 只讀 filesystem projection，三個 Wiki bootstrap 入口都只預覽/複製 `$devweave wiki bootstrap`，不執行 CLI、不寫 Wiki；Control Center 以總覽、工作項目、知識、驗證（含稽核）與說明五區呈現，顯示偏好只存於 Extension workspaceState。`PromptBundle` 與 `SnapshotGuidance` 可帶 optional `PlanModeGuidance`（`required`、`stage`），供總覽、mutation preview 與 copy result 顯示「先切換 Plan Mode，再貼到 Codex Chat」；`chatText` 維持既有 `$devweave ...` 內容，Extension 不嘗試切換 host mode。
- Extension 的 public command UI 以任務語言分組，所有 workflow decision 仍透過 prompt handoff 回到 Codex Chat；active work 與 closed history 分離，Wiki 頁面瀏覽提供有界搜尋、分類與顯示全部入口。`devweave.copyNextAction` 保留 command ID 但只開啟 Control Center；多 active work 的 `next` 必須明確選取，未指定 work 的 `status` 使用 `$devweave status --all` 查詢全部 active work。
- Extension 的 Wiki 搜尋以 Enter 套用大小寫不敏感的 title/path/body-preview 包含式查詢；輸入期間保留同一個 input DOM，結果與 metrics 真實 mount 到 `#wiki-results`。五個 tab/tabpanel 使用完整 ARIA 關聯、方向鍵/Home/End 與 focus restore；Watcher 由 debounce 與 single-flight refresh coordinator 合併，snapshot 的獨立讀取平行化後仍依固定順序輸出。
- Copy 成功後的 Webview `copyResult` 通知與 Extension-native success toast 不再共享 clipboard failure restore path；host 只在 clipboard adapter 失敗時恢復 ticket，walkthrough 的 bounded labels 則保留在 configured Extension/Python raw logs。
- 0.2.2 bootstrap bundle 的 version 從 package version 產生，提供完整控制面：六組核准 skills、通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter。Project、baseline 與三份 Wiki starter 以明確 semantic contract 採用合法 evolved bytes；AGENTS、skills、hook、lock 與其他 controls 維持 exact，初始化只建立缺少且無衝突的檔案，失敗或取消不留下 partial control bundle，說明手冊留在 Extension 內，不落地到 target repository。既有 0.2.1 artifact 仍保留。
- Windows 的 PreToolUse hook 使用上述標準 `command`，不依賴 Codex 不採用的 `commandWindows` 平行欄位；未綁定或未通過 G2 的寫入仍由 guard 以 deny JSON 表達，而不是把 policy deny 變成 hook process failure。這個邊界由 cmd/PowerShell、root/nested cwd、raw UTF-8、malformed input 與 read-only silence 的真實 child-process regression 覆蓋。

## 關鍵模組

- [[devweave-knowledge-workflow]]：Bootstrap、Query、Review、Promotion 的完整生命週期與真實來源優先序。
- [[knowledge-engine]]：knowledge machine commands、狀態投影、template scaffold、coverage 與 seal 邊界。
- [[vscode-extension]]：Control Center 的 Wiki 搜尋、refresh/snapshot、bootstrap repair、embedded help 與安全邊界。

## 真實來源與限制

- Current source behavior 與已核准 DevWeave artifacts 優先於 Wiki；衝突保留為 gap。
- Wiki 是可重建的 source-bound 知識快取，不是產品事實的最終權威。
- 探索上限是 index 加五個內容頁；系統不加入向量資料庫、全文索引或 Token 計量，也不宣稱精確節省數字。

## Skill governance overlay

本 Work Item 將 Skill instructions 視為可治理的 repository policy overlay。`devweave` 是唯一 router；`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling`、`tdd` 是唯一五個 companion allowlist，提供目前 phase 的方法並把結果回流既有 artifact/evidence。`.agents/skills/writing-great-skills` 是 maintenance-only：它不進 companion allowlist、不進 Extension bootstrap bundle，也不建立工作流程。

五個 companion 的 local optimization 保留 `skills-lock.json` 的 upstream source、skillPath 與 computed hash；local wording 是 overlay，不冒充 upstream release。Skill body 以 trigger branch、progressive disclosure、Wiki/phase precedence、停止條件與可檢查 completion criterion 組成；`grill-me` 維持 user-only invocation，`devweave` 維持 implicit invocation。這些修改沒有新增 CLI、JSON schema、router、state、ledger、branch、commit 或 PR 行為。

需要使用者選擇的五個 companion 都遵循同一份 `native-question-contract.md`：Plan Mode/native `request_user_input`、一題／二至三選項／推薦第一項／host `Other`、等待與 result safety；普通 pre-G2 context 不能自行建立第二套問答 UI，新的 implementation decision 必須 `revise`。

品質檢查包含 UTF-8 quick validation、repository contract 的 exact six-governed-Skill set、frontmatter/metadata/link/invocation policy、maintenance-only/bootstrap exclusion、隔離 forward-test，以及 Python/Extension full verification。Hook hardening 的 repository contract 現在包含 17 項測試；本 work item 的 Python final run 為 103 tests，另維持 77 項 Extension tests、58 個 bootstrap files 與 119 個 VSIX entries。validator 尚未支援的 `disable-model-invocation` 欄位由 repository contract 補驗，並保留 `grill-me` 的必要 policy。

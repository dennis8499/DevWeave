---
title: DevWeave Codebase Overview
type: overview
sources: [.agents/skills, AGENTS.md, skills-lock.json, tests/test_repository_contract.py, vscode-extension/esbuild.mjs]
last_updated: 2026-08-05
tags: [overview]
status: active
source_fingerprint: "sha256:73659abd2a990a8fa75a0352292e9b51b1cec70cd533d085dc437e830cb8c70e"
verified_by: 20260805-081842-feature-skills-writing-great-skills
---

# DevWeave Codebase Overview

DevWeave 是 repository-managed SDLC workflow。它以單一 `$devweave` router、可追溯 Work Item、G1/G2/G3 人工關卡、source-bound evidence、living baseline 與 Codebase Wiki 管理軟體變更。G1/G2 在 Gate 前採用互動式關鍵決策問答，讓需求與設計的未決事項先由使用者確認，再由 Gate 做一次可追溯的 Double Check。

## 核心流程

1. `new|feature|refactor|bug` 建立一般 Work Item；`wiki bootstrap` 建立或續接 `kind: feature`、`knowledge_profile: bootstrap` 的一般生命週期。
2. G1 先讀 `wiki/index.md`，再讀最多五個內容頁；只有先記錄 missing、placeholder、stale、矛盾或不足 gap，才回查最小必要 source。可由 repository 查出的事實由 router 自動整理，不重複問使用者。
3. G1 需求階段使用 `grill-me`/`grilling`，一次只問一個會影響目標、範圍、介面、風險、相容性或驗收的決策；Codex host 可用時使用原生 question facility 提供推薦在前的互斥選項、trade-off 與 `Other`，不可用時使用相同結構的 numbered fallback。回答回流 `brief.md`/`requirements.md`，完成 `validate` 後展示摘要並等待明確 G1 approval。
4. G2 使用 `codebase-design` 逐題確認重要設計取捨，採用同一套 native-first/fallback 問答規則；回答回流 `design.md`/`plan.md`，完成 `validate` 後展示方案、介面、失敗處理、回復方式與 task plan，等待明確 G2 approval。產品實作與 tracked tests 只在 current G2 後進行，Wiki 在 verification 前保持唯讀。
5. G3 驗證 current evidence、scope、baseline 與 Knowledge Review，確認實作符合已批准內容。新式 Work Item 必須選擇 `promote` 或 `no-update`；promote 最多變更五個內容頁並同步 index/log/seal。
6. High-risk Work Item 在 final artifacts 穩定後由唯一 DevWeave router 啟動一個 isolated、read-only Independent Review Agent。Python engine 只接收 machine-only `review record`，保存 source-bound `kind: review` evidence、redacted report hash 與 provenance；standard/low risk 不啟動此 reviewer。
7. 0.2.1 Windows 公開版交付 repository 與 VSIX，正式支援 Windows、VS Code 1.90+、Python 3.11+、Git 與 Codex；不包含 Marketplace 上架或 macOS/Linux 支援承諾。Control Center 的公開操作採 preview → 使用者確認複製 → Codex Chat handoff → Refresh，0.2.0 與 0.1.0 VSIX 保留作為回退。

本次 release hardening 另固定幾個容易被使用者誤解的邊界：`devweave.wikiBootstrap` 與 legacy `devweave.copyNextAction` 都只開啟 Control Center 的 preview flow，host 的 `PreviewGate` 仍是最後 copy gate；多 active work 的 `next` 必須明確選取，未指定 work 的 `status` 明確交給 `$devweave status --all`；五個 section 的 tab/tabpanel 關聯在 inactive 狀態也保持有效 target，方向鍵/Home/End、focus restore 與 forced-colors contract 由 Extension-local seam 驗證。

## 互動式決策與 Gate

Router 只把有實質影響的決策交給使用者：先提供已查證的 context、建議選項、取捨與不作決定的後果，然後等待目前問題的回答，才進入下一題或改寫 artifact。沉默、模糊同意與 agent 自己的推斷都不能當作決策或 approval；低風險命名與檔案位置等細節才可列為假設自行處理。

原生 question facility 的題目包含兩至三個互斥選項，第一項標記 `(Recommended)`，並提供 host `Other` 自訂答案；host 不可用時，router 顯示相同的 structured numbered fallback。這只改變問答介面，不增加 question state、CLI、schema 或 ledger，Gate 仍由 explicit human approval 完成。

Companion Skills 是階段內的方法，不建立第二套 lifecycle：`grill-me`/`grilling` 負責 G1 問答，`codebase-design` 負責 G2 設計問答，`diagnosing-bugs` 與 `tdd` 仍受既有階段限制。Gate 是對已驗證 artifacts 的 Double Check；Gate 產生的新決策或使用者改變答案時，必須透過 `revise` 回到最早受影響階段。

## 架構

- Python engine 是 workflow 與 knowledge policy 的權威來源；JSON/JSONL ledger 只能經 CLI 更新。互動式問答規則位於 router 與 phase guidance，並不新增 pending-question engine、CLI、schema 或第二套 ledger。
- `knowledge_core.py` 負責 Wiki parser、source/content fingerprint、lint、coverage、reserved-starter preflight、bootstrap assessment、canonical scaffold 與 seal。`init` 先在 lock 外、再在 lock 內檢查 reserved paths，成功後才建立 `.devweave` control state。
- `devweave_core.py` 負責 Work Item state、gate currentness、review/plan invalidation、G3 reconciliation 與 evidence。
- High-risk G3 的 review result 分為 `passed`、`unavailable`、`critical`：unavailable/timeout/malformed fallback 與 advisory 是 warning，具名 critical security/data-loss/irreversible/scope finding 會阻擋 G3，只有 exact narrow `review-critical` waiver 可解除；human approval 仍是最後關卡。
- VS Code Extension 只讀 filesystem projection，三個 Wiki bootstrap 入口都只預覽/複製 `$devweave wiki bootstrap`，不執行 CLI、不寫 Wiki；Control Center 以總覽、工作項目、知識、驗證（含稽核）與說明五區呈現，顯示偏好只存於 Extension workspaceState。
- Extension 的 public command UI 以任務語言分組，所有 workflow decision 仍透過 prompt handoff 回到 Codex Chat；active work 與 closed history 分離，Wiki 頁面瀏覽提供有界搜尋、分類與顯示全部入口。`devweave.copyNextAction` 保留 command ID 但只開啟 Control Center；多 active work 的 `next` 必須明確選取，未指定 work 的 `status` 使用 `$devweave status --all` 查詢全部 active work。
- Extension 的 Wiki 搜尋以 Enter 套用大小寫不敏感的 title/path/body-preview 包含式查詢；輸入期間保留同一個 input DOM，結果與 metrics 真實 mount 到 `#wiki-results`。五個 tab/tabpanel 使用完整 ARIA 關聯、方向鍵/Home/End 與 focus restore；Watcher 由 debounce 與 single-flight refresh coordinator 合併，snapshot 的獨立讀取平行化後仍依固定順序輸出。
- Copy 成功後的 Webview `copyResult` 通知與 Extension-native success toast 不再共享 clipboard failure restore path；host 只在 clipboard adapter 失敗時恢復 ticket，walkthrough 的 bounded labels 則保留在 configured Extension/Python raw logs。
- 0.2.1 bootstrap bundle 的 version 從 package version 產生，提供完整控制面：六組核准 skills、通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter。Project、baseline 與三份 Wiki starter 以明確 semantic contract 採用合法 evolved bytes；AGENTS、skills、hook、lock 與其他 controls 維持 exact，初始化只建立缺少且無衝突的檔案，失敗或取消不留下 partial control bundle，說明手冊留在 Extension 內，不落地到 target repository。

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

品質檢查包含 UTF-8 quick validation、repository contract 的 exact six-governed-Skill set、frontmatter/metadata/link/invocation policy、maintenance-only/bootstrap exclusion、隔離 forward-test，以及 Python/Extension full verification。validator 尚未支援的 `disable-model-invocation` 欄位由 repository contract 補驗，並保留 `grill-me` 的必要 policy。

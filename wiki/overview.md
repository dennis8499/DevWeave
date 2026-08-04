---
title: DevWeave Codebase Overview
type: overview
sources: [.agents/skills/devweave/SKILL.md, AGENTS.md, README.md, docs/使用手冊.md, vscode-extension/README.md]
last_updated: 2026-08-04
tags: [overview]
status: active
source_fingerprint: "sha256:cd34d3ceb382e6f4f3aaa56a53ec0bb162715e48eb1e554951e169abee73252b"
verified_by: 20260804-102428-feature-vs-code-extension-wiki
---

# DevWeave Codebase Overview

DevWeave 是 repository-managed SDLC workflow。它以單一 `$devweave` router、可追溯 Work Item、G1/G2/G3 人工關卡、source-bound evidence、living baseline 與 Codebase Wiki 管理軟體變更。G1/G2 在 Gate 前採用互動式關鍵決策問答，讓需求與設計的未決事項先由使用者確認，再由 Gate 做一次可追溯的 Double Check。

## 核心流程

1. `new|feature|refactor|bug` 建立一般 Work Item；`wiki bootstrap` 建立或續接 `kind: feature`、`knowledge_profile: bootstrap` 的一般生命週期。
2. G1 先讀 `wiki/index.md`，再讀最多五個內容頁；只有先記錄 missing、placeholder、stale、矛盾或不足 gap，才回查最小必要 source。可由 repository 查出的事實由 router 自動整理，不重複問使用者。
3. G1 需求階段使用 `grill-me`/`grilling`，一次只問一個會影響目標、範圍、介面、風險、相容性或驗收的決策；回答回流 `brief.md`/`requirements.md`，完成 `validate` 後展示摘要並等待明確 G1 approval。
4. G2 使用 `codebase-design` 逐題確認重要設計取捨；回答回流 `design.md`/`plan.md`，完成 `validate` 後展示方案、介面、失敗處理、回復方式與 task plan，等待明確 G2 approval。產品實作與 tracked tests 只在 current G2 後進行，Wiki 在 verification 前保持唯讀。
5. G3 驗證 current evidence、scope、baseline 與 Knowledge Review，確認實作符合已批准內容。新式 Work Item 必須選擇 `promote` 或 `no-update`；promote 最多變更五個內容頁並同步 index/log/seal。

## 互動式決策與 Gate

Router 只把有實質影響的決策交給使用者：先提供已查證的 context、建議選項、取捨與不作決定的後果，然後等待目前問題的回答，才進入下一題或改寫 artifact。沉默、模糊同意與 agent 自己的推斷都不能當作決策或 approval；低風險命名與檔案位置等細節才可列為假設自行處理。

Companion Skills 是階段內的方法，不建立第二套 lifecycle：`grill-me`/`grilling` 負責 G1 問答，`codebase-design` 負責 G2 設計問答，`diagnosing-bugs` 與 `tdd` 仍受既有階段限制。Gate 是對已驗證 artifacts 的 Double Check；Gate 產生的新決策或使用者改變答案時，必須透過 `revise` 回到最早受影響階段。

## 架構

- Python engine 是 workflow 與 knowledge policy 的權威來源；JSON/JSONL ledger 只能經 CLI 更新。互動式問答規則位於 router 與 phase guidance，並不新增 pending-question engine、CLI、schema 或第二套 ledger。
- `knowledge_core.py` 負責 Wiki parser、source/content fingerprint、lint、coverage、bootstrap assessment、canonical scaffold 與 seal。
- `devweave_core.py` 負責 Work Item state、gate currentness、review/plan invalidation、G3 reconciliation 與 evidence。
- VS Code Extension 只讀 filesystem projection，三個 Wiki bootstrap 入口都只預覽/複製 `$devweave wiki bootstrap`，不執行 CLI、不寫 Wiki；Control Center 以總覽、工作項目、知識、驗證、稽核與說明六區呈現，顯示偏好只存於 Extension workspaceState。
- Extension 的 public command UI 以任務語言分組，所有 workflow decision 仍透過 prompt handoff 回到 Codex Chat；active work 與 closed history 分離，Wiki 頁面瀏覽提供有界搜尋、分類與顯示全部入口。
- Extension 的 Wiki 搜尋以 Enter 套用大小寫不敏感的 title/path/body-preview 包含式查詢；輸入期間保留同一個 input DOM，結果區使用局部 render。Watcher 由 debounce 與 single-flight refresh coordinator 合併，snapshot 的獨立讀取平行化後仍依固定順序輸出。
- 0.2.0 bootstrap bundle 提供完整控制面：六組核准 skills、通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter；初始化只建立缺少且無衝突的檔案，說明手冊留在 Extension 內，不落地到 target repository。

## 關鍵模組

- [[devweave-knowledge-workflow]]：Bootstrap、Query、Review、Promotion 的完整生命週期與真實來源優先序。
- [[knowledge-engine]]：knowledge machine commands、狀態投影、template scaffold、coverage 與 seal 邊界。
- [[vscode-extension]]：Control Center 的 Wiki 搜尋、refresh/snapshot、bootstrap repair、embedded help 與安全邊界。

## 真實來源與限制

- Current source behavior 與已核准 DevWeave artifacts 優先於 Wiki；衝突保留為 gap。
- Wiki 是可重建的 source-bound 知識快取，不是產品事實的最終權威。
- 探索上限是 index 加五個內容頁；系統不加入向量資料庫、全文索引或 Token 計量，也不宣稱精確節省數字。

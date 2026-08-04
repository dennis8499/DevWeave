---
title: DevWeave Codebase Overview
type: overview
sources: [.agents/skills/devweave/SKILL.md, AGENTS.md, README.md, docs/使用手冊.md, vscode-extension/README.md]
last_updated: 2026-08-03
tags: [overview]
status: active
source_fingerprint: "sha256:58ab4cf4a9bc9e3582cf415565bbd10e80ca7f4e8181c3344fe96d5dcf85d349"
verified_by: 20260803-215202-feature-devweave-control-center-ux
---

# DevWeave Codebase Overview

DevWeave 是 repository-managed SDLC workflow。它以單一 `$devweave` router、可追溯 Work Item、G1/G2/G3 人工關卡、source-bound evidence、living baseline 與 Codebase Wiki 管理軟體變更。

## 核心流程

1. `new|feature|refactor|bug` 建立一般 Work Item；`wiki bootstrap` 建立或續接 `kind: feature`、`knowledge_profile: bootstrap` 的一般生命週期。
2. G1 先讀 `wiki/index.md`，再讀最多五個內容頁；只有先記錄 missing、placeholder、stale、矛盾或不足 gap，才回查最小必要 source。
3. G2 核准 requirements、design 與 immutable task definitions。產品實作只在 current G2 後進行，Wiki 在 verification 前保持唯讀。
4. G3 驗證 current evidence、scope、baseline 與 Knowledge Review。新式 Work Item 必須選擇 `promote` 或 `no-update`；promote 最多變更五個內容頁並同步 index/log/seal。

## 架構

- Python engine 是 workflow 與 knowledge policy 的權威來源；JSON/JSONL ledger 只能經 CLI 更新。
- `knowledge_core.py` 負責 Wiki parser、source/content fingerprint、lint、coverage、bootstrap assessment、canonical scaffold 與 seal。
- `devweave_core.py` 負責 Work Item state、gate currentness、review/plan invalidation、G3 reconciliation 與 evidence。
- VS Code Extension 只讀 filesystem projection，三個 Wiki bootstrap 入口都只預覽/複製 `$devweave wiki bootstrap`，不執行 CLI、不寫 Wiki；Control Center 以總覽、工作項目、知識、驗證與稽核四區呈現，顯示偏好只存於 Extension workspaceState。
- Extension 的 public command UI 以任務語言分組，所有 workflow decision 仍透過 prompt handoff 回到 Codex Chat；active work 與 closed history 分離，Wiki 頁面瀏覽提供有界搜尋、分類與顯示全部入口。

## 關鍵模組

- [[devweave-knowledge-workflow]]：Bootstrap、Query、Review、Promotion 的完整生命週期與真實來源優先序。
- [[knowledge-engine]]：knowledge machine commands、狀態投影、template scaffold、coverage 與 seal 邊界。

## 真實來源與限制

- Current source behavior 與已核准 DevWeave artifacts 優先於 Wiki；衝突保留為 gap。
- Wiki 是可重建的 source-bound 知識快取，不是產品事實的最終權威。
- 探索上限是 index 加五個內容頁；系統不加入向量資料庫、全文索引或 Token 計量，也不宣稱精確節省數字。

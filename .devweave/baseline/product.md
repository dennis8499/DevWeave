# Product Baseline

此文件保存已驗收的產品目標、使用者與能力。由 DevWeave 工作項在 G3 前更新。

## Vision

DevWeave 以單一 `$devweave` router，讓 Codex 在 repository 內以可追溯的探索、設計、實作、驗證與三道人工作業關卡交付軟體變更。

## Accepted Capabilities

- 公開 chat verbs 固定為 `new/feature/refactor/bug/next/status/revise/approve`。
- G1 採 Wiki-first：先讀 root `wiki/index.md`，再讀最多五個相關頁面，並把 pages/gaps 納入 G1 fingerprint。
- G3 可將驗證後的模組、實體、依賴、模式、決策、guide 與 synthesis 知識提升到 root `wiki/`；affected pages、index、append-only log 與 source provenance 由 engine 驗證。
- `.devweave/baseline/` 保存 accepted governance truth；`wiki/` 保存細緻且 source-bound 的 codebase knowledge。
- 不提供第二套 skill、Copilot surface、installer、agents、RAG 或資料庫。

## Roadmap

初版優先使用 deterministic、dependency-free 的檔案模型。大型 repository 若經 profiling 證實 source hashing 為瓶頸，可在不改 tracked contract 的前提下加入可再生 cache。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

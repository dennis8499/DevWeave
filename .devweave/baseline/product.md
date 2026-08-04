# Product Baseline

此文件保存已驗收的產品目標、使用者與能力。由 DevWeave 工作項在 G3 前更新。

## Vision

DevWeave 以單一 `$devweave` router，讓 Codex 在 repository 內以可追溯的探索、設計、實作、驗證與三道人工作業關卡交付軟體變更。

## Accepted Capabilities

- 公開 chat surface 為 `new/feature/refactor/bug/next/status/revise/approve/wiki bootstrap`；`$devweave wiki bootstrap` 對整個 repository 冪等建立或續接一般 feature-profile Work Item，不另開生命週期。
- High-risk G3 在 final artifacts 穩定後由既有單一 router 固定啟動 1 個 isolated、read-only Independent Review Agent；standard/low risk 不啟動。G2 `Design It Twice` 的 3+ sub-agents 仍是獨立的 optional design comparison。
- High-risk reviewer 只能讀取核准 artifacts、完整 diff、risk/scope、baseline、Wiki context 與 evidence，不繼承主 Agent reasoning，也不得修改 source/Wiki/ledger 或執行 approve/revise/close。Human G3 approval 仍是最後關卡。
- Review result 的 `passed` 正常通過；`unavailable`、timeout、malformed fallback 與 advisory findings 是 warning；critical security、data-loss、不可回復性或 scope finding 只有具名、窄幅 `review-critical` acceptance waiver 可解除。
- G1 採 Wiki-first：先讀 root `wiki/index.md`，再讀最多五個相關頁面，保存每頁 status、content hash 與 stored/computed source fingerprint；只有先記錄 gap 才回查最小必要 source。
- 每個新式 Work Item 在 G3 前必須完成 Knowledge Review：可重用知識採 `promote`，沒有 durable knowledge 時採有理由的 `no-update`，而不是強迫每次產生 Wiki diff。
- G3 可將驗證後的 overview、architecture、module、entity、pattern、dependency、decision、guide 與 synthesis 知識提升到 root `wiki/`；affected pages、最多五個 content targets、index、append-only log 與 source provenance 由 engine 驗證。
- `.devweave/baseline/` 保存 accepted governance truth；`wiki/` 保存細緻且 source-bound 的 codebase knowledge。
- 不提供第二套 router、orchestrator、agent、runtime installer、RAG 或資料庫。Repository 可提供 `grill-me`、`grilling`、`codebase-design`、`diagnosing-bugs` 與 `tdd` 五個 project-local companion Skills，但它們不擁有 lifecycle、artifact、evidence 或 gate。
- Root `AGENTS.md` 定義 companion Skill precedence；DevWeave 的 phase、G2 寫入限制、Wiki lifecycle、Git／remote tracker 邊界與 `$devweave revise` 永遠優先。
- VS Code Extension 可在已開啟的空白 workspace 中，經使用者 modal confirmation 直接安裝完整 DevWeave bootstrap：`.agents/skills/devweave/`、`.codex/hooks.json`、`.devweave/project.json`、baseline、work-item/cache 目錄與 Wiki starter；不需要 Codex Chat、手動 CLI、網路或外部 process。
- 既有合法 workspace 維持唯讀 dashboard、prompt preview/copy 與 workflow projection；相容 bootstrap bytes 只採用、不覆寫，任何 conflict、critical diagnostic 或寫入錯誤都 fail closed 並回報 exact paths。
- Extension 的公開下拉、Knowledge recommendation CTA 與 Command Palette `DevWeave: Bootstrap Codebase Wiki` 共用同一 prompt-only intent，精確產生 `$devweave wiki bootstrap`；Extension 不執行 CLI、不寫 live Wiki。

## Roadmap

初版優先使用 deterministic、dependency-free 的檔案模型。大型 repository 若經 profiling 證實 source hashing 為瓶頸，可在不改 tracked contract 的前提下加入可再生 cache。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

Companion Skills provenance: `20260802-215810-feature-matt-pocock-skills`（待 G3 核准）。

Bootstrap provenance: `20260803-112312-feature-vs-code-devweave`（待 G3 核准）。

Codebase LLM Wiki provenance: `20260803-161041-feature-codebase-llm-wiki`（待 G3 核准）。

Independent Review provenance: `20260804-122803-feature-g3-review-agent`（待 G3 核准）。

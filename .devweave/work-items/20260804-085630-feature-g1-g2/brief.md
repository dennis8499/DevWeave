# 工作摘要：建立 G1/G2 互動式決策流程

<!-- DEVWEAVE:artifact=brief version=1 work=20260804-085630-feature-g1-g2 kind=feature -->

## 問題與目標

目前 DevWeave 已要求 G1/G2 在 Gate 前完成 artifacts 與明確 human approval，但 router 與 phase guidance 沒有把「關鍵決策逐題問答」寫成強制流程。結果 agent 可能自行補上產品需求或設計取捨，直到 Gate 才讓使用者看到完整結果，降低需求共同理解與可追溯性。

本工作要讓 managed repository 的 G1/G2 形成可觀察的互動閉環：先由 agent 自動查證 repository facts，再使用對應 companion Skill 逐題確認會影響目標、範圍、介面、風險、相容性或驗收的關鍵決策；使用者回答回流至既有 artifacts，validate 後再由使用者做正式 Gate approval。

目標使用者是透過 Codex 使用 DevWeave 的 repository 維護者、開發者與 reviewer。成功訊號是政策文件、phase references、使用手冊與 repository contract tests 對上述行為一致，且未核准的 G1/G2 不會被聊天層默默推進。

## 現況證據

### Wiki facts

- `wiki/overview.md` 說明 DevWeave 是單一 router，G1/G2/G3 是人工關卡；產品實作只在 current G2 後進行。
- `wiki/architecture/devweave-knowledge-workflow.md` 說明 Python engine 擁有 lifecycle 與 gate policy，G1 context 必須 index-first，Wiki 在 G2 與 implementation 期間唯讀。
- `wiki/modules/knowledge-engine.md` 列出既有 machine surface，沒有 pending-question state、互動問答 ledger 或新的 approval schema。

### Source-backed facts

- `.agents/skills/devweave/SKILL.md` 已要求 G1、G2、G3 的 explicit human approval，以及使用 `grill-me`/`grilling`、`codebase-design`、`diagnosing-bugs` 與 `tdd` 的 phase mapping。
- `requirements-phase.md` 與 `design-phase.md` 已要求 Gate summary、validate 與 approval，但尚未明確規定關鍵決策逐題問答、等待回答與不可自行補決策。
- `AGENTS.md`、`README.md` 與 `docs/使用手冊.md` 已宣告 DevWeave 是唯一 router，且 companion Skills 不擁有 lifecycle、artifact、evidence 或 gate。
- `tests/test_repository_contract.py` 目前驗證 companion allowlist、provenance 與 side-effect precedence，但沒有檢查互動問答契約。

### Inferences

- 問題位於聊天層 router／phase instructions 的行為契約，不需要新增 Python engine state、CLI command、JSON schema 或 VS Code UI。
- 既有 `grilling` 已提供一次一題、等待回覆與提供建議的通用方法；需要由 DevWeave phase guidance 明確啟用並界定只處理關鍵決策。

### Unresolved gaps

- 過去已關閉 work item 的 ledger 只保存 approval event，不保存完整對話，因此無法由 repository 證明某次 approval 是否伴隨充分的問答；本工作以未來可驗證的政策與手動情境驗收補足此缺口。

## 範圍

本工作修改 DevWeave router 與 G1/G2/G3 phase guidance、root repository policy、README、繁體中文使用手冊與 repository contract tests。內容會定義：事實與決策的區分、關鍵決策逐題提問、使用者回答回流既有 artifacts、validate 後 Gate Double Check、明確 approval，以及新決策透過 `revise` 回到最早受影響階段。

執行時 scope 限於：

- `.agents/skills/devweave/SKILL.md`
- `.agents/skills/devweave/references/requirements-phase.md`
- `.agents/skills/devweave/references/design-phase.md`
- `.agents/skills/devweave/references/verification-phase.md`
- `AGENTS.md`
- `README.md`
- `docs/使用手冊.md`
- `tests/test_repository_contract.py`

## 非目標

不新增 pending-question engine、CLI command、JSON/JSONL ledger 欄位、public API、VS Code Extension UI 或新的 work-item lifecycle；不修改既有 `grill-me`、`grilling`、`codebase-design`、`diagnosing-bugs`、`tdd` 內容與 `skills-lock.json`；不修改 product runtime、Wiki content、baseline 或既有 gate semantics。

## 風險

風險等級：standard

主要風險是 instruction wording 變更可能使 agent 過度提問、漏問關鍵決策或把一般 implementation detail 當成 Gate decision。以「只問 material decision、一次一題、提供推薦與取捨、低風險細節列為假設」限制範圍，並以 contract tests 與手動對話情境驗收。變更可逆，既有 CLI、state、gate fingerprints、companion provenance 與 product verification commands 維持相容。

本 work 使用 standard verification profile；由於變更影響 repository governance 與 tracked tests，G3 仍執行既有必要驗證，不因沒有 product runtime 變更而跳過 Gate。

## Profile 補充

本 feature 保持既有單一 router、三道 Gate、Wiki-first、G2 前唯讀與 companion Skill precedence；新增的是聊天層互動決策契約，不是第二套狀態機。

<!--
- new：願景、限制、roadmap 與第一個 vertical slice。
- feature：現況、價值、影響面與相容性。
- refactor：行為契約、技術問題、安全接縫與基準。
- bug：expected/actual、重現證據與 root-cause 假設。
-->

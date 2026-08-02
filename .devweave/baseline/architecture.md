# Architecture Baseline

此文件保存已驗收的系統邊界、介面與長期設計決策。由 DevWeave 工作項在 G3 前更新。

## System Context

Codex 透過 `.agents/skills/devweave/SKILL.md` 路由公開意圖；`devweave.py` 提供 JSON machine CLI；`devweave_core.py` 擁有 work locks、state、events、evidence 與 gate；`knowledge_core.py` 以 Python standard library 提供 Wiki bootstrap、frontmatter、source fingerprint、lint、snapshot 與 seal。單一 `.codex/hooks.json` PreToolUse hook 呼叫 `guard.py`。五個 `.agents/skills/<companion>/` 目錄提供階段內工程方法，root `AGENTS.md` 是它們與唯一 DevWeave router 之間的 precedence interface。

## Boundaries and Interfaces

- `.devweave/work-items/`：machine lifecycle、artifacts 與 evidence；不得由 agent 直接編輯 JSON/JSONL ledgers。
- `.devweave/baseline/`：G3 接受的治理層 truth。
- `wiki/`：一般 Markdown 知識；G1 讀取，G2/implementation 唯讀，verification 僅允許 knowledge plan 精確 targets 與 coupled index/log。
- `.agents/skills/<companion>/`：由 `skills-lock.json` 追溯的 project-local upstream copies；只消費目前 phase context，產出必須回流 DevWeave artifact 或 evidence，不直接操作 machine ledger、Git 或 remote tracker。
- Product source、baseline 與 knowledge 各自具有 fingerprint。Wiki-only 變更不使 product evidence stale，但會使 G3 stale。
- Knowledge sources 固定為 1–5 個 repo-relative product paths；directory 以單次 Git listing 展開 tracked 與 non-ignored untracked files，再依排序後 current content hash。

## Accepted Decisions

- 保持 schema version 1，knowledge settings/state 採 additive compatibility；沒有 `base_knowledge` 的舊 active work 不新增追溯 blocker。
- `init/start` 非破壞性建立或採用 root `wiki/`；不相容同名內容 fail closed，交由 `doctor` 回報。
- G3 只強制處理本 work item product diff 真正影響的既有頁面；無影響且無 Wiki diff 時不要求 machine no-update rationale。
- Critical lint、undeclared/unchanged targets、未刷新 affected pages 或 log rewrite 阻擋 G3；其他 stale/orphan/semantic findings 為 warnings。
- Hook 是 Codex guardrail 而非 OS sandbox，G3 必須重新 reconcile 完整 Wiki diff。
- Companion Skills 採精確 allowlist 與未修改的 project-local copies；不安裝 Matt Pocock 的 setup/spec/ticket/implement orchestration。Instruction conflict 由 root policy 解決，upstream 更新必須建立新的 DevWeave feature。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

Companion Skills provenance: `20260802-215810-feature-matt-pocock-skills`（待 G3 核准）。

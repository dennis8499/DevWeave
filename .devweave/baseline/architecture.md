# Architecture Baseline

此文件保存已驗收的系統邊界、介面與長期設計決策。由 DevWeave 工作項在 G3 前更新。

## System Context

Codex 透過 `.agents/skills/devweave/SKILL.md` 路由公開意圖；`devweave.py` 提供 JSON machine CLI；`devweave_core.py` 擁有 work locks、state、events、evidence、gate、bootstrap profile 與 Knowledge Review/plan currentness；`knowledge_core.py` 以 Python standard library 提供 Wiki reserved-starter preflight/bootstrap assessment、frontmatter、context records、coverage、canonical scaffold、source fingerprint、lint、snapshot 與 seal。單一 `.codex/hooks.json` PreToolUse hook 呼叫 `guard.py`。五個 `.agents/skills/<companion>/` 目錄提供階段內工程方法，root `AGENTS.md` 是它們與唯一 DevWeave router 之間的 precedence interface。

## Boundaries and Interfaces

- `.devweave/work-items/`：machine lifecycle、artifacts 與 evidence；不得由 agent 直接編輯 JSON/JSONL ledgers。
- `.devweave/baseline/`：G3 接受的治理層 truth。
- `wiki/`：一般 Markdown 知識；G1 讀取，G2/implementation 唯讀，verification 僅允許 knowledge plan 精確 targets 與 coupled index/log。
- `.agents/skills/<companion>/`：由 `skills-lock.json` 追溯的 project-local upstream copies；只消費目前 phase context，產出必須回流 DevWeave artifact 或 evidence，不直接操作 machine ledger、Git 或 remote tracker。
- Product source、baseline 與 knowledge 各自具有 fingerprint。Wiki-only 變更不使 product evidence stale，但會使 G3 stale。
- Knowledge sources 固定為 1–5 個 repo-relative product paths；directory 以單次 Git listing 展開 tracked 與 non-ignored untracked files，再依排序後 current content hash。
- `init_project()` 先在 project lock 外檢查 Wiki，再於 lock 內重檢，成功補齊 Wiki 後才建立 project、baseline、cache 與 work-item control state；reserved conflict 不產生 partial control bundle。
- `knowledge bootstrap/review/context/plan/scaffold/seal` 都是唯一 router 下的 machine namespace；bootstrap 仍是 `kind: feature` 並沿用 G1/G2/G3/session binding，沒有第二個 Wiki state machine。
- High-risk G3 reviewer 由既有 DevWeave router 啟動 exactly once；Python engine 不 spawn Agent，只透過 machine-only `review record` 驗證固定 JSON、建立 additive `kind: review` evidence、report hash、current source/Git provenance 與 bounded raw log。不存在第二個 lifecycle、router、orchestrator 或平行 ledger。
- VS Code Extension 的 bootstrap recommendation 是 filesystem-only、non-authoritative projection；三個入口只經 `PromptComposer` 預覽/複製，engine output 才決定 create/resume/already-complete 與 gate currentness。

## Accepted Decisions

- 保持 schema version 1，knowledge settings/state 採 additive compatibility；只有新 Work Item 預設 `knowledge_review_required: true`，缺少 marker 的舊 active work 不新增追溯 blocker。
- `init/start` 非破壞性建立或採用 root `wiki/`；不相容同名內容 fail closed，交由 `doctor` 回報。
- `init/start` 對 missing、empty 或 custom-only Wiki 採 reserved-starter compatibility；只有 reserved starter file/directory 的錯誤 type 或 frontmatter 產生 `knowledge_conflict`。
- Bootstrap manifest 舊 entry 缺少 `existingPolicy` 時安全正規化為 `exact`；只有明確列出的 project、baseline、Wiki starter contract 可 `adopt-compatible`，未知 policy/kind 在任何 write 前 fail closed。
- 每個新式 Work Item 都必須有 current `promote|no-update` review；產品 source fingerprint 改變會 invalid review 並清空 plan。`no-update` 僅允許非 bootstrap、無 affected page、無 Wiki diff且 rationale 非空。
- Bootstrap readiness 要求 active/sourced/current 的 overview、architecture 與 module；bootstrap G3 必須 upsert 三至五個內容頁、零 product diff、零 delete，並同步 index/log/seal。既有 Wiki 超過五頁不影響 already-complete 判定。
- Canonical scaffold 支援九種內容型別，只允許 planned new upsert、合法 type directory 與 1–5 sources，採 exclusive no-overwrite placeholder create；seal 拒絕 placeholder、template token、invalid source 與 critical lint。
- Critical lint、undeclared/unchanged targets、未刷新 affected pages 或 log rewrite 阻擋 G3；其他 stale/orphan/semantic findings 為 warnings。
- Hook 是 Codex guardrail 而非 OS sandbox，G3 必須重新 reconcile 完整 Wiki diff。
- Companion Skills 採精確 allowlist 與未修改的 project-local copies；不安裝 Matt Pocock 的 setup/spec/ticket/implement orchestration。Instruction conflict 由 root policy 解決，upstream 更新必須建立新的 DevWeave feature。

## DevWeave Control Center VS Code Extension

- `vscode-extension/` 是 TypeScript Extension Host、vanilla Webview 與 esbuild bundle；Python DevWeave engine、JSON contract、work state、events、evidence、baseline 與 Wiki 仍是權威來源。
- `WorkspaceSnapshotReader` 只使用 VS Code workspace file API 讀取 project/work artifacts、evidence、events、baseline、Wiki、hook 與 skill metadata；不呼叫 Python、shell、Git、外部網路或 repository write API，也不自行重建 fingerprint。
- `BootstrapInstaller` 是受控的唯一 bootstrap write seam；它接收 build-time source-derived bundle 與 workspace filesystem adapter，集中執行 manifest path containment、SHA-256/byte-length integrity、parent/symlink/type preflight、same-byte adoption、idempotence 與 write-failure rollback。
- `bootstrap-compat.ts` 是 project/baseline/Wiki semantic contract 的單一 deep module；`BootstrapInstaller` 與 `WorkspaceSnapshotReader` 共用 normalized `existingPolicy`/`compatibility` metadata 與 validator，避免 Extension 顯示與實際寫入結果分歧。
- `VscodeBootstrapWorkspace` 僅透過 VS Code `workspace.fs` 寫入固定 manifest destinations；`ExtensionController` 只負責 workspace root、native modal confirmation、installer invocation、snapshot refresh 與 result reporting。既有合法 `project.json` 或 critical diagnostic 不會觸發自動重建。
- `esbuild.mjs` 從 repository 的 DevWeave skill、hook 與 starter templates 產生 VSIX 內 `dist/bootstrap/manifest.json`，bundle version 直接讀取 `package.json`；每個 source 都有 byte length/SHA-256，七個資料型 bootstrap destinations 明確宣告 semantic compatibility，其餘 controls 維持 exact。Runtime 不下載、不執行 source，也不依賴 Codex Chat、Python、shell、Git 或 network 完成 bootstrap。
- `PromptComposer` 是唯一 action seam，將 `ActionIntent` 轉成 deterministic、repo-relative、sanitized `PromptBundle`；Webview 只能經 `previewAction` 顯示預覽，再由使用者確認 `copyAction` 到 Codex Chat。Extension 不直接執行 mutation。
- `PreviewGate` 是純 Extension host module；copy ticket 綁定 panel identity、typed intent、prompt bundle、snapshot revision 與一次性 consume。Host 只接受 matching current ticket，Refresh、selection、initialization 或 snapshot update invalidate stale tickets；clipboard failure 只允許同一 ticket safe retry 一次。Host-launched `actionPreview` 傳回相同 intent/bundle/revision，`copyNextAction` 不得 bypass preview。
- Control Center 的 Wiki scheduler 將 query/type/show-all 結果實際 mount 到 `#wiki-results`；五個區域以 tab/tabpanel `aria-controls`/`aria-labelledby`、roving tabindex、方向鍵/Home/End 與 focus restore 實作。主要 CTA、native modal action、error、readiness 與 empty-state 使用繁體中文，technical command names 保留於 code label。
- Control Center 對 high-risk acceptance 投影 `Independent Review` readiness：missing/unavailable/advisory 為 attention，critical 為 not-ready，passed 且 source current 才為 ready；Extension 不啟動 Agent、engine、shell、Git、network 或 lifecycle mutation。
- Activity Bar TreeView 提供 repository/work-item navigation；Dashboard/Webview 提供 welcome、doctor、phase/gate、task/evidence、Wiki-first、acceptance 與唯讀 audit projection。多 work item 必須明確選取，不以第一筆資料默選。
- UI 使用 VS Code theme tokens、Codicons、CSP、ARIA/focus、high-contrast、reduced-motion 與非色彩單獨狀態表達；主要內容保持不透明，僅在控制項使用輕微透明效果。
- `extension-typecheck`、`extension-tests`、`extension-package` 與 `extension-smoke` 透過 DevWeave command profiles 管理；Extension 不提供 branch、commit、push、PR、Marketplace release、版本比較或還原。0.2.1 package verifier 必須同時確認 0.2.0/0.1.0 rollback artifacts retention。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

Companion Skills provenance: `20260802-215810-feature-matt-pocock-skills`（待 G3 核准）。

Control Center provenance: `20260803-090218-feature-devweave-control-center-vs-code-extensio`（待 G3 核准）。

Bootstrap provenance: `20260803-112312-feature-vs-code-devweave`（待 G3 核准）。

Codebase LLM Wiki provenance: `20260803-161041-feature-codebase-llm-wiki`（待 G3 核准）。

Independent Review provenance: `20260804-122803-feature-g3-review-agent`（待 G3 核准）。

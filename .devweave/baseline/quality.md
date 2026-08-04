# Quality Baseline

此文件保存已驗收的非功能需求、驗證命令與品質政策。由 DevWeave 工作項在 G3 前更新。

## Quality Attributes

- Determinism：stdlib-only frontmatter、canonical JSON、sorted paths、streaming SHA-256、exclusive canonical scaffold 與 atomic per-file writes。
- Safety：所有 knowledge paths 固定在 root `wiki/`；source 禁止進入 Wiki、`.devweave`、`.git` 或 repo 外；中間 symlink escape fail closed。
- Compatibility：schema version 1 additive migration、既有 Wiki 不覆寫、缺少 review marker 的 legacy active work 不追溯阻擋、既有 verbs 與 JSON envelope 不變。
- Traceability：G1 context records、G3 Knowledge Review/plan/seal、work provenance、index/log coupling、baseline 與獨立 fingerprints 均進入 machine validation。
- Independent Review safety：report 只可從 work-item incoming containment 讀取，受 fixed JSON、UTF-8、size bound、AC/TASK validation、secret redaction、SHA-256、source fingerprint 與 Git HEAD provenance 保護；critical finding 必須 exact named `review-critical` acceptance waiver。
- Review compatibility：schema version 1 additive nested review metadata；legacy evidence 可讀但不能冒充 current high-risk review，standard/low risk 不產生 reviewer requirement。
- Bounded knowledge：G1 固定 index 加最多五個內容頁，每個 Wiki page 最多五個 sources，每次 promotion 最多五個 content targets；不加入 vector/FTS/token measurement runtime。
- Instruction safety：repository contract 固定唯一 `devweave` router、精確五個 companion allowlist、folder/frontmatter identity、local-link containment 與 root precedence policy。
- Supply-chain traceability：`skills-lock.json` 記錄每個 upstream source、skillPath 與 computed hash；更新只能在新的 DevWeave feature 中人工觸發與檢閱。
- Extension bootstrap safety：manifest destinations/source 必須 repo-relative 且不重複；每個 bundled source 驗證 SHA-256/byte length；ancestor symlink、非預期 type、content conflict 與 malformed bundle 均在寫入前拒絕。所有 repository write 只存在於確認後的 VS Code filesystem adapter，rollback 只刪除本次建立的 files。
- Extension bootstrap compatibility：同 bytes 採用、重跑回報 idempotent、Windows/POSIX relative paths canonicalize 成相同 targets；既有合法或 critical-diagnostic project 不會由 initialize 自動修復。

## Verification Commands

- `python -B -m unittest discover -s tests -v`：83 項通過，包含 bootstrap G1→G3、review/no-update、context currentness、coverage、九種 scaffold、seal、CLI/guard、legacy 與 repository contract coverage。
- Repository contract tests：7 項通過，包含 single-router Codebase Wiki 閉環文件契約。
- `npx skills@latest list -a codex`：只列出唯一 local `devweave` router 與五個 `mattpocock/skills` companions。
- `python -B <skill-creator>/scripts/quick_validate.py .agents/skills/devweave`：通過。
- `git diff --check`：無 whitespace error；Windows checkout 僅回報既有 LF/CRLF conversion warnings。
- `vscode-extension/npm test`：26 項通過，涵蓋 BootstrapInstaller、bootstrap/review/coverage projection、legacy/unknown-state fail-closed、三個 prompt-only 入口、protocol、snapshot、prompt 與 security regression。
- `vscode-extension/npm run typecheck`：通過；`npm run package` 產生 production bundle，manifest 具 15 directories、40 files（32 skill files），source hash/length 全數匹配。
- `vscode-extension/npm run test:smoke`：VS Code Extension Host activation、Activity Bar view 與 `devweave.initialize`/既有 commands 通過。
- Independent Review targeted coverage：Python/CLI 覆蓋 passed、unavailable、advisory、critical、timeout/malformed-shaped fallback、waiver、stale source、report containment/size/redaction/hash/provenance；Extension 覆蓋 missing、passed、advisory、unavailable、critical 與 legacy projection。
- High-risk DevWeave verification：`extension-package`、`extension-smoke`、`extension-tests`、`extension-typecheck` 與 root `unit-tests` 均由 CLI verify 登錄為 current passing evidence。

## Operational Constraints

- Python 3.11+、Git repository、UTF-8、無第三方 runtime dependencies。
- Source pages 預期維持 1–5 個核心 sources；health payload 限制 page/finding summaries 數量。
- Repository 必須信任 hook；外部 editor 或停用 hook 的修改只能在 G3 reconciliation 被偵測。
- 完整 83 項 Windows suite 在目前環境約 242 秒內完成；`unit-tests` verification timeout 為 360 秒以保留合理環境抖動餘裕。
- Companion Skills 僅增加 Markdown、YAML 與一個未自動執行的 Bash template；Node.js／npx 與 network 只在人工安裝或更新時需要，不是 DevWeave runtime dependency。
- Extension bootstrap 的 VSIX package source 是 build-time source-derived；runtime 僅使用內嵌 manifest/resource reader 與 VS Code workspace API，不啟動 Python、shell、Git、network 或任意 child process。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

Companion Skills provenance: `20260802-215810-feature-matt-pocock-skills`（待 G3 核准）。

Bootstrap provenance: `20260803-112312-feature-vs-code-devweave`（待 G3 核准）。

Codebase LLM Wiki provenance: `20260803-161041-feature-codebase-llm-wiki`（待 G3 核准）。

Independent Review provenance: `20260804-122803-feature-g3-review-agent`（待 G3 核准）。

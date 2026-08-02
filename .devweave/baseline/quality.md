# Quality Baseline

此文件保存已驗收的非功能需求、驗證命令與品質政策。由 DevWeave 工作項在 G3 前更新。

## Quality Attributes

- Determinism：stdlib-only frontmatter、canonical JSON、sorted paths、streaming SHA-256 與 atomic per-file writes。
- Safety：所有 knowledge paths 固定在 root `wiki/`；source 禁止進入 Wiki、`.devweave`、`.git` 或 repo 外；中間 symlink escape fail closed。
- Compatibility：schema version 1 additive migration、既有 Wiki 不覆寫、legacy active work 不追溯阻擋、公開 verbs 與 JSON envelope 不變。
- Traceability：G1 context、G3 plan/seal、work provenance、index/log coupling、baseline 與獨立 fingerprints 均進入 machine validation。
- Instruction safety：repository contract 固定唯一 `devweave` router、精確五個 companion allowlist、folder/frontmatter identity、local-link containment 與 root precedence policy。
- Supply-chain traceability：`skills-lock.json` 記錄每個 upstream source、skillPath 與 computed hash；更新只能在新的 DevWeave feature 中人工觸發與檢閱。

## Verification Commands

- `python -B -m unittest discover -s tests -v`：62 項通過，包含 companion allowlist、provenance、relative-link 與 precedence contract coverage。
- `PYTHONPATH=tests python -B -m unittest tests.test_repository_contract -v`：6 項 targeted repository contract tests 通過。
- `npx skills@latest list -a codex`：只列出唯一 local `devweave` router 與五個 `mattpocock/skills` companions。
- `python -B <skill-creator>/scripts/quick_validate.py .agents/skills/devweave`：通過。
- `git diff --check`：無 whitespace error；Windows checkout 僅回報既有 LF/CRLF conversion warnings。

## Operational Constraints

- Python 3.11+、Git repository、UTF-8、無第三方 runtime dependencies。
- Source pages 預期維持 1–5 個核心 sources；health payload 限制 page/finding summaries 數量。
- Repository 必須信任 hook；外部 editor 或停用 hook 的修改只能在 G3 reconciliation 被偵測。
- 完整 62 項 Windows suite 在目前環境約 148 秒內完成；verification command timeout 應保留合理餘裕。
- Companion Skills 僅增加 Markdown、YAML 與一個未自動執行的 Bash template；Node.js／npx 與 network 只在人工安裝或更新時需要，不是 DevWeave runtime dependency。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

Companion Skills provenance: `20260802-215810-feature-matt-pocock-skills`（待 G3 核准）。

# Quality Baseline

此文件保存已驗收的非功能需求、驗證命令與品質政策。由 DevWeave 工作項在 G3 前更新。

## Quality Attributes

- Determinism：stdlib-only frontmatter、canonical JSON、sorted paths、streaming SHA-256 與 atomic per-file writes。
- Safety：所有 knowledge paths 固定在 root `wiki/`；source 禁止進入 Wiki、`.devweave`、`.git` 或 repo 外；中間 symlink escape fail closed。
- Compatibility：schema version 1 additive migration、既有 Wiki 不覆寫、legacy active work 不追溯阻擋、公開 verbs 與 JSON envelope 不變。
- Traceability：G1 context、G3 plan/seal、work provenance、index/log coupling、baseline 與獨立 fingerprints 均進入 machine validation。

## Verification Commands

- `python -B -m unittest discover -s tests -v`：60 項通過（既有 48 項與新增 12 項 CLI/guard/knowledge coverage）。
- `python -B <skill-creator>/scripts/quick_validate.py .agents/skills/devweave`：通過。
- `git diff --check`：無 whitespace error；Windows checkout 僅回報既有 LF/CRLF conversion warnings。

## Operational Constraints

- Python 3.11+、Git repository、UTF-8、無第三方 runtime dependencies。
- Source pages 預期維持 1–5 個核心 sources；health payload 限制 page/finding summaries 數量。
- Repository 必須信任 hook；外部 editor 或停用 hook 的修改只能在 G3 reconciliation 被偵測。
- 完整 60 項 Windows suite 在目前環境約 164 秒內完成；verification command timeout 應保留合理餘裕。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

# 功能驗收：整合 Codebase LLM Wiki 閉環

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260803-161041-feature-codebase-llm-wiki -->

## 驗證矩陣

Current product source fingerprint：`adeb69991c6cfa916591c9ebda1b9126311cd4c7881492b0644c8cc199f38b7c`。

| AC | TASK | Current evidence | 結果 |
| --- | --- | --- | --- |
| AC-001 | TASK-002, TASK-003, TASK-007 | EVID-008 | create/resume/already_complete 與無 scope machine bootstrap tests 通過。 |
| AC-002 | TASK-001, TASK-002, TASK-007 | EVID-008, EVID-014 | Bootstrap G1→G3、3–5頁、零 product diff、核心頁/index/log/seal 驗證通過。 |
| AC-003 | TASK-001, TASK-002, TASK-007 | EVID-008 | Index-first context records、content/source drift currentness 通過。 |
| AC-004 | TASK-003, TASK-006, TASK-007 | EVID-008 | Nonfresh gap、最小 source fallback 與四類 discovery output contract 通過。 |
| AC-005 | TASK-002, TASK-003, TASK-007 | EVID-008, EVID-014 | Review state/event、product fingerprint invalidation 與 plan reset 通過。 |
| AC-006 | TASK-002, TASK-007 | EVID-008 | promote/no-update rationale、bootstrap/affected/Wiki-diff 限制通過。 |
| AC-007 | TASK-001, TASK-002, TASK-007 | EVID-008 | affected/covered/uncovered 與五個 content target 上限通過。 |
| AC-008 | TASK-001, TASK-003, TASK-007 | EVID-008 | 九種 canonical scaffold 與 dependency/decision conditional fields 通過。 |
| AC-009 | TASK-001, TASK-003, TASK-007 | EVID-008, EVID-014 | Phase/G2/review/plan/path/source/no-overwrite/placeholder/token/guard/seal 通過。 |
| AC-010 | TASK-002, TASK-003, TASK-007 | EVID-008 | Affected refresh/delete、index/log、source provenance 與 G3 reconciliation 通過。 |
| AC-011 | TASK-004, TASK-005, TASK-007 | EVID-008, EVID-009, EVID-010, EVID-011, EVID-012, EVID-014 | 三入口同 prompt、projection、strict protocol、no direct execution 與 Extension Host activation 通過。 |
| AC-012 | TASK-003, TASK-005, TASK-006, TASK-007 | EVID-008, EVID-009, EVID-011, EVID-012, EVID-013 | Single-router 文件、public contract 與 canonical skill validation 通過。 |
| AC-013 | TASK-002, TASK-004, TASK-007 | EVID-008, EVID-009, EVID-014 | Schema-v1 additive state、legacy marker compatibility、unknown model fail-closed 通過。 |
| AC-014 | TASK-001, TASK-003, TASK-005, TASK-007 | EVID-008, EVID-009, EVID-010, EVID-011, EVID-012, EVID-014 | Deterministic path/source/hash、no partial overwrite、zero new runtime dependency 與 Extension security 通過。 |
| AC-015 | TASK-001, TASK-004, TASK-006, TASK-007 | EVID-008, EVID-009 | Index+五頁、bounded status、filesystem-only Extension、無 vector/FTS/token instrumentation 通過。 |
| AC-016 | TASK-007 | EVID-008, EVID-009, EVID-010, EVID-011, EVID-012, EVID-013, EVID-014 | 全部 configured commands、skill validator 與高風險 review current passing。 |

## Profile 證據

- Feature regression：EVID-008，root Python suite 83 tests、0 failures、242.005 秒。
- Feature acceptance：EVID-009，Extension core/security 16 tests、0 failures。
- Required commands：EVID-010 typecheck、EVID-011 production package、EVID-012 VS Code Extension Host smoke 均 exit 0。
- Skill contract：EVID-013，canonical skill-creator quick validator 通過。
- High-risk review：EVID-014，完整 product/Wiki/baseline diff、legacy bypass、path containment、gate/guard 與 Extension no-execution seam 無未解 blocker。
- EVID-007 因舊 `unit-tests` 240 秒 timeout 而失敗；legacy fixture 修正後以正式 `command set` 將相同完整命令 timeout 調為 360 秒，EVID-008 在未縮減測試範圍下取代該失敗結果。

## 基線更新

- `.devweave/baseline/product.md`：新增第九個公開 `wiki bootstrap` surface、每個新式 Work Item Knowledge Review、3–5頁 bootstrap 與 Extension 三個 prompt-only 入口。
- `.devweave/baseline/architecture.md`：記錄 knowledge model/lifecycle/CLI/Extension seams、bootstrap feature profile、additive review state、canonical scaffold 與 seal currentness。
- `.devweave/baseline/quality.md`：記錄 index+五頁、每頁五 sources、每批五 content targets、83 Python tests、26 Extension npm tests與 360 秒 verification timeout。
- 三個實際變更 paths 已透過 `baseline --target` 完整宣告；無 undeclared 或 declared-but-unchanged baseline path。

## Wiki 知識提升

- 本 Work Item 為缺少新 review marker 的 legacy item，因此不追溯要求 `knowledge review`；仍以 durable-value promotion 建立非空 plan。
- Affected pages：無。Uncovered changed paths：無；模組級 directory sources 已涵蓋全部 product changed paths。
- Content upserts（3）：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`；deletes：無。
- Coupled：`wiki/index.md`、`wiki/log.md`；log 僅追加一筆 `promote | 20260803-161041-feature-codebase-llm-wiki`，未重寫既有 body。
- 五個 changed Wiki pages 全部 active、indexed、由本 Work Item seal；health `healthy`，bootstrap `complete: true`，placeholder/stale/unsealed/critical/warnings 均為空。

## 殘餘風險

- Durable knowledge 的語意價值無法由 path overlap 自動證明，仍由 review rationale 與人工 G3 承擔；engine 只強制 affected-page obligation 與 promotion integrity。
- Extension bootstrap recommendation 是 non-authoritative filesystem projection，不重算 Git/source fingerprint；真正 currentness 仍以 Python engine 為準。
- 不蒐集 Token metric，因此只承諾固定 index+五頁與 gap 後最小 source fallback，不宣稱精確 Token 節省。
- 本 Codex session 的 CLI bind 回覆曾是 `awaiting_hook`，沒有可觀察的 hook confirmation；G3 完整 reconciliation 已通過 engine checks，但不宣稱執行期間 guard binding 已受信任。
- Extension smoke output 含 Node `DEP0190` 與 VS Code 內建 Mermaid private-API warning，Extension Host 仍 exit 0；本變更沒有新增相應 process/network seam。
- Waiver：無。

## 驗收結論

Codebase LLM Wiki 閉環已完整接入唯一 DevWeave router：首次 bootstrap、G1 bounded Wiki-first query、每個新式 Work Item review、coverage-aware promotion、九種 canonical scaffold、G3 seal/reconciliation 與 Extension 三個安全入口均已實作並由 current evidence 驗證。Living baseline 與根 Wiki 已同步，沒有 critical finding、uncovered changed path 或 waiver；可提交 G3 人工核准。

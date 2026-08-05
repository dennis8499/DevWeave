# 功能驗收：優化專案 Skills 可預測性（排除 writing-great-skills）

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260805-081842-feature-skills-writing-great-skills -->

## 驗證矩陣

目前 product source fingerprint：`0531966d5288afe8e5fb06b272097e9bfa0f4eb60c8cea441cecb439e9e3d543`；Git HEAD：`27ca18f67c87c464c61d22241023e6424fe20947`。

| AC | 驗收結果 | 對應 TASK / EVID |
| --- | --- | --- |
| AC-001 exact Skill set 與 maintenance-only exclusion | 通過；唯一 router 加五個 companion，`writing-great-skills` 不進 allowlist、lock 或 bootstrap bundle | TASK-001、TASK-004、TASK-005；EVID-008、EVID-009、EVID-011 |
| AC-002 frontmatter、metadata、relative links、invocation policy | 通過；五個 validator valid，`grill-me` 必要欄位由 repository contract 補驗 | TASK-003、TASK-004、TASK-005；EVID-009、EVID-010、EVID-011 |
| AC-003 phase routing、停止條件與 completion criteria | 通過；G1/G2/G3、Wiki-first、G2 前 regression boundary、public seam 與 decision return 均有文件與 forward-test | TASK-002、TASK-003、TASK-005；EVID-008、EVID-011 |
| AC-004 public interface、upstream provenance 與 no-side-effect boundary | 通過；`skills-lock.json` source/path/hash 與 writer hash 未變，未新增 CLI/schema/router/state/Git 行為 | TASK-001、TASK-004、TASK-005；EVID-009、EVID-011 |
| AC-005 full verification 與 scope | 通過；unit/Extension tests、typecheck、smoke、package、quick validation、forward-test、diff check 已執行；package waiver 見 WAIVER-001 | TASK-005、TASK-006；EVID-003、EVID-005、EVID-006、EVID-007、EVID-012、EVID-013、EVID-014、EVID-015、WAIVER-001 |

TASK-001～TASK-005 均完成；TASK-006 是依 engine contract 進入 verification 的 checkpoint，後續 G3 artifact、Knowledge Review、baseline 與 validation 已在本 acceptance 中完成。

Evidence inventory：EVID-001 為初次 unit suite；EVID-002/EVID-004 是 sandbox access-denied 的失敗嘗試；EVID-003 package 通過；EVID-005 smoke 通過；EVID-006 Extension 73/73 通過；EVID-007 typecheck 通過；EVID-008 forward-test 通過；EVID-009 static/provenance 通過；EVID-010 更正 EVID-009 的文字引用；EVID-011 為完整 regression 集合；EVID-012～EVID-015 為 final current unit/smoke/Extension tests/typecheck；EVID-016 為 final acceptance evidence。source-bound current passing evidence 使用 EVID-009～EVID-016；失敗 evidence 未被當作通過證據。

## Profile 證據

<!--
- new：第一個 vertical slice 的端到端 acceptance。
- feature：acceptance 與 regression。
- refactor：equivalence 與 regression。
- bug：修正前 reproduction 與修正後 regression。
-->

本 Work Item 是 `feature` profile，已具備 `acceptance` 與 `regression`：EVID-011 記錄完整 deterministic/forward verification 集合，EVID-012～EVID-015 記錄 final current command results。Repository contract 11 tests 全部通過；root unit suite 96 tests、1 skipped，Extension tests 73/73。

Quick validation 使用 UTF-8 模式；devweave、codebase-design、diagnosing-bugs、grilling、tdd 通過，grill-me 的 `disable-model-invocation: true` 因 validator 不支援而由 repository contract 明確補驗。`git diff --check` 通過。

## 基線更新

已透過 `baseline --target` 宣告並更新：

- `.devweave/baseline/architecture.md`：新增唯一 router、五 companion allowlist、maintenance-only `writing-great-skills`、local optimization overlay 與 lock provenance 邊界。
- `.devweave/baseline/quality.md`：更新 96-test/11-contract baseline，補上 UTF-8 validator exception、metadata/invocation contract、forward-test 與 Skill completion quality checks。

`skills-lock.json` 未修改；五個 upstream source/path/computedHash 與 G1 固定 hash 均維持不變。

## Wiki 知識提升

Knowledge Review disposition 為 `promote`。Rationale：永久記錄 local Skill optimization overlay、maintenance-only exclusion、五個 companion upstream provenance、phase/Gate boundaries、forward-test 與 repository contract quality checks。

- Affected pages：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`。
- Covered changed paths：六個受治理 Skill 的 Markdown/YAML、`AGENTS.md`、`tests/test_repository_contract.py`。
- Uncovered changed paths：無；三個 affected content targets 已列入 `knowledge plan`。
- Upserts：上述三個 content pages；deletes：無；coupled：`wiki/index.md`、`wiki/log.md`。
- Seal：五個 pages 均由 `knowledge seal` 以 work ID `20260805-081842-feature-skills-writing-great-skills` seal；knowledge fingerprint 為 `9779abdc857e6b0630dd0c8542c89af5d9349bc00d153454d1d1c37bcbcb7780`。
- Wiki health：healthy；pending refresh、unsealed pages、critical lint 與 warnings 均為空；bootstrap assessment 已 complete。

## 殘餘風險

- WAIVER-001：固定 `extension-package` command 會寫入 scope 排除的 tracked `vscode-extension/devweave-control-center-0.2.1.vsix`。EVID-003 已證明 package 57 bootstrap files/117 VSIX entries 通過；為維持 approved scope，generated VSIX 已恢復，其他四個 required commands 有 final current evidence。後續若要提交更新 VSIX，需另開 scope/revise。
- `bind` 目前回報 `awaiting_hook`，因此不宣稱 Codex Guard 已 trusted；G3 以完整 scope/diff/fingerprint/contract/evidence reconcile。
- Standard risk 依 policy 不啟動 Independent Review；沒有 critical finding、review-critical waiver、資料 migration、runtime/security boundary 或公開介面變更。
- EVID-002、EVID-004 的 sandbox access-denied 是已重跑成功的環境限制，不是產品或 Skill failure；EVID-010 已更正 EVID-009 的文字引用。

## 獨立 Review

本 Work Item 為 standard risk。依 DevWeave policy，standard/low-risk G3 不啟動 Independent Review；因此沒有 reviewer、review report 或 review-critical waiver。

## 驗收結論

本 Work Item 已依 approved G1/G2 intent 完成六個受治理 Skill 的可預測性 overlay，排除且未修改 `writing-great-skills`，保留五筆 upstream lock provenance、唯一 router、既有 lifecycle、CLI/schema/Hook/Extension runtime boundary。所有必要 machine checks、current evidence、baseline update、Wiki promote/seal 與 scope reconciliation 已完成。

目前等待使用者明確核准 G3。未收到 G3 approval 前，不執行 `approve` 或 `close`。

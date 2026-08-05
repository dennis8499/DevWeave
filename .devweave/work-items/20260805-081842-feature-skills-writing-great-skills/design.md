# 系統設計：優化專案 Skills 可預測性（排除 writing-great-skills）

<!-- DEVWEAVE:artifact=design version=1 work=20260805-081842-feature-skills-writing-great-skills -->

## 設計摘要

採用「唯一 DevWeave router + 六個受治理 local Skill overlay + 必要契約同步」設計。每個 Skill 保留既有 discovery identity 與 invocation policy；優化集中在 description trigger、SKILL.md 的執行入口、既有 reference 的 progressive disclosure、completion criteria、positive steering 與 stale-reference 清理。

關鍵不變量如下：

- `.agents/skills/devweave/` 仍是唯一 SDLC router；五個 companion 仍只是目前 phase 內的方法。
- `writing-great-skills` 是 maintenance-only exclusion，不修改、不列入 companion allowlist、不進入 `skills-lock.json` 或 Extension bootstrap。
- G1/G2/G3、Wiki-first、human approval、G2 前 tracked-write restriction、G3 Knowledge Review、high-risk review、CLI、JSON schema、Hook 與 Git/remote boundary 完全保持相容。
- `skills-lock.json` 的五個 upstream source/path/hash 是 provenance baseline；local overlay 不改寫其值。
- Skill instruction 不直接操作 machine ledger、Git、remote tracker、production instrumentation 或第二套 lifecycle。

## 選項比較

### DEC-001 候選：Skill 內容的所有權

1. **選定：受治理的 local overlay。** 在 repository-local copies 上改善內容與 phase safety，保留 upstream lock 作為來源基線。這直接滿足本次優化目標，且可由單一 work item 審查與回復。
2. **拒絕：只在 `AGENTS.md` 加 precedence。** 可避免 fork drift，但無法修正 Skill 內部的重複、模糊完成條件與不存在的 Skill reference。
3. **拒絕：重新建立一套 router/skill schema。** 會改變 discovery、lifecycle 或 machine contract，超出保守相容範圍。

### DEC-002 候選：資訊階層

1. **選定：核心入口留在 SKILL.md，分支細節留在既有 references。** SKILL.md 保留所有 branch 都需要的 vocabulary、phase gate、completion bar 與 pointer；`DEEPENING.md`、`DESIGN-IT-TWICE.md`、DevWeave phase references、`tests.md` 與 `mocking.md` 承載條件式細節。
2. **拒絕：把全部內容壓回 SKILL.md。** 會增加 context load、重複與 premature completion 風險。
3. **拒絕：只保留極短描述而移除治理細節。** 會讓 phase boundary、Wiki、approval 與副作用規則依賴外部文件，降低 agent predictability。

## 介面與資料流

### Skill discovery interface

- 每個目標 Skill 保留既有資料夾與 frontmatter `name`；`description` 以 distinct trigger branches 表達使用時機。
- `grill-me` 保留 `disable-model-invocation: true` 與 `agents/openai.yaml` 的 `allow_implicit_invocation: false`；`devweave` 保留 implicit invocation。
- `agents/openai.yaml` 只同步與最終 description 一致的 UI metadata，不新增 tool dependency 或 invocation surface。
- 所有 relative Markdown links 必須留在各自 Skill root 且目標存在；`skills-lock.json` 不變。

### Runtime data flow

```text
使用者意圖
  -> DevWeave status/bind/instructions
  -> current phase 與 approved artifacts
  -> 目前 phase 可用的 Skill method
  -> brief/requirements/design/plan/acceptance 或 evidence
  -> CLI validate/verify + human Gate approval
```

- G1 使用 `grill-me`/`grilling` 逐題處理 material decisions；回答回流 requirements artifacts。
- G2 使用 `codebase-design` 以 module、interface、seam、adapter、depth、locality 與 test surface 比較設計；回答回流 design/plan。
- Bug discovery 使用 `diagnosing-bugs` 建立 red-capable loop；G2 前只用既有命令、temp/cache harness 或其他非 tracked reproduction。
- Current G2 approval 後使用 `tdd` 執行一個 seam 一個 vertical red → minimal green slice；結果回流 task/evidence。
- Verification 由 DevWeave 負責完整 diff、baseline、Knowledge Review、package 與 G3 acceptance；companion Skills 不增加 phase 或 state。

### State、compatibility 與 test surface

- 不新增 state transition、CLI command、JSON field、public chat verb 或 Extension runtime interface。
- `tests/test_repository_contract.py` 將 maintenance-only exclusion、frontmatter、metadata、relative-link、invocation 與 exact companion set 固定成 repository contract。
- `vscode-extension/esbuild.mjs` 既有 explicit six-Skill bundle list 保持不變；package verification 確認 writer 不會被 glob 或 manifest 帶入。
- Skill 的 test surface 是其可觀察的 trigger、phase boundary、completion criterion、reference resolution 與 side-effect contract，不測試 Markdown 的排版細節。

## 失敗模式與回復

- **Frontmatter/metadata 不合法：** quick validation 或 repository contract 失敗；修正 Skill metadata 後重新驗證，不進入下一個 task。
- **Reference 遺失或越出 Skill root：** relative-link contract 失敗；補回正確 pointer 或刪除 stale pointer，不建立外部替代文件。
- **Phase boundary 漂移：** forward-test 發現 G2 前寫入、未回答即前進或 Skill 越過 Gate；以 `revise` 回到最早受影響 phase，重新設計並取得 G2 approval。
- **不存在的 Skill、commit/PR 或 runtime side effect：** 移除指示並改為回流 DevWeave artifact/evidence；不新增未授權工具或 workflow。
- **`writing-great-skills` 或 lock 被修改：** scope/diff check 阻擋 G3；移除 out-of-scope diff，保留 exclusion 與 upstream provenance。
- **上游來源暫時不可取得：** 記錄 gap，使用已記錄的 lock/source baseline，不推測新版內容、不改 lock。
- **驗證失敗：** 保留完整 raw log 與 evidence；依失敗原因回到 implementation、design 或 requirements，不以 waiver 取代可修正的檢查。

回復方式是回復本 work item 的 tracked diff；不需要資料 migration、runtime rollback 或 machine ledger 手工修正。

## 高風險分析

本工作維持 standard risk。Migration、資料安全、認證/隱私、不可逆資料操作與 performance path 均不適用，因為設計不修改產品 runtime、資料 schema、CLI engine、Extension runtime 或 external service。相容性處理由保留 discovery identity、public contract、phase boundary、lock provenance、exact bundle list 與完整 regression/package verification 負責。

## 設計決策

## DEC-001: 採用受治理的 local Skill overlay
- Requirements: REQ-001, REQ-003, REQ-004, NFR-001
- Decision: 直接優化六個目標 Skill 的 local copies；保留名稱、主要觸發方式、DevWeave precedence 與 upstream lock，不修改 `writing-great-skills`。
- Rationale: 同時修正 instruction quality 與 project-specific phase safety，並保持可追溯、可回復與上游 provenance。
- Consequences: local copies 與上游內容可能不同；之後任何 upstream update 仍須另開 DevWeave feature 並重新審查。

## DEC-002: 以 SKILL.md router 加既有 references 的 progressive disclosure 組織內容
- Requirements: REQ-002, NFR-002
- Decision: SKILL.md 只承載跨分支核心語彙、入口、完成條件與 hard boundaries；條件式細節放入既有 reference files。
- Rationale: 降低 context load 與 duplication，同時保留 agent 需要的 deterministic pointers。
- Consequences: 每個 pointer 必須明確寫出觸發條件；reference link integrity 成為驗收的一部分。

## DEC-003: 將 DevWeave phase safety 寫入 companion 使用流程
- Requirements: REQ-002, REQ-003, NFR-001
- Decision: G1/G2/implementation 的 Skill guidance 明確回流既有 artifacts/evidence；G2 前禁止 tracked product/test writes，已批准決策變更一律走 `revise`。
- Rationale: 讓 companion 方法服從唯一 router，而不是建立第二套 approval 或 task state。
- Consequences: Skill 可能在 material decision 未回答、Gate 未批准或 seam 未確定時停止並回到 DevWeave。

## DEC-004: 保留上游 lock，明確排除 maintenance Skill
- Requirements: REQ-004, NFR-001
- Decision: `skills-lock.json` source/path/hash 完全不變；contract test 與必要 root policy 將 `writing-great-skills` 標記為 maintenance-only exclusion，Extension bundle 仍只打包六個受治理 Skill。
- Rationale: lock 表示 upstream provenance，不應把 local overlay 偽裝成 upstream release；exclusion 修正目前 exact-set test 的誤判。
- Consequences: local optimized bytes 由 work item、baseline、Wiki 與 Git diff 追蹤，而非由 lock hash 宣稱為 upstream bytes。

## DEC-005: 以 contract、forward-test 與完整 package verification 驗證行為
- Requirements: REQ-001, REQ-002, REQ-003, NFR-002
- Decision: 驗證包含 UTF-8 skill validation、repository contract、isolated read-only forward scenarios、Python full suite、Extension tests/typecheck/package/smoke、lock/exclusion hash check 與 `git diff --check`。
- Rationale: Markdown 行為無 runtime API 可直接測試，需同時檢查 discovery、phase side effects、reference integrity 與 bundled output。
- Consequences: G3 需保留每個 AC/TASK 的 current evidence；已知 validator 不接受 `disable-model-invocation` 時，以 repository contract 補足該欄位。

## DEC-006: 在 verification 以最小必要範圍更新治理知識
- Requirements: REQ-004, NFR-002
- Decision: G3 使用 `promote` 刷新受影響的 `wiki/overview.md` 與 `wiki/architecture/devweave-knowledge-workflow.md`，同步 coupled `wiki/index.md`/`wiki/log.md`；baseline 只更新 architecture 與 quality。
- Rationale: 技能治理與 router boundary 是 durable knowledge，但不需要新增 module page 或廣泛重寫使用手冊。
- Consequences: Wiki 在 G2/implementation 保持 read-only；只有 declared knowledge plan、seal 與 G3 reconciliation 可以寫入。

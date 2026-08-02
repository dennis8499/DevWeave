# 功能驗收：導入 Matt Pocock 核心工程 Skills 作為階段內方法

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260802-215810-feature-matt-pocock-skills -->

## 驗證矩陣

目前 product source fingerprint：`3c3f53cea58544e98c0e0a6ab9943d68c4c1b32d64e6d1e83124298dadf9b90e`。

| Acceptance | Tasks | Evidence | 結果 |
| --- | --- | --- | --- |
| AC-001 精確 Skill 集合 | TASK-001, TASK-003 | EVID-001, EVID-002 | 通過：唯一 local router `devweave` 加上五個 `mattpocock/skills` companions；lock、frontmatter 與相依檔完整。 |
| AC-002 precedence policy | TASK-002, TASK-003 | EVID-001, EVID-002 | 通過：phase、G2、Wiki、CONTEXT/ADR、Git/tracker、ledger 與 revise 邊界均有 contract coverage。 |
| AC-003 階段使用文件 | TASK-002 | EVID-001, EVID-002 | 通過：README 提供安裝、phase table、四種呼叫範例、更新與 rollback。 |
| AC-004 repository contract | TASK-003 | EVID-001, EVID-002 | 通過：exact allowlist、唯一 router、folder/name、provenance、relative-link 與 policy tests 全數通過。 |
| AC-005 公開 surface 無回歸 | TASK-002, TASK-003 | EVID-001, EVID-002 | 通過：62 項完整 tests 維持 CLI/schema/hook/stdlib contract，exit code 0。 |
| AC-006 人工受管更新 | TASK-001, TASK-002 | EVID-001, EVID-002 | 通過：lock 記錄 computed hashes；README/AGENTS 禁止自動更新並要求新 DevWeave feature 與 G3。 |

## Profile 證據

- `EVID-001`（regression，passed，current）：DevWeave `verify --command unit-tests` 執行 `python -B -m unittest discover -s tests -v`，62 tests 於 148.053 秒內全部通過，exit code 0，未 timeout／truncate；覆蓋 AC-001～AC-006 與 TASK-001～TASK-003。
- `EVID-002`（acceptance，passed，current）：`npx skills@latest list -a codex`、filesystem／lock inspection、policy/docs inspection、scope hygiene、`git diff --check` 與 trailing-whitespace scan 通過；覆蓋 AC-001～AC-006 與 TASK-001～TASK-003。
- Targeted repository contract：設定 `PYTHONPATH=tests` 後執行 `python -B -m unittest tests.test_repository_contract -v`，6 tests 全部通過。既有 test layout 不是 package，未設定 tests import path 的 dotted invocation 會找不到 `devweave_test_support`；project configured discovery command不受影響。

## 基線更新

- `.devweave/baseline/product.md`：將「沒有第二套 skill」精確化為唯一 router／orchestrator，加入五個受治理 companion capabilities 與 precedence。
- `.devweave/baseline/architecture.md`：加入 project-local Skill discovery、root policy interface、artifact/evidence 回流與 manual update boundary。
- `.devweave/baseline/quality.md`：加入 allowlist／frontmatter／relative-link／policy coverage、lock provenance、62-test evidence 與 install-time dependency 限制。

三個實際變更路徑已透過 DevWeave `baseline --target` 完整宣告，沒有 undeclared baseline diff。

## Wiki 知識提升

`knowledge status` 回報 affected pages 為空，Wiki diff 為空，因此沒有建立 knowledge plan、upsert、delete 或 index/log coupling。既有 `wiki/overview.md` 仍為 placeholder warning；它與本次 feature 無 affected-source 關係，不阻擋 G3。

## 殘餘風險

- Session binding CLI 仍回報 `awaiting_hook`，沒有收到可信 hook additional context；因此不能宣稱 PreToolUse guardrail 已啟用。完整 diff、scope 與 G3 validation 是本次的補強，但使用者仍應確認 repository hook 已受信任。
- Installer 對 `diagnosing-bugs` 顯示 Snyk High Risk，而 Gen/Socket 分別為 Safe／0 alerts。人工檢查顯示它包含除錯指令與未自動執行的 HITL Bash template；root precedence 禁止未授權 production instrumentation、Git／remote 操作與 phase 外寫入。後續 upstream 更新仍須重新審查。
- 目前 session 不會熱載入新 Skills；filesystem、lock 與 skills CLI discovery 已驗證，實際對話使用前需開啟新的 Codex session。
- Node.js、npx、npm registry 與 GitHub network 只在安裝／人工更新時需要；第一次 sandbox 執行因 EACCES 失敗，取得明確權限後相同命令成功，不影響 DevWeave runtime。
- Waiver：無。

## 驗收結論

本工作項已依核准設計安裝精確五個未修改的 companion Skills，DevWeave 保持唯一 SDLC router。治理 precedence、使用／更新文件、provenance 與自動 contract coverage 均已完成；feature 所需 acceptance 與 regression evidence current 且通過，scope、baseline 與 knowledge 狀態可供 G3 核准。核准後應立即 close；若不接受 `diagnosing-bugs` 的殘餘供應鏈風險或 hook 未確認狀態，應拒絕 G3 並從 design／implementation revise。

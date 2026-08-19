# 功能驗收：建立公開跨平台 deterministic CI baseline

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260819-115533-feature-deterministic-ci-baseline -->

## 驗證基線

- Work Item：`20260819-115533-feature-deterministic-ci-baseline`；standard-risk feature，G1 scope 與 G2 build 已由使用者核准，TASK-001～TASK-003 均完成。
- Git HEAD：`3662d8622b46a1cab6931da988db3c4280def783`；current product/source fingerprint：`0a699f4b1b7641c5afa82333b44a9cf2c492dbe38a653be08da037974956d8f4`。
- Frozen standard plan：`sha256:be3121730798a8880b20a66919986b395d9a480f2e99cd8c418682908667d4bd`；7 個 selected commands 全部通過，2 個 release-only／dependent commands 依 plan 合法跳過。
- Final Knowledge fingerprint：`c8871a8591018400a90682884932952405c15fa5ce3f2313cd244f9a52a650bd`；planned pages 已全部 seal。

## 驗證矩陣

| Acceptance | TASK／evidence 與結果 |
| --- | --- |
| AC-001 Workflow trigger 與 check 可見性 | TASK-001／TASK-002 通過。`EVID-001` 先固定缺少 workflow 的 red；`EVID-008`、`EVID-012` 目前驗證 PR、`master` push、Python／Node／hygiene jobs、兩個 `fail-fast: false` 且無 `continue-on-error`。Hosted check 顯示仍待人類 push／PR 後觀察。 |
| AC-002 Python matrix | TASK-001／TASK-002 通過。`EVID-008`、`EVID-012` 固定 Ubuntu／Windows／macOS × Python 3.11～3.14 與完整 unittest command；遠端 12 cells 尚未實際啟動。 |
| AC-003 Node matrix | TASK-001／TASK-002 通過。`EVID-005` 為 88/88 Extension tests、`EVID-006` 為 typecheck；`EVID-008`、`EVID-012` 固定 Ubuntu／Windows × Node 20／22、`npm ci` → typecheck → test → build 的順序、lockfile install 與 setup-node 完整 SHA。本機 final `npm run build` 另通過。 |
| AC-004 Hygiene check | TASK-001／TASK-002 通過。`EVID-008`、`EVID-012` 固定獨立 Ubuntu hygiene job 與 `git diff --check`，且沒有忽略非零結果；最終本機 `git diff --check` 無 whitespace error，新 workflow 另經尾端空白掃描。 |
| AC-005 供應鏈與權限 contract | TASK-001／TASK-002 通過。`EVID-008`、`EVID-012` 驗證 top-level 僅 `contents: read`、三次 checkout 均不持久化 credentials、三個官方 Action 為核准完整 SHA、無浮動 major tag、secrets、write permission 或隱藏失敗設定。 |
| AC-006 Doctor capability truth | TASK-001 通過。`EVID-008`、`EVID-012` 驗證 Windows 必須取得 `py-3`、CMD、Windows PowerShell、PowerShell 7、hook schema 與 launcher 真實 probe；非 Windows 只接受精確 Windows-only prerequisite skip detail，不冒充 hosted certification。 |
| AC-007 README 支援邊界 | TASK-003 通過。`EVID-003` 先固定缺少 badge／文件的 red；`EVID-004` 收綠，`EVID-008`、`EVID-012` 再確認 badge、PowerShell／POSIX／Node 本機命令及「CI 開發矩陣不等於正式 release certification」文字。 |
| AC-008 既有回歸與 scope | TASK-001～TASK-003 通過。`EVID-005`～`EVID-011` 為 current standard regression，`EVID-012` 為 current acceptance；最終完整 Python discovery 為 131 passed／1 個既有 symlink privilege skip，Extension build、`git diff --check` 通過。Product diff 只在 `.github/workflows/ci.yml`、`README.md`、`tests/test_repository_contract.py`；其餘是已宣告 baseline、Work Item 與 Knowledge targets。 |

## Profile 證據

- TDD history：`EVID-001`（缺少 workflow）與 `EVID-003`（缺少 README contract）是可歸因、expected-nonzero 的 red evidence；`EVID-002` 是加入 workflow 後的中途 green，因後續 source change 已 stale；`EVID-004` 是 README 完成後 18 項 contract green。Final pass 不依賴 stale 的 `EVID-002`。
- Current standard regression：`EVID-005` `extension-tests`（88 tests）、`EVID-006` `extension-typecheck`、`EVID-007` `unit-tests-cli`（23）、`EVID-008` `unit-tests-contract`（18）、`EVID-009` `unit-tests-core`（45，1 項既有 Windows symlink privilege skip）、`EVID-010` `unit-tests-guard`（15）、`EVID-011` `unit-tests-knowledge`（16）；全部 passed、current、zero-only、gate-eligible。
- Current feature acceptance：`EVID-012` 由 controlled `unit-tests-contract` 產生，18/18 通過，覆蓋 AC-001～AC-008 與 TASK-001～TASK-003，source fingerprint 與 frozen plan current，沒有 undeclared write。
- Plan-defined skips：`extension-package` 為 `release-only`；`extension-smoke` 為 `release-only-dependency:extension-package`。本 standard-risk development baseline 沒有 release context，也沒有 waiver。
- 額外 final reconciliation：完整 Python discovery 131 tests 通過，只有既有 symlink privilege 1 skip；Extension `npm run build` 通過。Pre-G1 clean baseline 另已通過 Doctor、Python 129 tests／1 skip，以及 Extension `npm ci`、typecheck、88 tests、build；後續沒有修改 Extension source、manifest 或 lockfile。

## 基線更新

已在修改前由 DevWeave 宣告 `.devweave/baseline/quality.md`，再以最小 diff 固化 P0-00 的 trigger／matrix、`fail-fast: false`、read-only permission、安全 checkout、完整 Action SHA、無 secrets／Codex API key、frozen plan 結果、TDD evidence、hosted observation boundary 與「development baseline 不等於 release certification」。沒有修改其他 living baseline。

## Wiki 知識提升

- Knowledge Review disposition：`promote`；本 workflow、安全 pin／permission、跨平台矩陣、Doctor capability truth 與本機等價命令會被後續 P0 工作重用，因此具有 durable value。
- Engine-derived affected pages：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`；新增 `wiki/modules/public-ci.md` 覆蓋原本 uncovered 的 workflow。
- Planned upserts：上述四個 content pages；coupled：`wiki/index.md`、`wiki/log.md`；無 delete。六個 targets 已由 `knowledge seal` 一次封存，`pending_refresh=[]`、`uncovered_changed_paths=[]`、`unsealed_pages=[]`。
- Final Knowledge health 為 warning，只因 `wiki/modules/command-policy-engine.md` 與 `wiki/modules/vscode-extension.md` 有本 Work Item 開始前即存在、且不屬 affected／planned targets 的 source-stale warnings；沒有 critical lint，也沒有用 scope expansion 假裝清除警告。

## 獨立 Review

本 Work Item 風險為 `standard`；依 DevWeave policy 不啟動 high-risk 專用的 independent reviewer，也沒有 review evidence 或 review waiver。完整 diff、scope、安全字串、Knowledge 與 evidence reconciliation 由主流程完成。

## 殘餘風險

- `.github/workflows/ci.yml` 尚未被 commit／push，因此 GitHub-hosted 的 12 個 Python cells、4 個 Node cells與 hygiene check 尚無遠端 run；目前證明的是本機 deterministic contract 與現有 tests，不宣稱 hosted matrix 已全綠。這需要人類在自己的 Git 流程 push branch／建立 PR 後觀察。
- Python full suite 保留 1 項 Windows symlink creation privilege skip；此為既有環境權限限制，不解讀為功能失敗，也不宣稱該路徑已在本機完整驗證。
- Package、Extension Host smoke、VSIX release 與 deployment 是明確 non-goal；standard plan 的兩個 skips 不代表 release certification。
- 兩個 unrelated Wiki stale-source warnings 保留，後續應由其實際 source 變更所屬 Work Item refresh，而不是在 P0-00 順便修改。
- Hosted runner image 與完整 Action SHA 未來可能淘汰；需另開受治理變更核對新版 SHA，不應退回浮動 tag。
- Waiver：無。付費第三方 CI、private/self-hosted runner、repository secrets 與 Codex API key：均未引入。

## 驗收結論

G1/G2 核准範圍內的三個 TASK 已完成，TDD red→green、current standard regression、feature acceptance、完整本機 Python suite、Extension build、scope／whitespace reconciliation、quality baseline 與 Knowledge promotion 均已對齊。P0-00 已具備可供 GitHub 執行的公開 CI baseline；唯一無法在未 push 的本機 worktree 取得的是 hosted-run observation，已明確列為外部殘餘風險。目前只等待使用者核准或拒絕 G3；核准前不 approve、不 close，也不執行 commit、push 或 PR。

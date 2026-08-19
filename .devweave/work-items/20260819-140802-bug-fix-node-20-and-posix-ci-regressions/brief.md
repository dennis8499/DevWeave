# 工作摘要：Fix Node 20 and POSIX CI regressions

<!-- DEVWEAVE:artifact=brief version=1 work=20260819-140802-bug-fix-node-20-and-posix-ci-regressions kind=bug -->

## 問題與目標

PR #1 的首次 GitHub-hosted CI run `32218573938` 在 17 個 jobs 中有 10 個失敗：Node 20 的 Ubuntu／Windows 兩格都在 Extension unit tests 失敗，Python 3.11–3.14 的 Ubuntu／macOS 八格都在完整 suite 失敗；Node 22、四個 Windows Python jobs 與 hygiene 則成功。這表示先前本機 Windows／Node 22 的綠燈沒有覆蓋真正的跨版本與跨平台邊界。

本工作項服務 repository 維護者與 PR 貢獻者。目標是在不縮減 matrix、不弱化 Guard／hook policy、不增加 dependency 的前提下，讓 Node 20/22 與 Python 3.11–3.14 的既有 public CI development contract 真正可執行。成功訊號是同一 PR 的 12 個 Python、4 個 Node 與 1 個 hygiene job 全綠，且 0 個 Extension tests、錯誤 child exit 或錯誤平台 launcher 都不能被誤報為成功。

## 現況證據

### Wiki 事實

- 已依序記錄 `wiki/index.md`、`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`、`wiki/modules/public-ci.md`。
- Wiki 固定 public CI 為 12 個 Python cells、4 個 Node cells、1 個 hygiene job；standard profile 為 Extension tests/typecheck 與五組 Python suites，package/smoke 是 release-only skip。
- Wiki 明確區分 development CI 與特定 Windows release certification，並要求 Windows launcher 真實執行、非 Windows capability 明確 skip。
- `wiki/modules/vscode-extension.md` 的 source fingerprint 已 stale；`wiki/modules/public-ci.md` 尚未描述首次 hosted failure，兩者已在 knowledge context 記為 gaps。

### Source-backed 事實

- GitHub Actions run `32218573938`、head SHA `c895cd2a32c454621176e071ecc693f742e29039`：Node 20 log 顯示 `tsx --test "test/unit/**/*.test.ts"` 後直接回報找不到字面路徑 `test/unit/**/*.test.ts`。
- 同一 run 的 Ubuntu Python 3.14 代表性 log 固定為五項失敗：Python executable alias 與 resolved path 不同、Windows `Z:\\missing\\repository` 在 POSIX 被當成相對路徑、三項 `commandWindows` launcher 測試由 `/bin/sh` 執行而在 `(` 處語法失敗。其餘七個 POSIX Python jobs 的失敗測試集合相同。
- `vscode-extension/package.json` 的 `test` script 直接把 glob 傳給 `tsx`；Node 22 支援此 CLI glob，但 Node 20 不支援。
- CLI production code刻意將 executable 正規化為 `Path(...).resolve()`；Guard Verification Policy v2 刻意先評估 configured commands，再處理 generic read-only allowance。兩者都是現行安全契約，不應退回。
- `tests/test_repository_contract.py` 的三個 launcher methods 無平台條件，會在非 Windows 呼叫 `commandWindows`；Windows jobs 已證明真實 launcher path 可通過。
- VSIX builder 會遞迴收集 Extension tree，目前只有兩個明確 excluded files；若新增純 CI runner／test 而不排除，將意外改變 certified 119-entry package。

### 推論

- Node 問題應在 repository-local test-runner seam 修正：由程式明確列舉、排序並以 argv 傳入所有 `.test.ts`，可同時避開 shell glob 差異並在 0 tests 時 fail closed。
- Python 問題都是測試 fixture／平台邊界錯誤；修改 production canonicalization 或恢復 Guard 舊 short-circuit 會弱化已核准安全行為。
- 三項 `commandWindows` contract 在非 Windows 應呈現具名 skip，而不是執行或假裝通過；Windows matrix 繼續提供真實 oracle。

### 未解缺口

- 最終 macOS／Ubuntu 行為只能由 GitHub-hosted runners 觀察。依使用者在 Plan Mode 的決定，產品、文件、Wiki 與本機 profile 穩定後，由使用者先 commit/push；17/17 hosted jobs 全綠才進入 G3 摘要。此 hosted observation 是補充人工證據，不冒充 DevWeave controlled executor evidence。
- 目前沒有未回答、會改變 G1 範圍的 material requirement，沒有 waiver。

## 範圍

- 新增 Extension unit-test runner，遞迴找出並固定排序 `test/unit/**/*.test.ts`，以相同 Node executable 呼叫 lockfile 內的 `tsx/cli`，保留 child output/exit；0 tests、spawn error、signal 或非零 exit 均失敗。
- 新增一項 runner regression test；Extension unit-test current count 由 88 更新為 89。
- 更新 Extension package test script，並把純 CI runner／test 加入 VSIX builder exclusion，維持 58 個 bootstrap files 與 119 個 VSIX entries。
- 修正 CLI、Guard 與 Windows hook launcher 的五項跨平台測試契約，不修改相關 production implementation。
- 更新 current 89-test release surfaces、repository contract 與 quality baseline；G3 promote `overview`、`devweave-knowledge-workflow`、`knowledge-engine`、`vscode-extension`、`public-ci`，同步 index/log/seal。

## 非目標

- 不修改 `.github/workflows/ci.yml` 的 trigger、matrix、permissions、Action SHA 或 commands。
- 不修改 DevWeave lifecycle、CLI schema、Guard／command-policy production semantics、hook JSON、Extension runtime 或公開 API。
- 不加入 dependency、不改 `package-lock.json`，不使用 shell glob adapter 或第三方 glob package。
- 不重建、promotion 或替換 0.2.3 VSIX；不執行 smoke、release、部署、Marketplace 或 branch-protection 工作。
- 不自動 commit、push、merge 或修改 PR；所有 Git 操作由使用者執行。

## 風險

風險等級：standard

變更集中在測試啟動、測試 fixtures、package exclusion、文件與知識，不觸及使用者 runtime；但 runner 若吞掉 child failure、找不到測試卻回零，或平台 skip 過寬，會製造假綠，因此維持 standard risk。緩解方式是 explicit argv、deterministic sort、zero-test fail-closed、單元回歸、Windows 真實 launcher matrix、POSIX hosted observation、standard profile 與 `git diff --check`。變更可藉回復 script／fixtures／文件完整還原，無資料 migration、security downgrade、public-contract migration 或付費服務。

## Profile 補充

- Expected：Node 20/22 在 Ubuntu／Windows 執行同一組 Extension unit tests；Python 3.11–3.14 在三 OS 執行完整 suite，Windows-only launcher 在 Windows 實跑、非 Windows 具名 skip。
- Actual：Node 20 把 glob 當成字面路徑；八個 POSIX Python cells 因 executable alias、Windows 假路徑與無平台條件的 Windows launcher methods 固定失敗。
- Deterministic reproduction：GitHub Actions run `32218573938`；Node 20 兩格同一步失敗，八個 POSIX Python cells 同五項失敗，Windows／Node 22 對照組通過。
- Root cause：測試啟動與 fixture 對 Node 22 glob、Windows path alias、Windows shell 可用性做了未宣告假設；production security semantics 並非根因。
- 已確認 material decisions：直接補進 PR #1；使用新 standard-risk bug Work Item；G3 前先取得 hosted 17/17；由使用者分兩階段 commit/push；無 waiver。

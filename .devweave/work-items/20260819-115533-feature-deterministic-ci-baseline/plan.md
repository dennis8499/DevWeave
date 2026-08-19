# 執行計畫：建立公開跨平台 deterministic CI baseline

<!-- DEVWEAVE:artifact=plan version=1 work=20260819-115533-feature-deterministic-ci-baseline -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 建立 Public CI 與 Doctor characterization red seam

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, NFR-001, NFR-002, NFR-003, NFR-005, AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, DEC-001, DEC-002, DEC-003, DEC-004
- Inputs: 已核准 G1 artifacts、`tests/test_repository_contract.py`、現行 Doctor JSON contract、三個核准 action SHA；`.github/workflows/ci.yml` 尚不存在。
- Output: 新增 stdlib job-block helper／Public CI contract test；Doctor test 在 Windows 驗證真實 probe、非 Windows 驗證精確 skip detail。先不新增 workflow，使新 CI contract 產生可歸因的 red evidence，既有 Doctor assertions 維持通過。
- Verification: 透過 DevWeave controlled `unit-tests-contract` 先以 nonzero expectation 記錄「缺少 `.github/workflows/ci.yml`」的 red，再確認 failure 不是既有 contract regression。
- Dependencies: none

## TASK-002: 實作最低權限的跨平台 CI workflow

- Traces: REQ-001, REQ-002, REQ-003, REQ-004, NFR-001, NFR-002, NFR-005, AC-001, AC-002, AC-003, AC-004, AC-005, DEC-001, DEC-002, DEC-003, DEC-005
- Inputs: TASK-001 red contract、`vscode-extension/package.json`／lockfile、核准 OS/runtime matrices 與完整 action SHA。
- Output: `.github/workflows/ci.yml`；單一 workflow 具 Python/Node/hygiene jobs、exact triggers、`contents: read`、安全 checkout、完整 SHA、`fail-fast: false` 與核准 commands；無 secrets、smoke、package、release 或 deployment。
- Verification: DevWeave controlled `unit-tests-contract` zero-only 通過；人工檢視 workflow diff 確認 12+4+1 cells、command order、無浮動 refs、無 `continue-on-error`／write permission。
- Dependencies: TASK-001

## TASK-003: 文件化本機等價命令與 CI 支援邊界

- Traces: REQ-006, NFR-003, NFR-004, AC-007, AC-008, DEC-002, DEC-005
- Inputs: TASK-002 workflow、既有 README 驗證章節、Windows release certification baseline。
- Output: 先新增 README contract assertions 並觀察缺少 badge／POSIX／Node／caveat 的 red，再更新 README 標題與驗證章節，加入 CI badge、PowerShell/POSIX Python+hygiene、Node `npm ci`/typecheck/test/build、本機與 hosted matrix 說明及 release certification caveat。
- Verification: `unit-tests-contract` 由 red 回到 zero-only green；檢查 badge URL 指向 `ci.yml`，所有文件命令與 workflow/package scripts 一致。
- Dependencies: TASK-002

## 驗證策略

- **TDD targeted**：TASK-001 先執行 `unit-tests-contract` nonzero expectation，failure 只來自缺少 workflow；TASK-002、TASK-003 各自以相同 command zero-only 收綠。任何意外既有 failure 先停止診斷，不用寬鬆 assertion 掩蓋。
- **Python regression**：透過 G2 frozen verification plan 執行 contract、CLI、core、guard、knowledge 等 required Python commands；另以完整 stdlib discovery 核對 3.11+ 相容 surface。Windows symlink privilege 若不可用，只接受既有具名 skip。
- **Extension regression/build**：執行 `npm ci`、既有 Extension tests、typecheck 與 `npm run build`；因 Extension source/manifest 未變，不執行 smoke、package、VSIX release。若 managed command policy 不允許未設定的 direct build，保留 pre-G1 clean baseline 與 workflow contract，且不以 package command擴張 scope。
- **Hygiene/security**：`git diff --check`、完整 diff/scope review、搜尋浮動 action refs、`secrets.`、write permissions、`persist-credentials: true`、`continue-on-error`、smoke/package/release/deploy 字樣。
- **Manual acceptance**：確認 job/check names 可辨識 OS/runtime/stage；README 命令可複製；CI matrix 與 Windows release certification 沒有混稱。首次 hosted run 由人類 push／PR 後確認，Codex 不操作 remote。
- **G3 Knowledge Review**：選擇 promote；規劃 upsert `wiki/modules/public-ci.md`、刷新 `wiki/overview.md` 與 `wiki/architecture/devweave-knowledge-workflow.md`，同步 index/log/seal。Public CI module sources 限定 `.github/workflows/ci.yml`、`tests/test_repository_contract.py`、`README.md`、`vscode-extension/package.json`。

## 基線更新計畫

- 只更新 `.devweave/baseline/quality.md`：新增 Public CI quality attribute、exact matrices、least-privilege/action-pin contract、capability skip truth、本機／hosted verification 邊界與 final command results。
- 不更新 product 或 architecture baseline：P0-00 不新增 runtime capability或架構 provider abstraction；持久架構說明由受控 Wiki promotion 承擔。
- Baseline 與 Wiki 在 verification/G3 才寫入；implementation 階段保持唯讀。Final acceptance 必須列出實際通過/跳過數、未執行項目的理由與首次 GitHub hosted run 尚待人類 push 的外部缺口，不使用 waiver 假裝遠端結果已存在。

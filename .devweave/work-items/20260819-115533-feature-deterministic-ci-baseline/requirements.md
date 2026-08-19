# 需求與驗收條件：建立公開跨平台 deterministic CI baseline

<!-- DEVWEAVE:artifact=requirements version=1 work=20260819-115533-feature-deterministic-ci-baseline -->
## 假設與限制

- GitHub 預設分支為 `master`，repository 維持 public，使用 GitHub-hosted standard runners；不啟用 larger runner、自架 runner 或付費 Codex／LLM job。
- `vscode-extension/package-lock.json` 是 Node dependency 的唯一 lockfile；CI 必須使用 `npm ci`，不得在 job 中改寫 lockfile。
- 官方 Actions pin 採 2026-08-19 已核對的版本與完整 SHA：`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`（v7.0.1）、`actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97`（v7.0.0）、`actions/setup-node@820762786026740c76f36085b0efc47a31fe5020`（v7.0.0）。
- Python jobs 使用 repository 既有 stdlib suite；Node jobs 只使用既有 `typecheck`、`test`、`build` scripts。不加入 smoke、package 或 release。
- 首次遠端 Actions 結果只能在人類 push／建立 PR 後確認；Agent 不建立 branch、commit、push、PR 或 repository settings。
- 既有 Windows release certification 不因跨平台 CI 自動擴張；CI pass 代表開發合約通過，不代表所有組合已完成正式發行認證。
- 已確認的 material decisions：只實作 P0-00、standard risk、Python 三 OS、Node Windows／Ubuntu、Actions v7 完整 SHA、無 smoke／package／release／Codex API。無 waiver。

## 需求與驗收條件

## REQ-001: PR 與 master push 提供公開 checks
- Priority: must
- Acceptance: AC-001, AC-004
- Description: Repository 必須有單一公開 CI workflow；每次 pull request 與每次推送至 `master` 都啟動具名 Python、Node 與 hygiene checks，matrix 不因第一個失敗而取消其餘組合。

## REQ-002: Python 跨平台版本矩陣
- Priority: must
- Acceptance: AC-002
- Description: Python check 必須在 Ubuntu、Windows、macOS 的 GitHub-hosted standard runner 上，分別執行 Python 3.11、3.12、3.13、3.14 的完整 `unittest discover` suite。

## REQ-003: Node LTS 開發合約矩陣
- Priority: must
- Acceptance: AC-003
- Description: Node check 必須在 Ubuntu、Windows 的 Node 20、22 組合中，於 `vscode-extension` 依序執行 `npm ci`、`npm run typecheck`、`npm test`、`npm run build`。

## REQ-004: Repository hygiene check
- Priority: must
- Acceptance: AC-004
- Description: Workflow 必須在乾淨 checkout 上執行 `git diff --check`，whitespace error 必須使 check 失敗。

## REQ-005: CI 與 capability contract 可由本機測試固定
- Priority: must
- Acceptance: AC-005, AC-006
- Description: Repository contract tests 必須能在不呼叫 GitHub API 的情況下，拒絕遺失或被弱化的 workflow trigger、matrix、action pin、安全權限、命令與 capability truth；Windows Doctor fixture 要實際驗證 launcher，非 Windows 必須驗證明確 skip reason 而非冒充 Windows 認證。

## REQ-006: 維護者可執行本機等價驗證
- Priority: must
- Acceptance: AC-007
- Description: README 必須顯示 CI badge，並提供 PowerShell 與 POSIX 的 Python／hygiene 命令、Node install／typecheck／unit／build 命令及 CI 與 release certification 的差異。

## NFR-001: CI 採最低權限與安全 checkout
- Priority: must
- Acceptance: AC-005
- Description: Workflow top-level permissions 必須只有 `contents: read`；checkout 必須設定 `persist-credentials: false`；job 不得接收 repository secrets、API key 或 write permission。

## NFR-002: 第三方 Actions 與 dependency resolution 可重複
- Priority: must
- Acceptance: AC-003, AC-005
- Description: `checkout`、`setup-python`、`setup-node` 必須以已核對的完整 commit SHA 固定並附版本註解；Node dependency 必須使用 committed lockfile 與 `npm ci`，不得使用浮動 action tag 或 `npm install`。

## NFR-003: Capability 與認證敘述必須誠實
- Priority: must
- Acceptance: AC-006, AC-007
- Description: Unsupported OS／capability 必須以 `supported=false` 或包含平台原因的明確 skip reason 表達；跨平台 CI pass 不得被描述成正式 release certification。

## NFR-004: 既有行為與範圍保持相容
- Priority: must
- Acceptance: AC-008
- Description: P0-00 不得改變 DevWeave lifecycle、CLI、Guard、command policy、state/evidence semantics 或 Extension runtime；既有 Python 與 Extension tests 必須維持通過，變更路徑不得超出核准 scope、G3 baseline 與 Knowledge plan。

## NFR-005: 失敗訊號清楚且不隱藏矩陣結果
- Priority: should
- Acceptance: AC-001, AC-002, AC-003, AC-004
- Description: Python 與 Node matrices 必須設定 `fail-fast: false`，job／step 名稱須能從 GitHub checks 判讀 OS、runtime version 與失敗階段；不得以 `continue-on-error` 隱藏失敗。

## AC-001: Workflow trigger 與 check 可見性
- Requirement: REQ-001, NFR-005
- Scenario: Given repository contract 讀取 `.github/workflows/ci.yml`，When 檢查 workflow，Then 它只對 `pull_request` 與 `push` 到 `master` 自動觸發，且存在 Python、Node、hygiene 三類具名 checks，兩個 matrix 均為 `fail-fast: false` 且沒有 `continue-on-error`。

## AC-002: Python matrix 完整執行既有 suite
- Requirement: REQ-002, NFR-005
- Scenario: Given workflow contract，When 展開 Python strategy，Then runner 集合精確包含 `ubuntu-latest`、`windows-latest`、`macos-latest`，Python 集合精確包含 `3.11`、`3.12`、`3.13`、`3.14`，每個組合都執行 `python -B -m unittest discover -s tests -v`。

## AC-003: Node matrix 完整執行既有 scripts
- Requirement: REQ-003, NFR-002, NFR-005
- Scenario: Given workflow contract 與 `vscode-extension/package.json`，When 展開 Node strategy，Then runner 集合精確包含 `ubuntu-latest`、`windows-latest`，Node 集合精確包含 `20`、`22`，且每個組合在 `vscode-extension` 依序成功執行 `npm ci`、`npm run typecheck`、`npm test`、`npm run build`。

## AC-004: Hygiene check 會阻擋 whitespace error
- Requirement: REQ-001, REQ-004, NFR-005
- Scenario: Given workflow checkout，When `git diff --check` 回傳非零，Then hygiene check 失敗；正常 repository 則回傳零，且失敗不被忽略。

## AC-005: Workflow 供應鏈與權限 contract
- Requirement: REQ-005, NFR-001, NFR-002
- Scenario: Given repository contract tests，When workflow 遺失、permission 超過 `contents: read`、checkout 持久化 credentials、action 不是三個核准完整 SHA、matrix／trigger／commands 被縮減，Then 測試必須失敗；核准 workflow 則通過。

## AC-006: Doctor 不把 unsupported capability 假裝成 green certification
- Requirement: REQ-005, NFR-003
- Scenario: Given repository Doctor fixture，When 測試在 Windows 執行，Then 它實際驗證 `py-3`、`cmd`、`powershell`、`pwsh`、`hook-schema`、`launcher-probe`；When 在非 Windows 執行，Then Windows-only checks 仍明確標示成功的 prerequisite skip，detail 必須包含非 Windows／Windows-only 原因，不能宣稱真實 launcher 已通過。

## AC-007: README 提供 badge、本機命令與支援邊界
- Requirement: REQ-006, NFR-003
- Scenario: Given 新貢獻者閱讀 README，When 查看標題與驗證章節，Then 可看到連到 `ci.yml` 的 CI badge、PowerShell／POSIX Python 與 `git diff --check`、Node `npm ci`／typecheck／test／build，以及「CI 開發矩陣不等於正式 release certification」的明確說明。

## AC-008: 現有回歸與 scope 保持通過
- Requirement: NFR-004
- Scenario: Given 完成後的核准 diff，When 執行既有完整 Python suite、Extension `npm ci`／typecheck／unit／build 與 `git diff --check`，Then 全部成功（平台權限造成的既有具名 skip 可保留），且 product diff 只落在 `.github/workflows/ci.yml`、`README.md`、`tests/test_repository_contract.py`；其餘只允許 G3 核准的 quality baseline、DevWeave artifacts 與 Knowledge promotion targets。

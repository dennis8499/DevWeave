# 系統設計：建立公開跨平台 deterministic CI baseline

<!-- DEVWEAVE:artifact=design version=1 work=20260819-115533-feature-deterministic-ci-baseline -->

## 設計摘要

採用一個 `.github/workflows/ci.yml` 作為 **Public CI Workflow Module**。它對 GitHub 提供很小的 **Interface**：兩種事件入口（所有 pull request、`master` push）以及三類可觀察 checks（Python、Node、hygiene）；其內部隱藏 12 個 Python matrix cells、4 個 Node matrix cells、dependency bootstrap 與逐步失敗處理。這個 **Seam** 位於 repository 內的 declarative workflow 與 GitHub-hosted runner 之間，不新增第二種 CI provider，因此不建立假想 Adapter。

`tests/test_repository_contract.py` 是本機 **Contract Observer Module**。它的 Interface 仍是既有 stdlib `unittest`，在不呼叫 GitHub API、不引入 YAML dependency 的前提下，從 workflow/README bytes 驗證公開契約。測試以 top-level／job block locality 限制 assertions，避免某個 job 的 action、matrix 或 command 文字替另一個 job 誤通過。這個小測試介面同時約束 trigger、權限、pin、matrix、命令與文件，提供高 **Depth** 與跨後續 P0 工作的 **Leverage**。

關鍵不變量：

1. 自動 trigger 只有所有 `pull_request` 與 `push.branches: [master]`。
2. Workflow top-level permission 只有 `contents: read`；每次 checkout 都是 `persist-credentials: false`，不注入 secrets。
3. 三個官方 Actions 只使用核准的完整 commit SHA，版本只放在人類可讀註解。
4. Python/Node matrix 精確符合 G1；兩者 `fail-fast: false`，沒有 `continue-on-error`。
5. Python 只跑現有 stdlib suite；Node 只跑 lockfile install、typecheck、unit test、build，不跑 smoke/package/release。
6. CI 執行不改寫 repository、DevWeave machine ledger 或產品 runtime semantics；build output 只存在 runner workspace。
7. CI matrix pass 是開發合約證據，不自動擴張 Windows release certification。

## 選項比較

### Workflow 佈局

- **選定：單一 workflow、三個專責 jobs。** Python 與 Node 各自矩陣化，hygiene 獨立；check 名稱可直接定位 OS/runtime/stage，dependency 只在需要它的 job 安裝。
- **拒絕：單一 giant cross-product job。** 會把 Python OS/version 與 Node OS/version 做不必要的笛卡兒積，增加 runner 使用量，且失敗訊號混雜。
- **拒絕：Python、Node、hygiene 各一個 workflow。** 觸發與權限政策會複製三次，增加 drift 面積，也讓 badge 與 branch protection check 集合較難理解。

### Contract 驗證

- **選定：Python stdlib text/block contract。** 先確認檔案存在，再以 UTF-8/universal-newline 讀取；extract job-local block 後檢查 exact triggers、matrix lists、commands、SHA、permission 與 credential 設定。符合 repository 的 dependency-free 品質基線。
- **拒絕：加入 PyYAML、actionlint 或自製完整 YAML parser。** P0-00 不值得增加 runtime/tool supply-chain 與 lockfile；自製 parser 會把 CI 工作擴張成 parser 維護工作。
- **拒絕：只等 GitHub 遠端執行。** 無法在 workflow 被刪除、權限放寬或 matrix 被縮減時提供本機 deterministic red signal。

### Actions 版本與認證範圍

- **選定：核准 v7 releases 的完整 SHA + 版本註解。** 同時保有 immutable execution bytes 與維護者可讀性。
- **拒絕：`@v7`／`@main` 浮動 ref。** 上游 ref 可移動，無法重現相同執行內容。
- **拒絕：把 CI pass 改寫成跨平台 release certification。** CI 只觀測 development contract；正式 release 仍有不同的 host、VS Code 與 smoke/package 條件。

## 介面與資料流

### Public CI Workflow Module

- **Interface**：GitHub event、job/check name、success/failure conclusion；呼叫者不需要知道 matrix 展開細節。
- **Configuration**：`pull_request`、`push`/`master`、`contents: read`、runner/runtime lists、固定 action SHA、固定 commands。
- **Ordering**：每個 job 先安全 checkout，再 setup runtime，再按核准順序執行；Node 的 `npm ci` 必須先於 typecheck/test/build。
- **Error modes**：任何 step 非零即使該 matrix cell 失敗；其他 cells 因 `fail-fast: false` 繼續，沒有 error suppression。
- **Performance**：最多 12 個 Python、4 個 Node、1 個 hygiene job；是否平行與排隊由 GitHub-hosted runner 管理，不在 repository 建立自訂 scheduler。

資料流：

```text
pull_request 或 master push
  -> immutable checkout（無持久化 credentials）
  -> setup-python / setup-node（完整 SHA）
  -> repository tests / extension scripts / git diff --check
  -> 各 matrix cell 的 GitHub check conclusion
```

Python tests 只在 fixture／temporary directory 內建立測試資料；Node build 可寫 runner 的 `vscode-extension/dist`，但 workflow 不 commit、upload、release 或部署。沒有 secrets、Codex API、repository write token或 machine-ledger state transition。

### Contract Observer Module

- **Interface**：`RepositoryContractTests` 的測試結果。
- **Seam**：以 `Path.read_text(encoding="utf-8")` 讀 workflow 與 README；workflow job extractor 只接受 canonical two-space job indentation，將 Python、Node、hygiene assertions 保持 local。
- **Implementation**：檢查 exact trigger fragment、top-level permission、每個 job 的 matrix/commands、三個 action SHA、每次 checkout 的 `persist-credentials: false`、沒有 forbidden floating ref／`continue-on-error`／secret expression。
- **Doctor test surface**：Windows 分支要求六個 capability checks 存在、`ok` 且 detail 不是 skip；非 Windows 分支要求同六項的 detail 精確等於現行 Windows-only skip reason。產品 Doctor 實作不變。
- **README test surface**：badge 指向 `actions/workflows/ci.yml`，且驗證章節含 PowerShell、POSIX、Node 等價命令與 certification caveat。

### 相容性

- Python code 與 tests 維持 3.11+ stdlib-only；workflow 版本字串加引號，避免 YAML 把 `3.11` 等值轉成數字。
- Node 只使用 committed lockfile 與現有 scripts；不變更 package manifest、Extension source 或 VSIX artifacts。
- GitHub Actions 是唯一實作，沒有第二個真實 provider，依 codebase-design 原則不引入 Adapter。

## 失敗模式與回復

- **Workflow syntax／contract 錯誤**：本機 contract 可攔截既知結構與安全 drift；stdlib text check 不是完整 YAML parser，未知語法錯誤仍由首次 GitHub run 顯示，這是保留的 residual risk。
- **單一 OS/runtime 回歸**：具名 matrix check 只標紅該 cell；`fail-fast: false` 保存其餘結果供比較，不降級成 green。
- **Dependency／Action failure**：`npm ci`、setup action 或測試非零直接使 job 失敗，不 retry、不 `continue-on-error`、不切換浮動版本。
- **Unsupported Windows capability**：Windows runner 必須真實 probe；非 Windows 只允許精確、明確的 skip detail。若產品行為退化成模糊 green，repository contract 失敗。
- **供應鏈更新**：任何 action SHA 或 Node lockfile 更新都必須是後續受 review 的 repository change；本 workflow 不自行追最新版。
- **Runner 消耗**：限定 17 個 standard-runner jobs，沒有 schedule、macOS Node、larger runner 或重試 fan-out；公開 repository 不引入額外付費服務。
- **回復**：回復 `.github/workflows/ci.yml`、README 與 contract test，並在尚未 close 時透過 DevWeave revise／重新驗證；G3 的 quality/Wiki 更新同步回復。無資料 migration、schema rollback 或 runtime feature flag。
- **觀測**：GitHub checks 顯示 job／OS／version／step；本機 targeted contract 與完整 regression 提供 merge 前證據。首次遠端 run 由人類 push／PR 後確認，Agent 不操作 Git remote。

## 高風險分析

本工作項為 standard risk，不涉及資料 migration、production rollout、credential storage 或 irreversible operation，因此 high-risk migration／independent review 不適用。仍採高敏感度 CI 安全處理：read-only token、credential 不持久化、完整 SHA、無 secrets／Codex API、無 repository-controlled write token。

相容性風險集中在三個 runner OS 與 Python/Node versions，由 matrix 直接觀測；performance/cost 以 17 個無 schedule 的 standard jobs 為上限。完整 YAML semantic validation與首次 hosted-run 成功仍需 GitHub 外部觀測，但不以 waiver 假裝已驗證。

## 設計決策

## DEC-001: 單一 workflow 拆分三個專責 jobs
- Requirements: REQ-001, REQ-002, REQ-003, REQ-004, NFR-005
- Decision: 使用單一 `ci.yml`，拆成 Python、Node、hygiene 三個 jobs；兩個 matrix 均 `fail-fast: false`，check name 含 OS/runtime。
- Rationale: 以最小 policy surface 提供清楚 failure locality，避免 giant cross-product 與多 workflow drift。
- Consequences: PR 最多出現 17 個 checks/cells；結果完整但可能比 fail-fast 使用較多 standard runner minutes。

## DEC-002: 以 stdlib job-local contract 固定 workflow
- Requirements: REQ-005, NFR-002, NFR-004
- Decision: 在既有 `RepositoryContractTests` 以 UTF-8 text 與 canonical indentation job blocks 驗證 workflow，不加入 YAML parser 或外部 linter。
- Rationale: 保持 Python stdlib-only，且讓 trigger/matrix/security drift 在本機立即 red。
- Consequences: 測試對刻意的 workflow 格式重排較敏感；完整 YAML semantic 錯誤仍以 GitHub hosted run 作外部 oracle。

## DEC-003: CI 供應鏈採完整 SHA 與最低權限
- Requirements: NFR-001, NFR-002, AC-005
- Decision: top-level 只給 `contents: read`；checkout 不持久化 credentials；checkout/setup-python/setup-node 使用 G1 核准完整 SHA，job 不使用 secrets。
- Rationale: Workflow 會執行 repository-controlled code，必須降低 token 與 upstream ref 風險。
- Consequences: Action 升級需顯式受 review 變更；未來若 job 真需要其他權限，必須 revise 而不能暗中放寬。

## DEC-004: Capability truth 由同一 Doctor JSON interface 分平台驗證
- Requirements: REQ-005, NFR-003, AC-006
- Decision: 不改 Doctor implementation；只讓 contract test 在 Windows 驗證真實 probe detail，在非 Windows 驗證精確 Windows-only skip detail。
- Rationale: 現行產品行為已正確，增加測試即可封住「skip 冒充認證」的回歸，避免多餘 runtime 變更。
- Consequences: 各 CI OS 都能驗證自己的真實分支；如果 skip 文案契約變更，測試與文件需一起受 review 更新。

## DEC-005: Build 與 release certification 明確分離
- Requirements: REQ-003, REQ-006, NFR-003, NFR-004
- Decision: Node CI 只做 `npm ci`、typecheck、unit、build；README 明確說明這不是 smoke/package/release certification。
- Rationale: P0-00 要建立 development baseline，不應順帶擴張發行流程或產生 artifacts。
- Consequences: CI 能阻止編譯／單元回歸，但 VSIX host activation 與發行交易仍由既有 release verification 負責。

## DEC-006: G3 提升公開 CI durable knowledge
- Requirements: REQ-006, NFR-004, AC-007, AC-008
- Decision: Verification 更新 quality baseline，新增 `wiki/modules/public-ci.md`，刷新 `wiki/overview.md` 與 `wiki/architecture/devweave-knowledge-workflow.md`，再由 engine 同步 index/log/seal。
- Rationale: 公開 CI 是後續 P0 共用的長期開發契約，不應只存在 workflow bytes；README 變更也使兩個既有 source-bound pages 受影響。
- Consequences: 三個 content targets 在五頁上限內；Wiki 在 verification 前保持唯讀，任何計畫外頁面都阻擋 G3。

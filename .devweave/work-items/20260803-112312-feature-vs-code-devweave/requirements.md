# 需求與驗收條件：空白 VS Code 專案初始化產生 DevWeave 流程內容

<!-- DEVWEAVE:artifact=requirements version=1 work=20260803-112312-feature-vs-code-devweave -->

## 假設與限制

1. 目標 workspace 是已由 VS Code 開啟的 Git repository；Extension 不負責建立 Git。
2. Extension VSIX 會攜帶與目前 engine 版本相符的 runtime manifest、skill、references、
   assets 與 hook template；不從網路下載資產。
3. 「空白／未初始化」以 `.devweave/project.json` 不存在為主要判定；若檔案已存在但
   格式錯誤或部分內容衝突，視為 diagnostic/conflict，不自動修復。
4. 初始化完成後，DevWeave engine 執行仍遵守既有 Python 3.11+、Git、Codex hook trust
   與三道 gate 的 repository contract；本 feature 只移除手動安裝與初始化步驟。
5. 所有會造成 repository 寫入的動作都必須由使用者在 Extension UI 明確確認；背景
   refresh、activation 與既有 managed workspace 不可觸發 bootstrap。

## 需求與驗收條件

## REQ-001: 空白 workspace 顯示可執行的初始化入口

- Priority: must
- Acceptance: AC-001
- Description: 當 workspace 尚未有 `.devweave/project.json` 時，Extension activation
  與 Control Center 必須辨識 `Not initialized`，顯示「Initialize DevWeave」入口，並
  提供目前會建立的內容摘要與明確確認動作；不得只顯示複製 Codex prompt。

## REQ-002: Extension 可獨立完成完整 bootstrap

- Priority: must
- Acceptance: AC-002
- Description: 使用者確認後，Extension 必須只透過 VS Code workspace filesystem API
  將 VSIX 內建資產與產生內容寫入 workspace，建立執行 DevWeave 所需的
  `.agents/skills/devweave/`、`.codex/hooks.json`、`.devweave/project.json`、baseline、
  work-item/cache 目錄與 root Wiki starter；流程不得要求 Codex Chat、手動 Python CLI、
  網路或外部 process 才能完成初始化。

## REQ-003: 初始化成功後呈現可用狀態

- Priority: must
- Acceptance: AC-003
- Description: bootstrap 完成後，Extension 必須重新讀取 workspace snapshot，顯示
  `projectExists: true`、`managed: true`、skill/hook present，清除 `project_missing`，
  並將下一步導向既有 DevWeave workflow；初始化結果需列出建立、採用或跳過的路徑。

## REQ-004: 既有內容採用與衝突 fail closed

- Priority: must
- Acceptance: AC-004
- Description: 對已存在且內容與目前 bundled asset 相同的檔案，初始化必須採用且不產生
  實質 byte 變更；遇到內容不一致、manifest 缺失或寫入失敗時，必須停止剩餘有風險的
  寫入、保留既有 bytes，逐一回報 conflict/error path，且不可宣稱初始化成功。

## NFR-001: 非破壞、冪等與可回復

- Priority: must
- Acceptance: AC-004
- Description: 初始化只能寫入固定 allowlist 內、原本不存在或已驗證相容的目標；重複執行
  不得覆寫使用者檔案或產生內容漂移，錯誤時提供可理解的下一步，不刪除既有資料。

## NFR-002: workspace path 與供應鏈安全

- Priority: must
- Acceptance: AC-005
- Description: installer 必須拒絕 absolute/traversal/symlink escape 及 manifest 外路徑，
  不接受使用者輸入作為任意 destination，不執行 shell/Python/Git/network；VSIX 內建資產
  必須以版本化 manifest/完整性檢查與安全測試固定來源。

## NFR-003: package completeness 與跨平台可測試性

- Priority: must
- Acceptance: AC-006
- Description: production VSIX 必須包含初始化所需的全部 runtime 資產；installer 透過
  可替換的 filesystem port 測試，且 Windows/macOS/Linux 的 workspace-relative path
  結果一致，不依賴實際 shell 或平台特定路徑。

## REQ-005: 既有 managed workspace 行為相容

- Priority: must
- Acceptance: AC-007
- Description: 當 `.devweave/project.json` 已存在且能被 snapshot reader 讀取時，Extension
  必須維持現有唯讀 dashboard、Codex prompt composer、gate 與 work-item projection；
  初始化入口不得取代或自動重建既有 managed repository。

## AC-001: 未初始化 workspace 顯示初始化入口

- Requirement: REQ-001
- Scenario: Given VS Code 開啟一個沒有 `.devweave/project.json` 的 workspace，When Extension
  activation 或使用者開啟 Control Center，Then 顯示 `Not initialized` 與「Initialize DevWeave」
  按鈕，並顯示將安裝的 runtime/project/Wiki 內容摘要；頁面不可只提供 `Copy initialization prompt`。

## AC-002: 使用者確認後完成完整 bootstrap

- Requirement: REQ-002
- Scenario: Given AC-001 的 workspace 且 VSIX runtime manifest 完整，When 使用者確認初始化，
  Then installer 不呼叫 Codex Chat、Python CLI、shell、Git 或 network，並在 workspace 建立
  `.agents/skills/devweave/`、`.codex/hooks.json`、`.devweave/project.json`、三份 baseline、
  `work-items/`、cache 目錄與 `wiki/index.md`、`wiki/overview.md`、`wiki/log.md` 及類別目錄。

## AC-003: 成功狀態可供後續流程使用

- Requirement: REQ-003
- Scenario: Given AC-002 的寫入全部成功或被判定為相容採用，When installer 完成並刷新，
  Then snapshot 顯示 project 存在且 managed 為 true、skill/hook 均 present、沒有
  `project_missing`，並提供既有 `$devweave new/feature/refactor/bug` workflow 的下一步提示。

## AC-004: 相容、重複與衝突行為可預測

- Requirement: REQ-004, NFR-001
- Scenario: Given 目標已有相同 bundled bytes 或已存在的使用者檔案，When 初始化一次或再次執行，
  Then 保留既有 bytes、回報 adopted/skipped 且結果冪等；Given 任一受保護目標內容衝突，When
  初始化，Then 停止後續高風險寫入、回報 exact path 與 conflict，且 snapshot 不宣稱 managed
  bootstrap 成功。

## AC-005: 受限寫入與資產完整性

- Requirement: NFR-002
- Scenario: Given installer 收到任何不在固定 manifest 的 path、absolute/traversal path、
  symlink escape 或不完整資產，When 執行 bootstrap，Then 拒絕該操作、完全不執行外部 process、
  回報安全/manifest diagnostic，且不將檔案寫到 workspace root 以外。

## AC-006: VSIX 與跨平台測試覆蓋

- Requirement: NFR-003
- Scenario: Given production package build，When 檢查 VSIX 與以 memory filesystem 執行
  installer tests，Then 每個 manifest target 都存在且可讀，Windows-style 與 POSIX-style
  relative paths 產生相同 targets，unit/typecheck/package/smoke checks 均通過。

## AC-007: 既有 managed workspace 不受影響

- Requirement: REQ-005
- Scenario: Given 已有合法 `.devweave/project.json`、work item 與 Wiki 的 repository，When
  Extension refresh 或開啟 Control Center，Then 保持既有 dashboard projection、唯讀檔案開啟、
  prompt preview/copy 與 mutation-blocking diagnostics 行為，不自動執行 bootstrap。

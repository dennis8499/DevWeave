# 功能驗收：空白 VS Code 專案初始化產生 DevWeave 流程內容

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260803-112312-feature-vs-code-devweave -->

## 驗證矩陣

所有 current evidence 的 source fingerprint 為
`ae62d5568db2a93f2ef457e8044ff5df4c5128158cf998c09cef68e94a66b9fe`。

| Acceptance | 驗證結果 | Tasks / Evidence |
| --- | --- | --- |
| AC-001 未初始化顯示入口與內容摘要 | 通過：Webview 顯示 `Not initialized` 與 `Initialize DevWeave`；Command Palette 有 `devweave.initialize`；smoke 與 UI/security regression 通過。 | TASK-003/TASK-004 · EVID-002, EVID-003, EVID-007 |
| AC-002 確認後完成完整 bootstrap | 通過：production bundle 具 15 directories、40 files（含 32 skill files）；installer 透過 VS Code filesystem seam 寫入 hook、project、baseline、cache/work-items 與 Wiki starter；23 個 Extension tests 通過。 | TASK-001/TASK-002/TASK-003 · EVID-001, EVID-004, EVID-006, EVID-007 |
| AC-003 成功後刷新可用狀態 | 通過：controller 在 install 後 refresh snapshot，Webview 顯示 bootstrap report；既有 snapshot、Extension Host smoke 與 regression 通過。 | TASK-003 · EVID-002, EVID-003, EVID-006 |
| AC-004 相容、冪等、衝突與 rollback | 通過：same-byte adopted、conflict fail closed、malformed/hash/path/symlink rejection、write-failure rollback 與 date transform 均有 regression coverage；不覆寫既有 bytes。 | TASK-002 · EVID-003, EVID-006, EVID-007 |
| AC-005 受限寫入與資產完整性 | 通過：manifest destination/source containment、duplicate/type/ancestor 檢查、SHA-256/byte length 驗證與 no-process/network security checks 通過。 | TASK-001/TASK-002/TASK-004 · EVID-001, EVID-003, EVID-004, EVID-007 |
| AC-006 VSIX 完整性與跨平台測試 | 通過：production package 成功；40 個 source hash/length 全數匹配；Windows/POSIX relative path regression、typecheck、smoke 與 root suite 通過。 | TASK-001/TASK-002/TASK-004 · EVID-001, EVID-002, EVID-004, EVID-005, EVID-006 |
| AC-007 managed workspace 相容 | 通過：合法既有 project 不進 installer；既有 snapshot/prompt/gate/Wiki projection、mutation blocking 與 root 62 tests 通過；initialize 只在 project missing 才要求確認。 | TASK-003/TASK-004 · EVID-002, EVID-003, EVID-005, EVID-006, EVID-007 |

## Profile 證據

- acceptance：EVID-001（production package）、EVID-002（VS Code Extension Host smoke）、EVID-004（TypeScript typecheck）。
- regression：EVID-003（既有 core/security tests）、EVID-005（root 62 Python tests）、EVID-006（Extension npm test 23/23，含 BootstrapInstaller）。
- high-risk review：EVID-007，檢查 bundle provenance、manifest/hash、path/symlink safety、preflight/rollback、native confirmation、managed compatibility 與 no-external-process invariant。
- 所有 evidence 均 `status=passed`、`binds_current_source=true`、`stale=false`；無 waiver。

## 基線更新

- 已透過 DevWeave baseline declaration 宣告並更新：
  - `.devweave/baseline/architecture.md`：新增 `BootstrapInstaller` deep module、VS Code filesystem adapter、source-derived manifest provenance、confirmation、managed compatibility 與 rollback boundary。
  - `.devweave/baseline/product.md`：接受 Extension 在空白 workspace 直接安裝完整 DevWeave bootstrap 的產品能力，並保留既有 workspace 相容行為。
  - `.devweave/baseline/quality.md`：接受 manifest integrity、path/symlink safety、idempotence、rollback、cross-platform path canonicalization 與 verification coverage。
- 三個 target 均有實際內容變更，未宣告 baseline path 為零。

## Wiki 知識提升

- Wiki 無變更：`knowledge status` 顯示 `affected_pages=[]`、`changed_paths=[]`、`pending_refresh=[]`，因此沒有建立空的 knowledge plan，也沒有修改 index/log 或 seal。
- 既有 `wiki/overview.md` placeholder 僅是 G1 已記錄的 unrelated warning；本 feature 的 product source scope 不提供該頁的新 source evidence，故保留 warning，不將其誤標為本次 affected page。

## 殘餘風險

- 未在真實外部空白 repository 以人工點擊 modal 完成一次端到端互動；本次以 memory filesystem installer regression、manifest hash/length audit、Extension Host smoke 與 root suite 驗證同一個 production seam。這是手動 acceptance coverage 的已知限制，不影響 automated current evidence。
- 已存在的 `project.json`、partial target 或內容 conflict 不做 migration/repair；使用者需依報告的 exact paths 人工處理，這是設計中的 fail-closed 行為。
- 產生 bootstrap bundle 需要在 repository checkout 執行 Extension package build；發布的 VSIX 會攜帶已產生的 `dist/bootstrap`，runtime 不下載資產。
- Waiver：無。

## 驗收結論

本 feature 已完成核准範圍：VS Code Extension 在空白 workspace 顯示直接初始化入口，經 native modal confirmation 後，使用內嵌且具 SHA-256/byte-length manifest 的 bundle，透過 VS Code workspace filesystem API 建立執行 DevWeave 所需的 skill、hook、project、baseline、cache/work-items 目錄與 Wiki starter。既有合法 workspace 維持原本唯讀 projection 與 Codex prompt workflow；相容內容只採用，衝突與錯誤 fail closed。

所有 high-risk configured verification commands、23 個 Extension unit/security tests、root 62 tests、manifest completeness/hash audit、cross-platform path regression、smoke 與獨立 review 均通過。基線更新已宣告且完成，Wiki 維持 read-only 並保留既有 placeholder warning。工作項可提交 G3 Acceptance review。

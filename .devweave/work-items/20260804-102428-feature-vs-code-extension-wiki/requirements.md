# 需求與驗收條件：修正 VS Code Extension 效能、Wiki 搜尋與完整初始化

<!-- DEVWEAVE:artifact=requirements version=1 work=20260804-102428-feature-vs-code-extension-wiki -->

## 假設與限制

- Wiki query 使用大小寫不敏感的包含式查詢，搜尋 title、path 與 body preview；不做 typo-tolerant fuzzy ranking。
- 使用者輸入期間不即時套用結果；按 Enter 才 commit query。分類變更與顯示全部可直接套用，但只能更新結果區。
- workspace watcher 保留自動 refresh；多事件需 debounce、single-flight，完成後最多再執行一次最新 pending refresh。
- bootstrap 只建立缺少的 non-conflicting files；不同 bytes 的既有檔案列 conflict 且不覆寫，允許其他缺檔建立，最終標示 partial。
- 使用手冊以 Extension-local bundle 提供，不寫入 target workspace；現有 0.1.0 VSIX 不覆寫，0.2.0 另行產出。

## 需求與驗收條件

## REQ-001: Wiki 搜尋維持穩定輸入與包含式匹配

- Priority: must
- Acceptance: AC-001, AC-002
- Description: 使用者輸入查詢時 input DOM、selection 與字元順序保持不變；按 Enter 後，以大小寫不敏感的包含式匹配搜尋標題、路徑與摘要，分類仍按 type 精確篩選。

## REQ-002: Webview 局部更新不重建無關 UI

- Priority: must
- Acceptance: AC-001, AC-003
- Description: Wiki query、分類、顯示全部與區域切換只更新必要的結果／區域；連續 local state updates 透過 render scheduler 合併，不能因搜尋操作重建整個 Knowledge section。

## REQ-003: Refresh 合併且不允許重疊 snapshot

- Priority: must
- Acceptance: AC-004, AC-005
- Description: watcher burst 與手動 Refresh 共用 single-flight coordinator；讀取進行中只保留最新 pending request，舊結果不得覆蓋較新的 snapshot。

## REQ-004: Snapshot 讀取可平行化但輸出穩定

- Priority: must
- Acceptance: AC-005, AC-006
- Description: 可獨立讀取的 filesystem data 以平行方式取得，work/page/evidence/diagnostic projection 仍依固定排序輸出，錯誤不因 concurrency 改變語意。

## REQ-005: Bootstrap 提供完整 DevWeave 控制套件

- Priority: must
- Acceptance: AC-007, AC-008
- Description: manifest 必須包含 `devweave`、五個核准 companion skills、通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter；不得包含產品 source、tests、fixtures、work/history 或 repository 使用文件落地檔。

## REQ-006: Bootstrap 支援安全部分修復

- Priority: must
- Acceptance: AC-009, AC-010, AC-011
- Description: project 已存在但控制套件不完整時，Extension 顯示補齊入口；installer 只建立缺檔，既有不同內容列 conflict 且永不覆寫，寫入失敗時回復本次建立的檔案。

## REQ-007: Dashboard 顯示 bootstrap completeness 與 embedded help

- Priority: must
- Acceptance: AC-012, AC-013
- Description: snapshot projection 能顯示缺少的 bootstrap control paths；Dashboard 提供懶載入的說明分頁，內容來自 bundled 使用手冊且不需 repository write 或 network。

## REQ-008: VSIX package 與 manifest 可驗證

- Priority: must
- Acceptance: AC-014
- Description: Extension version 與 bootstrap bundle 升至 0.2.0；build、manifest、VSIX inspection 能確認所有必要檔案存在且 integrity metadata 正確，保留既有 0.1.0 artifact。

## NFR-001: 互動效能與併發安全

- Priority: must
- Acceptance: AC-003, AC-004, AC-005, AC-006
- Description: 搜尋輸入不觸發全量 DOM replacement；watcher burst 不產生重疊 workspace scan；測試可 deterministic 驗證 render、讀取 concurrency 與 coordinator call count，不加入 production telemetry。

## NFR-002: 安全與相容性邊界

- Priority: must
- Acceptance: AC-010, AC-011, AC-015
- Description: 保持既有 path normalization、manifest hash validation、CSP、no process/network、preview-first public command 與 legacy snapshot projection 相容性。

## AC-001: Wiki 輸入不倒序

- Requirement: REQ-001, REQ-002
- Scenario: Given Knowledge section 已開啟，When 使用者連續輸入 `DevWeave`，Then input 顯示順序保持 `DevWeave`、焦點與游標不被重置，且尚未按 Enter 前不套用新 query。

## AC-002: Wiki 包含式查詢

- Requirement: REQ-001
- Scenario: Given 頁面 title 為 `Knowledge Engine` 且 path/body 含 `VSCode`，When 使用者以不同大小寫輸入 `engine` 或 `vscode` 並按 Enter，Then 對應頁面出現在結果；拼字錯誤不要求命中。

## AC-003: Webview 局部 render

- Requirement: REQ-002, NFR-001
- Scenario: Given 已載入 Wiki list，When 使用 query Enter、type change 或 show-all，Then 只更新結果／metric DOM seam，無關 header、input 與其他 section 不被重建。

## AC-004: Refresh burst 合併

- Requirement: REQ-003, NFR-001
- Scenario: Given 一次 snapshot read 尚未完成，When watcher 與手動 refresh 連續觸發多次，Then 同一時間最多一個 read，完成後至多再執行一次最新 pending request。

## AC-005: 最新 snapshot 優先

- Requirement: REQ-003, REQ-004
- Scenario: Given 兩次 refresh 的完成順序不同，When 較舊 request 晚於較新 request 完成，Then published snapshot 不得回退到較舊結果，且輸出排序維持 deterministic。

## AC-006: 平行讀取保持 projection contract

- Requirement: REQ-004, NFR-001
- Scenario: Given 包含多個 Wiki pages、work items、artifacts 與 evidence 的 fixture，When 讀取 workspace，Then 獨立 reads 可平行執行，結果與 baseline projection 完全相同，diagnostic order 穩定。

## AC-007: 空 workspace 完整 bootstrap

- Requirement: REQ-005
- Scenario: Given 空 workspace 且使用者確認初始化，Then 建立所有控制目標：AGENTS、skills lock、六組 skills、hook、project、三份 baseline、Wiki starter 與必要目錄，且不建立產品／history 檔案。

## AC-008: Manifest allowlist 完整

- Requirement: REQ-005, REQ-008
- Scenario: Given production build 完成，When 檢查 manifest 與 bundle entries，Then 五個 companion skill 的所有 source files、devweave files 與 control templates 都有 destination、byte length 與 SHA-256。

## AC-009: Partial bootstrap repair

- Requirement: REQ-006
- Scenario: Given 只有部分 DevWeave files 存在，When 使用者確認補齊，Then 建立所有缺少且無 conflict 的檔案，報告 repaired 或 partial，Dashboard 顯示剩餘缺口。

## AC-010: Conflict 不覆寫

- Requirement: REQ-006, NFR-002
- Scenario: Given 既有 AGENTS、project 或 skill file bytes 不同，When 執行補齊，Then 保留原 bytes、列出 conflict，其他安全缺檔仍可建立，且不宣稱 complete。

## AC-011: Bootstrap rollback

- Requirement: REQ-006, NFR-002
- Scenario: Given 某個缺檔寫入失敗，Then 本次已建立檔案回復、既有檔案不變，report 明確列出 errors 與 rolledBack。

## AC-012: Bootstrap completeness UI

- Requirement: REQ-007
- Scenario: Given snapshot 發現缺少 control paths，Then Dashboard 顯示補齊 CTA 與缺口，不把 project.json 存在誤判為完整初始化。

## AC-013: Embedded help

- Requirement: REQ-007
- Scenario: Given 使用者開啟說明分頁，Then Extension 顯示初始化、workflow、Wiki、Gate、companion 與安全邊界說明，內容來自 Extension bundle，workspace 無新增文件且無 network request。

## AC-014: Versioned package verification

- Requirement: REQ-008
- Scenario: Given 執行 package 與 VSIX inspection，Then 產出 0.2.0 package，必要 bootstrap entries 可讀且 integrity 驗證通過，既有 0.1.0 artifact bytes 不被覆寫。

## AC-015: Regression baseline

- Requirement: NFR-002
- Scenario: Given 完成實作，When 執行 typecheck、Extension unit/security tests、package、smoke test 與 Repository unittest，Then 所有既有與新增測試通過，且 runtime 仍無 process、shell、network 或未授權 workspace write path。

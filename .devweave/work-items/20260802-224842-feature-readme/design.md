# 系統設計：補充 README 與繁體中文使用手冊

<!-- DEVWEAVE:artifact=design version=1 work=20260802-224842-feature-readme -->

## 設計摘要

本設計將文件拆成「入口 README」與「完整使用手冊」兩層：README 聚焦第一次閱讀者的
定位、前置需求、快速開始與流程導覽；`docs/使用手冊.md` 承載一般使用者與維護者需要的
完整命令、state、gate、Wiki、hook、測試與故障排除參考。兩份文件以相對連結互相導覽，
所有可執行命令與 machine vocabulary 均直接對齊目前 source、CLI help、contracts、tests
與 repository policy。

關鍵不變量如下：

- 不增加或修改 runtime、公開 router、machine CLI、schema、hook、Wiki、baseline 或 tests。
- README 與手冊只寫入繁體中文說明；命令、路徑、JSON keys、phase、gate 與 exit code 保持
  實際英文拼寫。
- 目前 `wiki/overview.md` placeholder 只作為手冊中的已知限制，不進行 Wiki promotion。
- 實作 diff 僅允許 `README.md` 與 `docs/使用手冊.md`，DevWeave artifacts 由 engine 管理。

## 選項比較

### 選項 A：只擴充 README

把快速開始、完整 CLI、維護與 troubleshooting 全部放在 README。優點是只有一個入口；
缺點是 README 過長，首次使用者難以辨識最短操作路徑，也不利於維護者查詢細節。
不採用。

### 選項 B：新增手冊但複製完整內容到兩份文件

可讓每個檔案獨立閱讀，但同一命令與 policy 會產生雙重事實來源，未來容易漂移。
不採用。

### 選項 C：README 入口 + `docs/使用手冊.md` 詳細參考

README 保留短路徑與核心概念，手冊提供完整 reference，並以連結把兩者串起來。這符合
兩類讀者需求，降低重複內容與導覽成本，且不需要任何 runtime 變更。採用。

## 介面與資料流

### 文件介面

- `README.md`：repository root 的公開入口，連結到 `docs/使用手冊.md`、`AGENTS.md`、
  contracts 與測試入口。
- `docs/使用手冊.md`：詳細使用者／維護者文件，連結回 README，並以章節分隔 chat surface、
  machine CLI、lifecycle、Wiki、hook、測試與 troubleshooting。
- 不新增 Python API、CLI subcommand、JSON wire shape 或 schema field。

### 實作資料流

1. 從 approved requirements 取得目前 public surface、scope 與不變量。
2. 以 source、`--help`、contracts 與 tests 核對命令、參數、exit code、state transition、
   Wiki policy 與 guard 行為。
3. 在 G2 後先完成 README 與手冊，再執行相對連結、命令 smoke check、完整 unittest 與
   `git diff --check`。
4. G3 以 acceptance artifact、current evidence、scope diff 與 `knowledge status` 作為
   唯一驗收輸入；目前沒有 Wiki source overlap，不建立 knowledge plan。

### 狀態與相容性

文件工作不改變 work item state schema；G1/G2/G3 fingerprints 只因預期 artifacts 或
文件 diff 改變而由 engine 更新。README 與手冊中的 machine contract 以現行 schema version
1 與 JSON-only CLI 為準，所有相對連結以 repository root 為基準。

## 失敗模式與回復

### 失敗模式

- CLI help 與手冊不一致：停止文件寫作，重新查閱 `devweave.py` help 與 source，修正文件。
- 連結指向不存在路徑：以 repository-relative path 檢查並修正 Markdown，不新增 placeholder。
- guard 拒絕文件 patch：確認 current G2、session binding 與 work scope；不得繞過 hook 或直接
  修改 state。
- G2 後需求或設計發現錯誤：使用 `revise --from requirements|design` 回到最早受影響階段，
  重新核准後再繼續；不得直接改寫 immutable plan。
- 測試或驗證失敗：保留 failure evidence，修正文件或記錄明確 blocker，再重新執行驗證。

### Rollback 與觀測

文件變更沒有 migration 或資料 rollback；若驗收不通過，保留 work item evidence，透過受 scope
控制的文件 patch 移除或修正兩份文件，或由使用者以 Git workflow 回復 diff。觀測點包括
`status`／`instructions` 的 gate 狀態、`validate` 報告、verification log、`git diff`、
`git diff --check` 與最終 acceptance matrix。

## 高風險分析

本工作風險為 `standard`，不涉及 authentication、privacy、destructive data、migration、
multi-service runtime 或 public API behavior；高風險 security、performance、migration 與
independent review 分析均不適用。相容性仍以文件中的命令與 machine contract 不得漂移為
核心檢查，並由 CLI smoke checks、完整測試與 G3 diff review 覆蓋。

## 設計決策

## DEC-001: 分層文件介面

- Requirements: REQ-001, REQ-002, REQ-003, NFR-003
- Decision: 採用 README 入口加 `docs/使用手冊.md` 詳細參考的雙層結構。
- Rationale: 同時滿足首次使用者的短路徑與維護者的深度查詢，避免單一 README 過長。
- Consequences: 需要維護兩份文件的導覽連結，但規則各有唯一主要承載位置。

## DEC-002: Source-bound 文件核對

- Requirements: REQ-004, NFR-001
- Decision: 命令、state、gate、Wiki 與 hook 描述以現行 source、CLI help、contracts、
  tests 與 AGENTS policy 交叉核對；不新增文件 generator 或新的 runtime interface。
- Rationale: 文件是目前行為的可讀入口，必須保留 machine contract 的真實拼寫與限制。
- Consequences: 文件更新需要同步執行 smoke checks；未來 runtime contract 變更時需重新檢查
  README 與手冊。

## DEC-003: 文件專用驗證與範圍隔離

- Requirements: REQ-005, NFR-002, NFR-003
- Decision: 只更新兩份文件；以 link/path check、CLI smoke check、完整 unittest、
  `git diff --check`、DevWeave scope 與 G3 acceptance matrix 驗證。
- Rationale: 文件變更不需要產品程式或測試改動，但必須防止連結、命令與 scope 漂移。
- Consequences: 現有 Wiki placeholder 只列為 warning；目前沒有 source overlap，因此不
  建立空的 knowledge promotion plan。

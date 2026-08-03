# 需求與驗收條件：補充 README 與繁體中文使用手冊

<!-- DEVWEAVE:artifact=requirements version=1 work=20260802-224842-feature-readme -->



## 假設與限制

本工作只更新 `README.md` 並新增 `docs/使用手冊.md`；文件內容以現行 source、CLI help、
contracts、tests、AGENTS 與 accepted baseline 為準。使用者可在 Codex 對話層使用公開
`$devweave` verbs，維護者可在 repository root 執行 Python machine CLI；兩者的角色與用途
必須明確區分。現有 Wiki placeholder 只需在手冊說明其狀態，不在本工作建立 Wiki promotion。

## 需求與驗收條件

## REQ-001: 專案入口說明

- Priority: must
- Acceptance: AC-001
- Description: README 必須以繁體中文清楚說明 DevWeave 的定位、主要使用者、核心價值、
  Python/Git/Codex 前置需求、managed repository 行為與不提供的能力，讓首次讀者能判斷
  是否適合導入本專案。

## REQ-002: 快速開始與核心流程

- Priority: must
- Acceptance: AC-002
- Description: README 必須提供從 hook trust、初始化或首次 `$devweave` 呼叫，到建立 work
  item、G1/G2/G3、驗證與關閉的可操作路徑，並說明 `new`、`feature`、`refactor`、`bug`、
  `next`、`status`、`revise`、`approve` 的用途。

## REQ-003: 完整使用者與維護者手冊

- Priority: must
- Acceptance: AC-003
- Description: `docs/使用手冊.md` 必須涵蓋初始化、Codex hook、公開 chat surface、完整
  machine CLI、work item artifacts、task/evidence、gate、fingerprint、Wiki-first、
  knowledge promotion、companion skills、測試、維護與故障排除。

## REQ-004: CLI 與生命週期事實正確

- Priority: must
- Acceptance: AC-004
- Description: 文件中列出的 CLI 命令、子命令、重要參數、JSON-only 輸出、exit code、phase、
  gate、session binding、scope、verification 與 stale/invalidation 行為，必須與目前
  `devweave.py`、`devweave_core.py`、`guard.py`、contracts 與測試相符，不得發明未實作能力。

## REQ-005: 文件導覽與交叉連結

- Priority: must
- Acceptance: AC-005
- Description: README 必須連到 `docs/使用手冊.md`；手冊必須能回到 README，並連結既有的
  `AGENTS.md`、DevWeave contracts、phase references、project structure 與測試入口，且所有
  repository-relative links 都指向存在的檔案或目錄。

## NFR-001: 繁體中文與機器介面保真

- Priority: must
- Acceptance: AC-006
- Description: 使用者可讀說明、標題、表格、錯誤處理與操作步驟使用繁體中文 zh-TW；命令、
  路徑、JSON keys、schema keys、phase、gate、work kind、risk level 與 exit code 保留實際
  英文拼寫，方便直接複製執行與搜尋 source。

## NFR-002: 範圍隔離與可逆性

- Priority: must
- Acceptance: AC-007
- Description: 實作 diff 僅包含 `README.md`、`docs/使用手冊.md` 與 DevWeave 正規產生的
  work-item artifacts；不得修改產品程式、測試、依賴、build、CI、Wiki、baseline 或
  machine JSON/JSONL ledger。

## NFR-003: 可維護的文件結構

- Priority: must
- Acceptance: AC-008
- Description: README 聚焦入口與快速開始；詳細命令與操作放在使用手冊；內容以標題、表格、
  code block 與 troubleshooting 分組，避免同一規則在兩份文件中產生互相矛盾的副本。

## AC-001: README 可作為專案入口

- Requirement: REQ-001
- Scenario: Given 使用者第一次開啟 repository，When 閱讀 README，Then 能在不閱讀 source
  的情況下理解 DevWeave 是什麼、需要什麼環境、管理哪些變更與如何取得完整手冊。

## AC-002: README 可引導首次操作

- Requirement: REQ-002
- Scenario: Given 一個已具備 Git、Python 3.11+ 與 Codex 的使用者，When 依 README 的快速
  開始步驟操作，Then 能找到 hook trust、初始化／首次 chat command、work item 與三道 gate
  的正確下一步，且不會被引導直接跳過 G1 或 G2。

## AC-003: 手冊涵蓋兩類讀者

- Requirement: REQ-003
- Scenario: Given 一般使用者或 repository 維護者查閱手冊，When 尋找日常操作、CLI 參數、
  Wiki、hook、測試或故障排除，Then 能在對應章節找到具體命令、前置條件、結果與 recovery
  方式。

## AC-004: 命令與 state 行為可核對

- Requirement: REQ-004
- Scenario: Given 文件中的每個核心命令與生命週期描述，When 以現行 CLI `--help`、`doctor`、
  `project`、`status --all`、source 或 tests 交叉核對，Then 命令名稱、參數、輸出格式、
  exit code 與 gate/stale 行為均有實際依據且沒有虛構選項。

## AC-005: 導覽連結可用

- Requirement: REQ-005
- Scenario: Given README 與使用手冊已完成，When 執行相對連結與檔案存在性檢查，Then README
  到手冊、手冊回 README 及其引用的 repository 文件連結全部可解析。

## AC-006: 語言與命令可直接使用

- Requirement: NFR-001
- Scenario: Given zh-TW 使用者複製手冊中的命令，When 在 repository root 執行，Then 命令與
  路徑保留實際大小寫及拼寫，使用者可直接查找對應的英文 machine key 或 CLI help。

## AC-007: Diff 不越界

- Requirement: NFR-002
- Scenario: Given 文件實作與驗證完成，When 檢查 `git diff` 與 DevWeave scope，Then 只有兩份
  使用者文件及正規 work-item artifacts 被修改，Wiki、產品 source、tests、baseline、
  dependencies、build、CI 與 JSON/JSONL ledger 沒有非預期變更。

## AC-008: 文件分工清楚

- Requirement: NFR-003
- Scenario: Given 使用者需要快速開始或查詢深度操作，When 分別閱讀 README 或使用手冊，Then
  README 提供短路徑與導覽，手冊提供詳細參考，兩者對同一規則沒有相互矛盾的描述。

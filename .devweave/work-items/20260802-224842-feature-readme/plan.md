# 執行計畫：補充 README 與繁體中文使用手冊

<!-- DEVWEAVE:artifact=plan version=1 work=20260802-224842-feature-readme -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 重整 README 入口

- Traces: REQ-001, REQ-002, NFR-001, NFR-003; AC-001, AC-002, AC-006, AC-008; DEC-001, DEC-002
- Inputs: approved brief、requirements、現行 README、AGENTS、CLI help 與 contracts。
- Output: 以繁體中文重寫 `README.md`，包含定位、前置需求、快速開始、公開 `$devweave`
  verbs、G1/G2/G3、核心限制、repository structure、測試入口與使用手冊連結。
- Verification: 檢查 README headings、快速開始命令、相對連結、machine names 與不變量描述。
- Dependencies: none

## TASK-002: 建立完整使用手冊

- Traces: REQ-003, REQ-004, NFR-001, NFR-003; AC-003, AC-004, AC-006, AC-008; DEC-001, DEC-002
- Inputs: approved design、README 入口結構、`devweave.py` CLI help、core/contracts、
  guard、Wiki lifecycle、測試與 companion skill policy。
- Output: 新增 `docs/使用手冊.md`，涵蓋初始化、hook trust、chat surface、完整 machine CLI、
  work item/artifact/task/evidence/gate/fingerprint、Wiki、companion skills、測試、維護與
  troubleshooting。
- Verification: 對照 CLI help 與 source 逐節核對命令、參數、exit code、phase、gate、
  failure/recovery 與禁止事項。
- Dependencies: TASK-001

## TASK-003: 完成文件交叉連結與一致性檢查

- Traces: REQ-004, REQ-005, NFR-002, NFR-003; AC-004, AC-005, AC-007, AC-008; DEC-002, DEC-003
- Inputs: TASK-001、TASK-002 的兩份文件。
- Output: README ↔ 使用手冊、AGENTS、contracts、phase references 與測試入口的相對連結
  完整；兩份文件對同一 machine contract 不互相矛盾，且無 TODO 或未實作命令。
- Verification: 執行文件 link/path check、各 CLI `--help` smoke check、`doctor`、`project`、
  `status --all` 與 `git diff --check`。
- Dependencies: TASK-001, TASK-002

## TASK-004: 完成文件範圍與回歸驗證準備

- Traces: REQ-004, NFR-002, NFR-003; AC-004, AC-007, AC-008; DEC-002, DEC-003
- Inputs: TASK-003 的一致性檢查結果與目前 work scope。
- Output: 確認 diff 僅包含 README、使用手冊與正規 work-item artifacts；建立 G3 所需的
  acceptance/regression 驗證清單，並記錄不需 baseline 或 Wiki promotion 的理由。
- Verification: 執行完整 `unit-tests`，檢查 `knowledge status`、baseline scope、Git diff
  與 acceptance matrix 的覆蓋範圍。
- Dependencies: TASK-003

## 驗證策略

- Targeted CLI：執行 root CLI help、各 public subcommand help、`doctor`、`project` 與
  `status --all`，確認手冊中的 syntax、JSON-only output 與 exit code 描述可核對。
- 文件檢查：確認兩份文件均為 zh-TW、沒有 TODO、標題層級清楚、README 與手冊雙向連結、
  引用的 repository-relative paths 存在。
- Regression：透過已設定的 `unit-tests` 命令執行 `python -B -m unittest discover -s tests -v`，
  期待現有 62 項測試全部通過。
- Scope：執行 `git diff --check`、檢查 work scope 與完整 diff，確認沒有 source、tests、
  dependencies、build、CI、Wiki、baseline 或 machine ledger 變更。
- Knowledge：執行 `knowledge status --work`；若仍無 affected page，不建立空的 knowledge
  plan 或 no-update machine rationale。
- Acceptance：G3 acceptance artifact 以 REQ/AC/TASK/evidence matrix、測試結果、文件檢查、
  scope 結果、Wiki warning 與 residual risk 組成。

## 基線更新計畫

本工作不改變已接受的產品、架構或品質治理真相，因此不更新 `.devweave/baseline/`。在
verification 階段透過 DevWeave baseline command 記錄空 targets 與明確理由「本 work item
僅更新使用者文件，未改變 accepted governance truth」。Wiki 維持唯讀；目前 starter
placeholder warning 不屬於本 work item 的 affected page。

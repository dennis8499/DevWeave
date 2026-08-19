# 需求與驗收條件：Fix Node 20 and POSIX CI regressions

<!-- DEVWEAVE:artifact=requirements version=1 work=20260819-140802-bug-fix-node-20-and-posix-ci-regressions -->

## 假設與限制

- 修正直接補進 `hardening/p0-00-public-ci` 的 PR #1，不建立第二條 CI workflow 或第二個 PR。
- Git branch、commit、push、PR 與 merge 全由使用者操作；Agent 只修改工作區並執行受治理驗證。
- 使用者已決定在 G3 前先做一次 provisional commit/push，17 個 hosted jobs 全綠後才進入 G3；close 後再由使用者 push 最終 governance records。Hosted result 是補充人工證據，DevWeave G3 的 machine coverage 仍由 current standard-profile controlled evidence 提供。
- 不修改 CI matrix、production security semantics、public API、dependencies、lockfile 或 current VSIX bytes。
- 新增恰好一項 Extension unit test，因此 current source baseline 由 88 更新為 89；既有歷史 Work Item 與 Wiki log 的 88-test 紀錄不得改寫。
- Windows launcher tests 在 Windows 必須真實執行；非 Windows 只能以明確 Windows-only 原因 skip。沒有 waiver。

## 需求與驗收條件

## REQ-001: Node 20 與 Node 22 執行相同 Extension unit tests
- Priority: must
- Acceptance: AC-001, AC-002
- Description: `npm test` 必須在 Node 20／22 與 Windows／Ubuntu 不依賴 shell glob 展開，遞迴執行固定排序的全部 `test/unit/**/*.test.ts`；child 結果須原樣決定 command exit。

## REQ-002: CLI executable assertion 保留 canonical path 契約
- Priority: must
- Acceptance: AC-003
- Description: CLI contract test 必須接受 `sys.executable` 在 POSIX 經 symlink resolution 後的 canonical path，並同時核對 `argv[0]` 與 `resolved_executable`，不得弱化 production executable trust normalization。

## REQ-003: Guard 的 unmanaged-repository fixture 必須跨平台
- Priority: must
- Acceptance: AC-004
- Description: Guard contract 必須使用真實 repository 外 absolute temporary directory 驗證 unmanaged cwd 不啟用 DevWeave，不得依賴 Windows drive syntax 或恢復 Verification Policy v2 移除的 read-only early short-circuit。

## REQ-004: Windows hook launcher contract 只在可觀察平台執行
- Priority: must
- Acceptance: AC-005
- Description: 三項 `commandWindows` process-level tests 必須在 Windows 完整執行 CMD、Windows PowerShell、PowerShell 7 與 root/nested cwd matrix；非 Windows 必須以具名 Windows-only reason skip，不得呼叫 POSIX shell 執行 Windows command。

## REQ-005: Current verification 與發布說明保持一致
- Priority: must
- Acceptance: AC-006
- Description: Current source 的 Extension unit-test baseline 必須更新為 89，純 CI runner／test 不得增加 certified VSIX entries；quality baseline、release surfaces、repository contract 與五個 affected Wiki content pages 必須一致且保留歷史 provenance。

## NFR-001: Test runner deterministic 且 fail closed
- Priority: must
- Acceptance: AC-001, AC-002
- Description: Runner 必須使用 deterministic lexical ordering、argument-array child process、inherited stdio 與 exact nonzero propagation；0 tests、spawn error、signal 或 null/nonzero status 一律失敗。

## NFR-002: 相容性與安全行為不得退化
- Priority: must
- Acceptance: AC-003, AC-004, AC-005, AC-006
- Description: 修正不得改動 CI workflow、CLI/Guard/hook production semantics、dependency graph、lockfile、public API 或 VSIX entry count；跨平台差異只能在 test seam 明確表達。

## AC-001: Node 20/22 unit suite 實際執行 89 項
- Requirement: REQ-001, NFR-001
- Scenario: Given 完成後的 Extension tree，When 分別以 Node 20 與目前 Node 執行 `npm test`，Then runner 以 explicit file argv 執行 89 項 tests、全部通過，且輸出不再包含字面 glob 找不到檔案。

## AC-002: Runner discovery 與失敗傳播受回歸保護
- Requirement: REQ-001, NFR-001
- Scenario: Given 含巢狀 `.test.ts`、非測試檔與空目錄的 temporary fixtures，When 呼叫 discovery seam，Then 只回傳固定排序的測試檔；空集合拋出錯誤，child 非零或啟動異常使 top-level command 非零。

## AC-003: Python executable alias 在所有 OS 維持 canonical JSON
- Requirement: REQ-002, NFR-002
- Scenario: Given `sys.executable` 可能是 symlink 或實體路徑，When CLI `command set` 回傳 command JSON，Then test 期待 `str(Path(sys.executable).resolve())`，且 `argv[0]` 與 `resolved_executable` 相等；Windows 與 POSIX 均通過。

## AC-004: Repository 外 read-only Bash 不誤啟用 Guard
- Requirement: REQ-003, NFR-002
- Scenario: Given platform-native temporary directory 且其中沒有 `.devweave/project.json`，When Guard 收到 read-only Bash payload，Then 回傳 `None`；fixture 不從目前 repository 向上誤發現 managed project，configured-command policy ordering保持不變。

## AC-005: Windows launcher coverage 與非 Windows skip 誠實
- Requirement: REQ-004, NFR-002
- Scenario: Given Python suite 在 Windows 執行，When 執行三項 launcher tests，Then CMD、PowerShell 5.1、PowerShell 7 的 deny JSON、malformed input、read-only silence 全部實跑通過；Given Ubuntu/macOS，Then 同三項以精確 Windows-only reason 顯示 skipped 且其餘 suite 通過。

## AC-006: Current baseline、文件、Wiki 與 package boundary 一致
- Requirement: REQ-005, NFR-002
- Scenario: Given 完成後的 source，When 執行 repository contract、Extension tests/typecheck/build、完整 Python suite 與 `git diff --check`，Then current surfaces 一致標示 89 Extension tests、Python Windows baseline 仍為 111（既有 symlink privilege skip 可保留）、VSIX contract 仍為 58 bootstrap files／119 entries；舊 evidence 與 Wiki log 的 88-test 歷史內容保持不變。

# 執行計畫：Fix Node 20 and POSIX CI regressions

<!-- DEVWEAVE:artifact=plan version=1 work=20260819-140802-bug-fix-node-20-and-posix-ci-regressions -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 以單一回歸測試建立 deterministic Unit Test Runner

- Traces: REQ-001, NFR-001, AC-001, AC-002, DEC-001
- Inputs: 已核准 G1 artifacts、目前 `package.json` glob script、lockfile 的 `tsx/cli` export、現有 88 個 Extension tests。
- Output: 先新增 `unit-test-runner.test.ts` 的單一 top-level red test，再新增 `run-unit-tests.mjs` 與更新 `npm test` script；runner只列舉排序後的regular `.test.ts`，以same Node與explicit argv啟動tsx，所有abnormal outcomes fail closed，current suite精確為89。
- Verification: 以 DevWeave controlled `extension-tests` 記錄 missing-runner red 與89-test zero-only green；執行 `extension-typecheck`，並檢查捕捉到的 node executable、argv、cwd、`shell:false`、`stdio:inherit`、exact nonzero、zero/error/signal/null分支。
- Dependencies: none

## TASK-002: 修正 CLI executable 與 Guard unmanaged fixture

- Traces: REQ-002, REQ-003, NFR-002, AC-003, AC-004, DEC-002
- Inputs: hosted Python failure logs、production canonical executable JSON、`RepositoryHarness` temporary Git repository。
- Output: `test_cli.py` 同時檢查 canonical `argv[0]`／`resolved_executable`；`test_guard.py` 使用未初始化的absolute temporary repository驗證read-only Bash不啟用DevWeave；不修改production scripts。
- Verification: DevWeave controlled `unit-tests-cli` 與 `unit-tests-guard` zero-only通過；人工diff確認沒有 `.agents/skills/devweave/scripts` production變更。
- Dependencies: none

## TASK-003: 將 Windows hook launcher coverage 綁定真實 capability

- Traces: REQ-004, NFR-002, AC-005, DEC-002
- Inputs: 三項現有 `commandWindows` process-level methods、`WINDOWS_HOOK_RUNNERS` 與 Windows CI 對照綠燈。
- Output: 新增單一精確 non-Windows skip reason，僅裝飾三項launcher methods；Windows仍執行CMD、Windows PowerShell、PowerShell 7與root/nested cwd matrix，其他平台不呼叫POSIX shell解讀Windows command。
- Verification: 本機Windows以DevWeave controlled `unit-tests-contract` 真實全綠；hosted Ubuntu/macOS顯示同三項具名skip且其餘suite通過。
- Dependencies: none

## TASK-004: 固定 package boundary 與 89-test current surfaces

- Traces: REQ-005, NFR-002, AC-006, DEC-003, DEC-004
- Inputs: TASK-001 runner paths、TASK-002/TASK-003 platform contracts、目前58-bootstrap／119-VSIX contract與四個release surfaces。
- Output: VSIX builder排除runner與runner test；既有package-version test固定test script及exclusions；repository release contract、README、使用手冊、Extension README、Webview help一致標示89 tests；不改lockfile、workflow或VSIX bytes。
- Verification: `extension-tests`、`extension-typecheck`、`unit-tests-contract`、`npm run build`與`git diff --check`通過；static assertions仍固定58 bootstrap files／119 VSIX entries，release-only package/smoke不執行。
- Dependencies: TASK-001, TASK-002, TASK-003

## 驗證策略

- **TDD targeted**：TASK-001先讓單一新test因runner module缺失而red，再以最小runner實作收為89 green；不得以刪除test、吞child failure或放寬zero-test處理收綠。
- **Python targeted**：TASK-002跑CLI/Guard commands；TASK-003在Windows跑repository contract真實launcher matrix。POSIX分支由hosted full suite觀察精確skip，既有GitHub failure作reproduction而非G3 eligible evidence。
- **Controlled regression**：G2後凍結standard Effective Verification Plan；執行Extension tests/typecheck與CLI、contract、core、guard、knowledge五組Python commands。`extension-package`與其smoke dependency保留release-only skip reason。
- **Additional regression**：執行完整 `python -B -m unittest discover -s tests -v`、`npm run build`、scope/diff review與`git diff --check`；本機Node 24驗證module，Node20/22由hosted matrix驗證。
- **Hosted acceptance**：Agent不做Git操作。使用者provisional commit/push後，同一PR必須有12個Python、4個Node、1個hygiene共17/17通過；任一失敗先回implementation診斷，不進G3。
- **Package boundary**：不執行package/smoke、不建立candidate、不promotion current VSIX；以builder exclusions、package-version contract與既有119-entry verifier assertion證明source boundary。
- **G3 Knowledge Review**：hosted全綠後選擇promote，upsert `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`、`wiki/modules/public-ci.md`，同步index/log/seal。Public CI page加入runner source並記錄Node glob與Python capability修正；Wiki在verification前唯讀。

## 基線更新計畫

- Verification階段更新 `.devweave/baseline/quality.md` 的current Extension command/result為89，加入本Work Item的standard-profile與hosted17/17結果。
- 保留P0-00 frozen profile、pre-G1 baseline、既有evidence與Wiki log中真實發生過的88-test歷史文字；不回寫歷史Work Item。
- 不更新product／architecture baseline：沒有runtime capability、public API或architecture provider變更；durable module/CI知識由五頁Wiki promotion承擔。
- `acceptance.md` 分開列出controlled evidence、manual build/hygiene、hosted observation、三個POSIX Windows-only skips與未執行package/smoke理由；沒有waiver。

# 系統設計：Fix Node 20 and POSIX CI regressions

<!-- DEVWEAVE:artifact=design version=1 work=20260819-140802-bug-fix-node-20-and-posix-ci-regressions -->

## 設計摘要

本修正由兩個互不擴張 production surface 的模組完成。第一個是 repository-local **Unit Test Runner Module**：對維護者與 CI 的唯一外部 **Interface** 仍是無參數的 `npm test`，其 **Seam** 位於 `package.json` script 與 `scripts/run-unit-tests.mjs`。Runner 在內部隱藏跨 Node 版本的檔案探索、排序、`tsx/cli` 解析、argument-array child process、stdio 與 exit propagation，讓四個 Node matrix cells 共用一個高 **Depth** 實作並提高 failure **Locality**。

第二個是既有 Python contract tests 的 **Platform Capability Test Surface**。它不新增 production Adapter，而是在 test seam 誠實表達 executable alias、unmanaged repository 與 Windows launcher 的平台條件；目前 production CLI canonicalization、Guard Verification Policy v2 ordering、hook launcher 與 `.github/workflows/ci.yml` 都保持不變。

關鍵不變量：

1. `npm test` 不依賴 shell glob、`.bin` wrapper 或第三方 glob dependency；同一 Node executable 以 explicit argv 啟動 lockfile 安裝的 `tsx/cli`。
2. Test discovery 只接受 `test/unit` 下的 regular `*.test.ts`，不跟隨 symlink directory，以 `/` 正規化的相對路徑作 code-unit lexical ordering，再傳入 absolute paths。
3. Child numeric status 原值回傳；0 tests、filesystem／resolver／spawn error、signal 或 null status 一律回傳 1，且 child stdout/stderr 維持 inherited。
4. 新增的 runner regression 只有一個 top-level `test()` 且不建立 subtests，使 current Extension baseline 精確由 88 變成 89。
5. Python 修正只修改 tests；Windows launcher 三項在 Windows 真實執行，在 POSIX 以同一精確原因 skipped。
6. 新 runner 與 runner test 都排除於 VSIX builder，58 個 bootstrap files、119 個 VSIX entries、現有 VSIX bytes 與 retained artifacts 不變。
7. 無 public API、schema、dependency、lockfile、CI matrix、security policy、runtime 或 migration 變更。

## 選項比較

### Runner 啟動方式

- **選定：repository-local explicit-file runner。** 手動遞迴列舉與固定排序測試檔，使用 `process.execPath` 與 Node 內建 resolver 取得 `tsx/cli`，再以 argument array 啟動。這同時消除 shell 與 Node 20/22 glob 差異。
- **拒絕：保留 `tsx --test "test/unit/**/*.test.ts"`。** Node 20 將 glob 視為字面路徑，已由 hosted logs 證明無法滿足 matrix。
- **拒絕：改用 shell-specific glob 或第三方 glob package。** Windows/POSIX shell 語意不同，且會新增 dependency／lockfile 與供應鏈範圍。

### Runner 測試 Seam

- **使用者選定：可注入的內部 seam。** `npm test` 維持唯一外部 Interface；模組匯出 `discoverUnitTests(testRoot)` 與 `runUnitTests(options)` 供單一 regression test 使用。Filesystem 以 temporary directory 作 local substitute，child process 以 fake spawn Adapter 觀察 argv 與結果。
- **拒絕：純黑箱 subprocess。** 雖更貼近完整 process，但需要假 `tsx` tree，且 spawn error、signal 與 null status 難以穩定重現，會增加速度與平台脆弱性。
- **拒絕：另拆 discovery package。** 只有一個 caller，拆分會形成 pass-through shallow module 並擴張 G1 scope；單檔深模組具有較佳 Locality。

### Python 平台邊界

- **選定：修正 assertions 與 fixtures。** CLI test 期待 canonical executable；Guard test 使用未 managed 的 absolute temporary Git repository；三項 `commandWindows` tests 用 `sys.platform == "win32"` 作 capability gate。
- **拒絕：修改 production canonicalization 或恢復 Guard read-only early short-circuit。** 兩者會弱化已核准 executable trust 與 command-policy ordering。
- **拒絕：讓 POSIX shell 嘗試執行 Windows command。** 這會把 unsupported capability 假裝成 product regression，且無法提供 Windows launcher 的有效 oracle。

### Package 與驗證邊界

- **選定：以 explicit exclusion 與 static package contract 維持 119 entries。** 不執行 release-only package/smoke，也不重建、promotion 或替換 0.2.3 VSIX。
- **拒絕：接受新增 VSIX entries 或更新 certified count。** Runner 與其 test 只是 development infrastructure，不應成為 Extension runtime payload。
- **選定：同一 PR 的 hosted 17/17 是 G3 前置人工觀察。** 本機 controlled evidence 與 hosted observation 分開記錄，不把外部結果冒充 engine evidence。

## 介面與資料流

### Unit Test Runner Module

- **External Interface**：`npm test`，無新增 CLI flags；`package.json` 將 script 固定為 `node scripts/run-unit-tests.mjs`。
- **Internal test Interface**：
  - `discoverUnitTests(testRoot) -> Promise<string[]>`：回傳依 normalized relative path 排序的 absolute test paths。
  - `runUnitTests({ extensionRoot, testRoot, nodeExecutable, tsxCli, spawn, writeError } = {}) -> Promise<number>`：所有 options 均有 production defaults；test 注入 fake spawn 與 error sink。
- **Production adapters**：Node `fs/promises.readdir`、`createRequire(import.meta.url).resolve("tsx/cli")`、`child_process.spawnSync`、`process.stderr`。
- **Test adapters**：OS temporary filesystem、捕捉呼叫的 fake spawn、in-memory error collector。Dependency category 是 local-substitutable，不建立 public port。
- **Invocation guard**：只有 `process.argv[1]` resolve 後等於 `import.meta.url` 對應檔案時，才把 `await runUnitTests()` 指派給 `process.exitCode`；被 regression test import 時不遞迴啟動 suite。

資料流：

```text
npm test
  -> current Node 執行 run-unit-tests.mjs
  -> 遞迴 test/unit，過濾 regular *.test.ts
  -> normalized-relative lexical sort
  -> resolve locked tsx/cli
  -> spawnSync(process.execPath, [tsxCli, --test, ...absoluteTests])
  -> inherited child output + exact numeric exit
```

### Python Contract Test Surface

- CLI command-set assertion 先計算 `expected = str(Path(sys.executable).resolve())`，再同時檢查 `argv[0]`、其餘 argv 與 `resolved_executable`。
- Guard read-only Bash case 使用 `RepositoryHarness` 尚未 `init()` 的 absolute temporary Git repository，讓 discovery 找到真正 unmanaged root 而不是由 `Z:\\...` 在 POSIX 向目前 repository 反向解析。
- 新增 `NON_WINDOWS_HOOK_LAUNCHER_SKIP = "Windows-only hook launcher contract requires cmd.exe, Windows PowerShell, and PowerShell 7."`；三個 launcher methods 各用 `@unittest.skipUnless(sys.platform == "win32", ...)`。Windows 仍完整跑三 runner × root/nested cwd matrix。

### Package、文件與知識

- VSIX builder exclusion set 新增 `scripts/run-unit-tests.mjs` 與 `test/unit/unit-test-runner.test.ts`；`package-version.test.ts` 在既有 test 內固定 `npm test` script 與兩個 exclusions，不增加 top-level test 數。
- README、使用手冊、Extension README、Webview help 與 repository release contract 的 current baseline 更新為 89。
- `.devweave/baseline/quality.md` 只在 verification 更新 current 89-test 結果；P0-00 frozen、pre-G1 與其他 evidence-specific 88-test 歷史行保留。
- Wiki 在 G2/implementation 唯讀；G3 promote 五個既定 content pages，更新 current count、Node runner seam、Python platform truth 與首次 hosted outcome，同步 index/log/seal，但不改寫既有 Wiki log 的 88-test 歷史 entry。

## 失敗模式與回復

- **0 tests／directory read error**：runner 輸出具體訊息並回 1，不允許空 suite 假綠。
- **缺少或無法解析 `tsx/cli`**：resolver error 轉為 exit 1；不 fallback 到 network、`npx` 或 shell PATH。
- **spawn error／signal／null status**：輸出 error 或 signal detail 並回 1；不將 abnormal termination 解讀為成功。
- **child test failure**：任何 numeric nonzero 原值傳播，讓 CI step 顯示真實 failure。
- **POSIX Python launcher**：三項明確 skipped；其他 tests 繼續執行。Windows 若缺少任一 launcher，test 仍失敗而不是 skip。
- **package drift**：static contract 若找不到兩個 exclusions、test script 或 119-entry verifier assertion即失敗；不藉 package rebuild修改 current artifact。
- **hosted cell 失敗**：留在同一 Work Item 診斷；若需改變介面、production semantics、scope 或 task，從最早受影響 phase `revise`，不使用 waiver 掩蓋。
- **回復**：由使用者透過 Git 回復 runner/script/test fixture/package exclusion／文件與 G3 governance changes；沒有資料、schema 或 runtime migration。Agent 不執行 commit、push、reset 或 merge。
- **觀測**：runner 繼承 child stdio並保留 exit；unittest 顯示精確 skip reason；GitHub checks 以 OS/runtime 命名；G3 分開列出 controlled evidence 與 17-cell hosted observation。

## 高風險分析

本工作項為 standard risk，不涉及 production rollout、credential、資料 migration、irreversible state 或 public API，因此 high-risk migration、security review、performance benchmark與 Independent Review Agent 不適用。

相容性風險集中於本機沒有 Node 20，也無法本機觀察 Ubuntu/macOS；以 Node 24 驗證 runner module，再以既有 GitHub Node 20/22 與 Python 3.11–3.14 matrix作最終 external oracle。Runner 最多列舉目前 89 個 tests，效能成本相對 `tsx` 啟動可忽略；recursive traversal 只限 `test/unit`。

## 設計決策

## DEC-001: 以可注入深模組取代 shell glob
- Requirements: REQ-001, NFR-001
- Decision: `npm test` 委派給單檔 Unit Test Runner；外部介面無參數，內部提供 discovery/run seam，使用 temporary filesystem 與 fake spawn adapters測試。
- Rationale: 使用者在 Plan Mode 選定此方案；它能以單一 top-level test deterministic 覆蓋 discovery 與所有 fail-closed 分支，並把 Node/platform 差異集中在一處。
- Consequences: 新增兩個 internal exports，但不成為 Extension API；runner 必須維持 explicit argv、排序與完整 exit semantics。

## DEC-002: 跨平台差異只在 Python test seam 表達
- Requirements: REQ-002, REQ-003, REQ-004, NFR-002
- Decision: 修正 CLI expected path、Guard temporary unmanaged repository，以及三項 Windows-only decorators；production CLI、Guard、hook bytes 不變。
- Rationale: Hosted failure 是 fixture 對 symlink、Windows path 與 shell capability 的錯誤假設，不是 production security regression。
- Consequences: POSIX full suite新增三個具名 skip；Windows matrix持續實跑全部 launcher cases，安全契約不弱化。

## DEC-003: Development runner 不進入 certified VSIX
- Requirements: REQ-005, NFR-002
- Decision: Builder明確排除 runner與其 test，既有 package contract固定 script與 exclusions；current release surfaces改為89 tests，但不重建 VSIX。
- Rationale: Development-only infrastructure不應改變119-entry runtime payload或current artifact bytes。
- Consequences: 未來移動 runner/test路徑時，builder與package contract必須一起更新；release-only package/smoke仍合法跳過。

## DEC-004: Hosted 17/17 成功先於 G3 governance
- Requirements: REQ-005, NFR-002
- Decision: 完成本機 controlled verification後，由使用者 provisional commit/push；同一 PR 取得17/17後才更新 acceptance、living baseline與Wiki並請求G3。
- Rationale: Node 20與POSIX是本機無法完整重現的外部平台邊界，Gate摘要不能以推論取代真實hosted observation。
- Consequences: 需要兩階段使用者Git操作；hosted服務不可用或任一cell紅燈時，Work Item保持active且不進G3。

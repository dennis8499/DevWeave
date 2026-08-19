# 功能驗收：Fix Node 20 and POSIX CI regressions

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260819-140802-bug-fix-node-20-and-posix-ci-regressions -->

## 驗證矩陣

### 驗證基線

- Work Item：`20260819-140802-bug-fix-node-20-and-posix-ci-regressions`；standard-risk bug，G1 scope 與 G2 build 已由使用者核准，TASK-001～TASK-004 全部完成，無 waiver。
- Git HEAD：`036ca6b2cbaabe117a82420948e5b7c3bdbd2a83`；current product/source fingerprint：`3dae54d518eb27185075ab8c940eb320496d7ac3ddb1f1b8611c13fb1cf583f8`。
- Frozen standard plan：`sha256:eb3236f2ed8e4ed93f8fa3e2d0e6b9d68ca9be2f279545a599c2a686e804e62c`；trace-complete 循序 batch `VB-1786ea0ecaff` 的 7 個 selected commands 全部 passing，2 個 release-only／dependent commands依 plan 合法跳過。
- Hosted oracle：PR #1 GitHub Actions run `32231940371` 在同一 HEAD 完成 17/17；12 個 Python cells、4 個 Node cells與 repository hygiene 均 passing，記錄為 supplemental `EVID-024`。
- Final Knowledge fingerprint：`b6a14028a58f242fafd0cd966a3aa82174cf8311b56733989aa03fb0a496f863`；五個 planned content pages 與 index/log 已全部 seal。

| Acceptance | TASK／evidence 與結果 |
| --- | --- |
| AC-001 Node 20/22 實際執行 89 項 | TASK-001 完成。`EVID-057` 以 controlled `extension-tests` 執行 89/89；runner 將 sorted explicit file paths 傳給 resolved `tsx/cli`。Hosted run 的 Node 20／22 × Ubuntu／Windows 四格全部通過，包含 typecheck、test 與 build。 |
| AC-002 discovery 與失敗傳播 | TASK-001 完成。`EVID-003` 先因 runner module 尚不存在產生單一 88-pass／1-fail red；`EVID-057` 收綠並覆蓋 nested discovery、忽略非 `.test.ts`、deterministic order、exact nonzero、spawn error、signal、null status 與 empty suite。 |
| AC-003 Python canonical executable | TASK-002 完成。`EVID-058` 的 CLI 23/23 通過，驗證 `argv[0]` 與 `resolved_executable` 均等於 `str(Path(sys.executable).resolve())`；hosted Windows、Ubuntu、macOS 的 Python 3.11～3.14 全部通過。 |
| AC-004 unmanaged repository Guard fixture | TASK-002 完成。`EVID-059` 的 Guard 15/15 通過；fixture 使用 `RepositoryHarness` 建立平台原生 temporary repository，read-only Bash 回傳 `None`，不依賴 `Z:\\` 或恢復被移除的 early short-circuit。 |
| AC-005 Windows launcher／POSIX skip truth | TASK-003 完成。`EVID-060` 的 repository contract 18/18 在本機 Windows 實跑 CMD、PowerShell 5.1、PowerShell 7；hosted Windows Python cells 全綠。Ubuntu／macOS 的三項 process-level methods 只以 exact `Windows-only hook launcher contract requires cmd.exe, Windows PowerShell, and PowerShell 7.` reason skip，其餘 suite 全綠。 |
| AC-006 baseline、文件、Wiki、package boundary | TASK-004 完成。`EVID-050` 固定 current 89 tests，`EVID-060` 固定四個 release surfaces、runner/package exclusions 與 58 bootstrap／119 VSIX contract；`EVID-051` typecheck 通過。四個 hosted Node jobs 的 `npm run build` 通過，`git diff --check` 無 whitespace error。舊 Work Item／Wiki log 的 88-test 歷史未改寫，current quality baseline 與五頁 Wiki 已更新。 |

## Profile 證據

- 修正前 reproduction：`EVID-001`／`EVID-002` 保存 GitHub run `32218573938` 的實際故障形狀——Node 20 把 glob 當字面路徑；Python Ubuntu／macOS 在 canonical executable、Windows drive fixture 與 `commandWindows` launcher 失敗。兩者為 manual、non-gate evidence；`EVID-003` 是 TASK-001 controlled expected-nonzero TDD red。
- Current standard regression：`EVID-050` extension tests（89）、`EVID-051` typecheck、`EVID-052` CLI（23）、`EVID-053` repository contract（18）、`EVID-054` core（45，1 個既有 Windows symlink privilege skip）、`EVID-055` Guard（15）、`EVID-056` Knowledge（16）；全部 current、zero-only、gate-eligible，且逐筆追溯 AC-006／TASK-004。
- Current targeted trace：`EVID-057` 覆蓋 AC-001／AC-002 與 TASK-001；`EVID-058` 覆蓋 AC-003／TASK-002；`EVID-059` 覆蓋 AC-004／TASK-002；`EVID-060` 覆蓋 AC-005／TASK-003。AC-006／TASK-004 由 standard batch 全面覆蓋。
- Hosted acceptance：`EVID-024` 記錄 run `32231940371` 的 17/17。它刻意標示 `manual_evidence_not_gate_eligible`，不取代上述 controlled evidence。
- Plan-defined skips：`extension-package` 為 `release-only`；`extension-smoke` 為 `release-only-dependency:extension-package`。本次不建立 candidate、不 promotion VSIX，沒有 waiver。
- 一次 `--max-parallel 3` 重跑時，所有 test process 本身皆通過，但 `EVID-030`、`EVID-035`、`EVID-038` 將鄰近 verifier 寫入的 `.devweave` records 判為 undeclared writes；這批不作 G3 證據。後續無 AC/TASK metadata 的 records 也已透過 official implementation revision 標為 stale；相同 frozen plan 以 trace-complete `--max-parallel 1` 重跑後形成 7/7 的 `VB-1786ea0ecaff`。

## 基線更新

已先由 DevWeave 宣告 `.devweave/baseline/quality.md`，再加入 cross-platform runner／canonical Python executable／具名 Windows-only skip contract、current 89-test standard batch與 hosted 17/17。P0-00 原始 frozen plan、pre-G1 88-test baseline 與其他歷史 provenance 均保留；沒有修改 product 或 architecture baseline。

## Wiki 知識提升

- Knowledge Review disposition：`promote`；runner、平台 capability truth、hosted CI 結果與 current test count 對後續 CI／release 工作具有 durable value。
- Planned upserts：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/public-ci.md`、`wiki/modules/vscode-extension.md`；coupled：`wiki/index.md`、`wiki/log.md`；無 delete。
- `knowledge-engine` sources 納入 `tests/test_guard.py` 後，final `covered_changed_paths` 包含全部 12 個 product changed paths；`pending_refresh=[]`、`uncovered_changed_paths=[]`、`unsealed_pages=[]`，七個 targets 全部 seal。
- Final health 為 warning，只因不在本工作 affected／planned set 的 `wiki/modules/command-policy-engine.md` 有既存 stale-source warning；無 critical lint，沒有超過五頁上限來順手修改無關頁面。

## 獨立 Review

本 Work Item 風險為 `standard`；依 DevWeave policy 不啟動 high-risk 專用 independent reviewer，也沒有 review evidence 或 review waiver。

## 殘餘風險

- Release-only package／Extension Host smoke 未執行，沒有產生或變更 VSIX；本次證明的是 development CI 與靜態 package boundary，不是新的 release certification。
- 使用者已核准本機 `npm run build`，但直接命令兩次都被 repository 的 DevWeave configured-command enforcement 拒絕，因此未繞過 guard；build 的 current 外部證據來自同一 HEAD 的四個 hosted Node jobs，全部通過。
- Python core suite仍保留 1 個既有 Windows symlink creation privilege skip；三個 Windows-only launcher tests 則已在本機與 hosted Windows 實跑，不屬於該 skip。
- `--max-parallel 3` 暴露 verifier evidence-recording 的 cross-write false negative；循序執行可穩定取得合格證據。這不影響產品或 GitHub CI 結果，但可另開 DevWeave engine work item 改善並行 ledger isolation。
- 共 45 筆 source-bound evidence 已正確 stale：包含 20 筆 pre-push records 與被 trace-complete rerun 取代的中途 records；本驗收只使用 `EVID-050`～`EVID-060` 作 machine gate proof。
- 一個 unrelated Wiki stale-source warning 保留；Hosted runner image、Action SHA 與 dependencies 日後改變時需新的受治理 run，不能沿用本次 17/17。
- Waiver：無。CI workflow、production CLI／Guard／hook semantics、dependency graph、lockfile、public API 與 current VSIX bytes：均未修改。

## 驗收結論

G1/G2 核准範圍內的四個 TASK 已完成。Node 20 的 quoted-glob 問題改為 explicit-file deterministic runner；Python POSIX failures 改以 canonical interpreter、平台原生 fixture 與 capability-bound Windows tests修正，沒有弱化 production trust 或 Guard semantics。Current controlled standard profile 7/7、AC/TASK targeted evidence 全綠，PR #1 hosted run 17/17，quality baseline、五頁 Wiki、index/log/seal 與 scope reconciliation均已對齊。

目前可交由使用者核准或拒絕 G3；核准前不執行 `approve acceptance`、`close`、commit、push、PR 或 merge。

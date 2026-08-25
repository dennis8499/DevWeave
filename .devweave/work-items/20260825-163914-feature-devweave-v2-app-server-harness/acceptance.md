# 功能驗收：DevWeave V2 app-server harness

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260825-163914-feature-devweave-v2-app-server-harness -->

## 驗證範圍與來源

- Risk/profile：`high`／feature；G1 與 G2 已由使用者核准，human G3 尚未核准。
- Immutable base ref：`3662d8622b46a1cab6931da988db3c4280def783`。
- 已驗證 UI code anchor：`c82c9e8023b209a7a063bf15eee69e4a67334ae2`；其後加入 completed-transition ExecPlan 的 finalizer guard與本 G3 候選文件，皆已由 V2/repository tests覆蓋。最終 UI/package evidence仍須在 source freeze後重綁。
- Codex provenance：CLI `0.149.0-alpha.4.3`，executable SHA-256 `21f44f04e70d41d011268863d5109f5d7fc2862c14f390083e39ca3398b5ca47`，291 個 generated schema files，schema SHA-256 `def4a7e9c01d3eaf697ad5a8ada283e6733c9b54892bc4e6928eb1132320d85a`。
- UI evidence：9/9 assertions、1 screenshot；report 綁定 run、code anchor、Codex version 與 schema hash，screenshot SHA-256 `02214188e66a9611d40655c3236fa3c066a6693abe9452c288950cc489fd83e0`，bounded log 中 secret 已 redacted。

## 驗證矩陣

狀態定義：`通過` 代表目前已有對應的 mechanical/rehearsal evidence；`阻擋` 代表不可用 mock 取代的 release evidence 尚缺；`G3 待切換` 代表 disposable-clone proof 已通過，但主工作樹必須等 human G3 才可執行 breaking finalizer。

| AC | Tasks | 狀態 | Evidence / 結果 |
| --- | --- | --- | --- |
| AC-001 | TASK-007, TASK-012 | 阻擋 | Scripted app-server lifecycle tests 通過，real initialize/thread/MCP probe 通過；仍缺會呼叫 Codex 服務的 model turn、steer/interrupt/resume 完整 live transcript。 |
| AC-002 | TASK-006, TASK-012 | 通過 | Doctor 以實際 absolute Codex path 完成 version/executable/schema provenance；missing/not-file/version/schema failure fixtures 均 fail closed。 |
| AC-003 | TASK-005, TASK-012 | 通過 | MCP transcript/adversarial tests 通過；real app-server thread inventory 只列出 exact 8 tools，cursor/`_meta`/unknown-field validation 與 scope guards 已對齊實際 protocol。 |
| AC-004 | TASK-005, TASK-006, TASK-008 | 通過 | MCP discovery 無 host-only aliases/passthrough；authenticated host bridge、forged role/replay/agent-host mutation tests 通過。 |
| AC-005 | TASK-002, TASK-008 | 通過 | Low/standard/high Gate、fingerprint invalidation、self/detached/max-three review policy tests 通過。 |
| AC-006 | TASK-003, TASK-012 | 通過 | Actual run branch 為 `devweave/20260825-163914-app-server-harness`；scoped phase commits存在，base ref 未移動，未 push/PR/merge/switch-back；dirty/detached/collision fixtures 通過。 |
| AC-007 | TASK-002, TASK-012 | 通過 | Typed ExecPlan、atomic store、revision/mutation idempotency、restart reducer fixtures 通過；runtime state 預設 ignored。 |
| AC-008 | TASK-002, TASK-005, TASK-008 | 通過 | PendingDecision option/custom/cancel/malformed/stale round-trip 與 same-run resume tests 通過。 |
| AC-009 | TASK-010, TASK-012 | G3 待切換 | Canonical docs navigation、link/topic/trace guards及 disposable final-tree check 通過；主樹在 G3 前刻意保留 legacy baseline/Wiki authority。 |
| AC-010 | TASK-003, TASK-011 | 通過 | `export-v1` byte-stable，記錄 21 closed work items／411 evidence files，input 未修改；raw V1 可由 immutable base/Git history回復。 |
| AC-011 | TASK-001, TASK-006 | 通過 | 六個 public CLI verbs、五個 versioned schemas、golden/unknown-field/version/error-code fixtures 通過。 |
| AC-012 | TASK-007, TASK-009 | 通過 | Extension event/controller/webview suites與 real VS Code smoke 通過；五個 accessible tabs 顯示 connection、run、plan、diff/tool、decision/Gate/verification/review/usage/diagnostics及 projection/stale 狀態。 |
| AC-013 | TASK-004, TASK-012 | 通過 | Verification DAG、selection、serial writers、`shell=False`、runtime executable hash、declared-effect reconciliation、stale/timeout/undeclared-write及 environment isolation tests 通過。 |
| AC-014 | TASK-008, TASK-012 | 阻擋 | Detached/max-three/critical-blocker controller tests 通過；仍缺 real detached reviewer thread transcript，以及 G3 point-cut 的 exactly-one isolated read-only reviewer verdict。 |
| AC-015 | TASK-001, TASK-011 | G3 待切換 | 2.0.0 version/package contract、9-entry VSIX candidate verifier與 disposable clean-cutover forbidden-path/command scan 通過；main finalizer 與最終 source-bound package 待 G3。 |
| AC-016 | TASK-002, TASK-005, TASK-006, TASK-008 | 通過 | Unknown method/field、forged role、stale revision、path/symlink/scope violation fixtures在 mutation 前拒絕並產生 bounded diagnostics。 |
| AC-017 | TASK-002, TASK-004, TASK-007 | 通過 | Canonical serialization、atomic replace/append、duplicate delivery及 crash-before/after-write replay tests 通過。 |
| AC-018 | TASK-004, TASK-009 | 通過 | Bounded metrics/log/diagnostic、secret redaction、reasoning discard、prompt non-persistence及 usage-unavailable/null semantics tests 通過。 |
| AC-019 | TASK-001, TASK-010 | G3 待切換 | Architecture fixture/checker涵蓋 root/module size、dependency direction、schema drift、docs links與 AC trace；disposable V2 final tree通過，main transition tree需 finalizer 後重跑 public `check`。 |
| AC-020 | TASK-009, TASK-012 | 通過 | Extension 113/113、typecheck/build及 real VS Code `1.131.0` smoke 通過；UI report 9/9、1 screenshot、有完整 provenance與 bounds。 |
| AC-021 | TASK-001, TASK-011, TASK-012 | 阻擋 | Windows x64 path/process/JSONL/filesystem/Git adapter tests 與 VS Code smoke 通過；因 real model-turn matrix尚未獲外部資料傳送授權，不宣稱 Windows certification；其他 OS 維持 unverified。 |
| AC-022 | TASK-003, TASK-011, TASK-012 | 通過 | Scoped commit chain、immutable base、V1 export、failure-preserving finalizer tests與 disposable-clone recovery rehearsal通過；系統未自動 reset/merge/push。 |

## Profile 證據

- V2 Python suite：64/64 通過。
- Repository contract：16/16 通過。
- Extension unit/DOM/security：113/113 通過；typecheck 與 production build 通過。
- Real VS Code Extension Host smoke：通過；empty-workspace 與 repository-workspace command registration 都已驗證。
- 2.0.0 package：candidate build/verify 通過，共 9 entries；最後 source freeze 後必須再建置並記錄最終 VSIX hash。
- Disposable cutover clone：V2 public check、V2 tests、schema-v2、forbidden V1 paths/commands、base-ref invariant與 clean tree全部通過。
- Formal release evidence 未完成：live Codex E2E、exactly-one isolated reviewer、human G3、main finalizer與 post-cutover full matrix。

## 基線更新

- `product.md` 加入 V2 app-server primary surface、exact MCP tools、2.0.0 clean cutover/recovery 與 certification blocker。
- `architecture.md` 加入實際 Codex protocol/schema observations、host/MCP boundary、ExecPlan authority、verification `env_allowlist` 與 hash-bound finalizer。
- `quality.md` 加入目前測試、real VS Code/UI evidence、Codex/schema provenance、disposable rehearsal與 remaining blockers。
- 以上三份 legacy baseline 只服務本次 G3；finalizer 後由 `ARCHITECTURE.md` 與 `docs/` 成為唯一長期 truth。

## Wiki 知識提升

Disposition candidate：`no-update`。V2 刻意取消 Wiki runtime authority，新的 durable knowledge 已寫入 `ARCHITECTURE.md` 與 `docs/{product,design,reliability,security,quality}.md`；不把 legacy clipboard/Wiki workflow提升為 V2 truth。Legacy Knowledge Review/close 必須在 G3 前經 machine CLI 記錄，actual finalizer 再依核准 manifest 移除 Wiki raw tree。

## 殘餘風險與 blockers

- Live test 會使用現有 Codex login/network，並把 bounded workspace-related context 傳到 Codex 服務；尚未取得這項明確授權，因此 runner 正確回報 blocked，而不是 mock pass。
- Codex `app-server` protocol 仍可能隨目前 alpha CLI 變動；generated schema hash、doctor、strict boundary parsers與 protocol regression tests是 drift detection seam。
- Cutover manifest 會因本 acceptance/baseline/legacy state 更新而 stale；必須在 G3 source freeze後重新產生，並只對 human G3 核准的 exact hash執行 finalizer。
- Formal reviewer 必須在 live evidence齊全、diff freeze後 exactly once 啟動；目前尚未啟動，不得預先消耗或重複 reviewer point-cut。

## 驗收結論

目前為「G3 尚不可核准」：19 項 AC 已有 mechanical 或 disposable-cutover evidence，AC-001、AC-014、AC-021 因 real Codex model-turn／detached-review／Windows certification evidence 缺少而 blocked。取得外部資料傳送授權並完成 live E2E後，才進入 exactly-one isolated high-risk review；修正 critical findings並重新驗證後，再向使用者提出 human G3。G3 核准前不會在主工作樹執行 breaking finalizer。

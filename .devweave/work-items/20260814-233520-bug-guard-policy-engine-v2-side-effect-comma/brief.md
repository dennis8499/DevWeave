# 工作摘要：建立 Guard Policy Engine v2 並修正 Side-effect Command Policy

<!-- DEVWEAVE:artifact=brief version=1 work=20260814-233520-bug-guard-policy-engine-v2-side-effect-comma kind=bug -->

## 問題與目標

DevWeave 目前把 configured command 的授權近似成 argv 比對，並以固定字串 prefix 判斷 read-only Bash；這無法證明 executable、cwd、phase、release context、環境或實際檔案變更符合治理宣告。G2 後未註冊的 side-effect Bash 也可能被放行，造成治理 hook 與 verification engine 的可信度缺口。相同 command 在 Guard、Verification Runner 與 G3 Acceptance 的判斷也可能分歧，讓非零或任意 expectation、舊 policy evidence、selective profile 與未宣告寫入被誤當成 gate evidence。

目標是建立嚴格 fail-closed 的單一 Verification Policy：以共用 Policy Evaluator 驗證每次執行，對 read-only command 使用 executable/subcommand argv grammar，對 registered command 使用 controlled executor、sandbox 與 postcondition；G2 凍結 Effective Verification Plan；evidence 綁定 plan/command/source/input/output digest 並由 engine 計算 `gate_eligible`。所有 deny、violation、snapshot、promotion 與 stale 結果都留下可追溯 evidence。成功訊號是使用者列出的七組 bug reproduction 與 P0 驗收案例全部得到預期結果，未知輸入與 guard 例外不會放行，連續三次 clean run 結果完全一致。

## 現況證據

### Wiki facts

- 已依 index-first 順序記錄 `wiki/index.md`、`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md` 與 `wiki/modules/vscode-extension.md` 的 content hash、source fingerprint 與 observed status。
- 現有頁面描述 optional command metadata、argv/selection、release-only dependency 與 hook boundary，但沒有完整 CommandPolicy v2、typed argv grammar、canonical executable/cwd、explicit release context、snapshot/sandbox、postcondition promotion 或 side-effect waiver。

### Source-backed facts

- `.agents/skills/devweave/scripts/guard.py` 的 `READ_ONLY_PREFIXES` 以字串 prefix 判斷命令；`_matches_configured_command` 只把 shell tokens 與 project 的 `argv` 直接比較，沒有 cwd、真實 executable、環境、phase 或 release context 驗證。
- `handle_hook` 在有 binding 且通過 G2 後，對非 read-only、非 configured、非 Wiki 命令落到 `return None`；因此 arbitrary side-effect Bash 沒有預設拒絕邊界。
- `.agents/skills/devweave/scripts/devweave_core.py` 目前只驗證 `affected_paths`、`writes`、`outputs`、`release_only` 等 optional metadata，並以 `subprocess.run(..., shell=False)` 在設定 cwd 執行，沒有完整 policy parse、executable registry、前後 filesystem/Git snapshot 或 output postcondition。
- `_record_verification_execution()` 目前把 `expect=nonzero`/`any` 的 expectation match 記為 `status=passed`，沒有 engine-derived `gate_eligible`；G3 以 raw passed evidence 覆蓋 required command 與 AC。
- profile runner 依自身 selection/parallel 邏輯執行，G3 直接讀 project required set，沒有共用 G2 frozen Effective Verification Plan；command definition、project policy 與 source fingerprint 也未共同形成 evidence currentness。
- `command set/remove` 可在 active Work Item 期間直接改 project policy，沒有使既有 G2、G3、plan 與 evidence deterministic stale；profile runner 也沒有禁止 writes command 與 writes:none command 以不安全順序並行，或檢查 undeclared writes。
- `.devweave/project.json` 的 `extension-package` 是 `writes: tracked-artifact` 且 `release_only: true`；在舊流程中只靠 command metadata/profile selection，未要求明確 release context 或 sandbox promotion。
- `.codex/hooks.json` 已固定 exact `^(Bash|apply_patch|Edit|Write)$` matcher；本工作不改變 matcher，而是強化其 guard decision 與 engine controlled executor。

### Inferences

- 根因是 command identity、execution context 與 observed effects 被拆成互不相連的 checks；繼續增加 shell regex 無法可靠涵蓋 wrapper、symlink/junction、環境替換與隱藏輸出。
- 可靠的控制點應是 typed policy admission，加上隔離執行、全樹 filesystem/Git snapshot、declared output/work scope postcondition 與 evidence，而不是從任意 shell string 猜測寫入路徑。

### Unresolved gaps

- 尚未確認新的 policy schema 在現有所有 tests、Windows wrapper 與 extension verification 命令中的完整相容性；這是 G2 design 與 implementation 的驗證責任。
- 目前沒有可接受的 legacy command-policy fallback；本 work item 將同一個 project config 一次遷移至 `command_policy_version: 2`，parse failure 維持 fail closed。
- 尚未在正式 regression suite 中驗證 BUG-01～BUG-07；G1 必須先以 temporary/cache harness 留下每一項 source-backed failure，G2 後才轉成 tracked tests。

## 範圍

範圍包含：

- `.agents/skills/devweave/scripts/command_policy.py`、`guard.py`、`devweave_core.py`、`devweave.py` 的 single Policy Evaluator、CommandPolicy v2、typed grammar、controlled executor、Effective Verification Plan、snapshot/postcondition、release context、waiver/evidence、digest/stale 與 fail-closed errors。
- `.devweave/project.json` 的 v2 command policy、trusted executable registry、profiles/command metadata；整體 project/state schema 仍維持 v1。
- G2 frozen plan 與 evidence eligibility 的 state/ledger typed mutation path；project command policy mutation 對 active Work Item 的 deterministic stale contract；Doctor/Project validation 與 G3 validator 的同源判斷。
- G1/G2 相關 reference、CLI contract、repository contract 與 tests，覆蓋 Windows/POSIX path、wrapper、symlink/junction、nested repository、Unicode whitespace、shell operator、environment/config/alias/preprocessor injection。
- `README.md`、`docs/使用手冊.md`、`.devweave/baseline/architecture.md`、`.devweave/baseline/quality.md` 與 root Wiki 的治理說明；Wiki 只在 verification 依 knowledge plan 更新。

實際寫入輸出只允許經 typed controlled executor 的 declared outputs；tracked-artifact 需在 temporary filesystem sandbox 完成 postcondition 後才可 promotion，且 promotion path 必須在 work scope。

## 非目標

- 不改變 extension 的產品功能、Control Center UI、VSIX 版本或公開 host mode；只調整其使用的 governance command contract。
- 不以 regex 寫出任意 shell string 的完整寫入路徑推理器，不允許 shell operator、alias、response file、preprocessor 或環境替換成為隱性授權。
- 不建立 Git branch、commit、push、remote issue、deployment 或 production instrumentation；不以 Git worktree mutation 取代 temporary sandbox。
- 不將 Work Item brief/requirements/design/plan artifact 的 typed mutation path 改成 side-effect shell command；不改動既有 DevWeave ledger 的 schema version 或直接編輯 JSON/JSONL ledger。
- 不承諾跨平台 runtime 的完整認證；本次重點是目前 Windows host 與 repository 已宣告的 POSIX/Windows adversarial policy seams。

## 風險

風險等級：high

主要風險是治理收緊後誤拒絕既有 verification command，或 sandbox/promotion 與 Windows executable resolution 不一致而阻斷 G3。這是 security、scope 與 data-integrity 風險；任何未知 policy、parse exception、cwd/executable mismatch、未宣告 output 或 snapshot error 都必須 fail closed。可逆性由 temporary sandbox、current artifact 保留、postcondition 前不 promotion 與 machine evidence 提供；不允許以人工跳過取代 evidence。

基線為目前 project schema/state schema v1、既有 command profiles、`python -B -m unittest discover -s tests -v`、extension test/typecheck/package/smoke 與 repository contract。若必要的 ad-hoc side-effect 無法納入 registered typed policy，只能使用明確、窄範圍、含 canonical executable/argv/cwd/outputs/timeout/scope/actor/expiry/digest 的 one-shot waiver，並仍經 controlled executor；本 G1 不預先授予 waiver。

## Profile 補充

本 work item 採 bug profile：

- Expected：G2 前所有 `writes != none` 的 configured command Deny；release-only 必須有 explicit release context；完整 policy identity 與 execution snapshot/postcondition 通過才可執行或 promotion；未知 command/subcommand/flag、shell operator、wrapper/環境替換與 guard exception fail closed。
- Actual：舊 guard 以 prefix/argv-only 判定，configured write command 可在未有完整 context 時進入 executor，G2 後 arbitrary Bash 可能放行，verification 不比較 actual changed paths 與 declared outputs。
- Root-cause hypothesis：舊系統沒有 single typed policy admission seam，command selection metadata 與 process execution、observed filesystem effects、evidence lifecycle 分離。
- Reproduction：將以 DevWeave `evidence add --kind reproduction` 記錄目前 source-backed failure，至少涵蓋 read-only prefix bypass、configured direct Bash、policy drift、nonzero/any eligibility、profile/G3 mismatch、parallel write ordering 與 undeclared writes。

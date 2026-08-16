# 需求與驗收條件：建立 Guard Policy Engine v2 並修正 Side-effect Command Policy

<!-- DEVWEAVE:artifact=requirements version=1 work=20260814-233520-bug-guard-policy-engine-v2-side-effect-comma -->
<!-- Requirements below use contiguous unique REQ/NFR/AC identifiers. -->
## 假設與限制

### 已回答的 material decisions

- 採 strict v2 migration：不保留舊的 argv-only 或 optional-policy fallback；同一 Work Item 更新現有 commands、fixtures 與 tests。
- registered command 的 write execution 採 typed controlled executor，並要求明確 release context；不以 command ID 或 profile 推斷 release。
- writes command 使用 temporary filesystem sandbox；不建立或修改 Git branch/worktree，full-tree filesystem 與 Git snapshot 都納入比較。
- read-only grammar 只支援 Git、rg 與明確必要的 exact PowerShell read commands；unknown command/subcommand/flag 一律拒絕。
- ad-hoc side-effect 只能以 typed one-shot human waiver/evidence 明確授權，需 canonical executable/argv/cwd/outputs/timeout/work scope/actor/expiry/digest，且仍由 controlled executor 執行。
- Windows `.cmd`/`.bat` wrapper 只有在 trusted executable registry 明確登錄且 hash/path 相符時可用；不可把未登錄 wrapper 當成 direct read-only executable。
- policy violation 分層：pre-run denial 不啟動 process 並回傳 exit 2；post-run undeclared effect 或 writes:none effect 產生 evidence、verification failure exit 4，兩者都阻擋 G3。
- executable trust 使用 trusted registry 的 canonical absolute path 與 content hash；PATH lookup 必須解析到同一真實路徑/hash。
- 新增 `command_policy_version: 2`；project/state/ledger 的既有 schema version 仍為 1。

## 需求與驗收條件

## REQ-001: 建立完整且嚴格的 CommandPolicy v2

- Priority: must
- Acceptance: AC-001, AC-008
- Description: 每個 configured command 必須解析為 typed `CommandPolicy`，包含 `id`、`resolved_executable`、`argv_schema`、`cwd`、`min_phase`、`allowed_risk`、`writes`、`outputs`、`release_only`、`network`、`env_allowlist`、`timeout`；必填欄位、enum、path、grammar 與 schema version 不合法時整批 fail closed，不得回退 argv-only。

## REQ-002: 驗證 execution identity 與 context

- Priority: must
- Acceptance: AC-002, AC-003, AC-004, AC-010
- Description: 執行前必須確認目前 phase/risk、explicit release context、canonical cwd、trusted executable real path/hash、allowlisted environment、network policy 與 timeout。cwd 必須與 policy canonical value 完全相符且解析後仍在 repository 內；resolved executable 不得被 PATH shadowing、相對路徑、symlink/junction 或 wrapper 逃逸替換。G2 前任何 `writes != none` 的 configured command 必須 Deny。

## REQ-003: 以隔離執行與 observed effects 控制寫入

- Priority: must
- Acceptance: AC-005, AC-006, AC-007, AC-012
- Description: controlled executor 必須在執行前後取得 full-tree filesystem 與 Git snapshot，計算 `actual_changed_paths` 並與 `declared_outputs`、`work_scope` 比較。writes:none 只要新增檔案或修改 tracked state 即是 policy violation；declared output 以外的變更必須 fail 並保留 evidence。tracked-artifact 必須先在 temporary sandbox 完成 postcondition，再依 declared output promotion，不能直接污染 working tree。

## REQ-004: 以 typed argv grammar 取代 read-only prefix

- Priority: must
- Acceptance: AC-009, AC-010
- Description: 移除 `READ_ONLY_PREFIXES`。`git status`、`git log`、`git diff`、`git branch` 與 `rg` 各自使用明確 executable/subcommand grammar；只允許列舉的 safe flags，`git diff` 強制 `--no-ext-diff` 與 `--no-textconv` 並拒絕 `--output`，`git branch` 只接受 exact `--show-current`，rg 拒絕 `--pre`、`--pre-glob`、未知 flag、config/preprocessor/environment-driven behavior。unknown command/subcommand/flag fail closed。

## REQ-005: 收緊 Bash 分類與 typed mutation boundary

- Priority: must
- Acceptance: AC-011, AC-012
- Description: post-G2 Bash 分為 grammar-proven read-only、registered command 與 ad-hoc side-effect。read-only 只能由 argv policy 直接允許；registered command 只能透過 DevWeave controlled executor；ad-hoc side-effect 預設拒絕，必要時須有窄範圍 typed one-shot waiver/evidence。brief、requirements、design、plan artifact 維持專門 typed mutation path，不透過 side-effect shell command 放行。

## NFR-001: Fail-closed 與可重現性

- Priority: must
- Acceptance: AC-008, AC-013
- Description: guard exception、JSON/argv parse failure、missing policy、snapshot error、unknown input、環境不一致與 promotion/postcondition failure 均不得放行；相同 repository、policy、context 與 test input 連續三次 clean run 的 decision、exit class、changed-path/output/evidence 摘要必須完全一致。

## NFR-002: Evidence 與安全邊界可稽核

- Priority: must
- Acceptance: AC-005, AC-006, AC-012, AC-013
- Description: Deny、policy violation、snapshot、postcondition、promotion、waiver 與 controlled execution 必須保存 work-attributed、source-bound、bounded evidence，不保存 secrets、完整環境或任意未界定輸出；任何 violation 都使 verification/G3 不可通過。

## AC-001: G2 前 configured write command 被拒絕

- Requirement: REQ-001, REQ-002
- Scenario: Given current phase is before G2 and configured command `extension-package` has `writes: tracked-artifact`, when the command is requested, then no process starts, result is `Deny`/exit class 2, and the reason identifies the phase/write policy.

## AC-002: release-only command 需要明確 release context

- Requirement: REQ-002
- Scenario: Given a release-only policy and no explicit release context, when the same command is requested from any profile or by its command ID, then it is denied.

## AC-003: cwd mismatch 被拒絕

- Requirement: REQ-002
- Scenario: Given identical argv and executable but a cwd different from the canonical policy cwd, when execution is requested, then it is denied; a nested repository cwd is not treated as equivalent.

## AC-004: executable shadowing 被拒絕

- Requirement: REQ-002
- Scenario: Given identical argv but an executable resolved from another PATH entry, a relative path, a POSIX symlink, or an untrusted Windows `.cmd`/`.bat` wrapper, when execution is requested, then it is denied unless the exact trusted registry path and hash match.

## AC-005: 未宣告 output 產生 violation 並保留證據

- Requirement: REQ-003, NFR-002
- Scenario: Given a registered command declares outputs A only, when isolated execution changes A and undeclared path B, then the command fails with post-run policy violation/exit class 4, evidence records actual B, and B is not promoted.

## AC-006: writes:none 產生檔案即失敗

- Requirement: REQ-003, NFR-002
- Scenario: Given a writes:none command, when it creates a new file or changes tracked state anywhere in the sandbox/repository snapshot, then verification fails closed, records the changed path evidence, and does not report success.

## AC-007: tracked-artifact 只在 postcondition 後 promotion

- Requirement: REQ-003
- Scenario: Given a tracked-artifact command with declared outputs and a valid postcondition, when it runs in the temporary sandbox, then only declared in-scope outputs are promoted after postcondition; failed postcondition leaves the current artifact/worktree unchanged.

## AC-008: exception、parse failure 與 unknown policy fail closed

- Requirement: REQ-001, NFR-001
- Scenario: Given malformed policy JSON, invalid argv grammar, missing trusted executable, guard exception, snapshot exception, unknown command/subcommand/flag, or malformed shell tokenization, when admission or execution occurs, then it is denied or failed and never falls through to allow.

## AC-009: read-only grammar adversarial matrix

- Requirement: REQ-004
- Scenario: The matrix rejects `git diff --output=...`, `git diff --ext-diff`, `git -c diff.external=...`, `rg --pre ...`, `rg --pre-glob ...`, unknown flags, `GIT_EXTERNAL_DIFF`, Git pager/external helper, ripgrep config/preprocessor, response/alias expansion, and environment-based executable replacement; known-safe status/log/diff/branch/rg forms remain allowed.

## AC-010: shell/path/Unicode adversarial matrix

- Requirement: REQ-002, REQ-004
- Scenario: The matrix rejects shell operators, newline, Unicode whitespace, quoted or relative executable, POSIX symlink executable, untrusted Windows wrapper, and nested repository cwd; parsing never normalizes these into a different allowed command.

## AC-011: Bash categories 與 typed artifact mutation

- Requirement: REQ-005
- Scenario: Given a bound work item after G2, grammar-proven read-only is allowed directly, registered command is allowed only through controlled executor, ad-hoc side-effect is denied by default, a narrowly matching one-shot waiver is required for exceptional execution, and work-item Markdown artifacts remain writable only through their dedicated typed mutation path.

## AC-012: policy violation blocks verification/G3

- Requirement: REQ-003, REQ-005, NFR-002
- Scenario: Any pre-run deny, post-run changed-path mismatch, writes:none effect, failed postcondition, or failed promotion produces machine evidence and prevents the verification/build/acceptance gate from becoming current.

## AC-013: 三次 clean run 結果一致

- Requirement: NFR-001, NFR-002
- Scenario: With the same clean repository, policy, context, PATH, environment allowlist and adversarial test set, run the complete guard/policy suite three consecutive times; decision, exit class, changed paths, declared outputs and evidence summary are byte-for-byte/deterministically identical.

## REQ-006: 單一來源的 Verification Policy Evaluator

- Priority: must
- Acceptance: AC-014, AC-019, AC-025
- Description: `guard.py`、`verify --command`、`verify --profile`、G3 Acceptance、Doctor/Project validation 與 command mutation validation 必須呼叫同一個 Policy Evaluator。Evaluator 輸入至少包含 Work Item、phase、gate status、session binding、command definition、argv、cwd、writes、outputs、affected paths、release stage、dependency closure 與 current project policy digest，輸出 canonical decision/reason code；入口不得複製或弱化判斷邏輯。

## REQ-007: G2 凍結 Effective Verification Plan

- Priority: must
- Acceptance: AC-015, AC-018
- Description: G2 核准時由 engine 建立並以既有 typed state mutation path 凍結 Effective Verification Plan。Plan 必須包含 `plan_id`、`plan_digest`、project policy digest、每個 command definition digest、required/selected/skipped/not-applicable 集合與理由、dependency closure、stage、writes/output/exclusive policy、expected success exit codes 與 gate eligibility policy。Runner 與 G3 只能讀取同一 plan；selective path 不得另建未綁定 plan 的 required set。

## REQ-008: Digest-bound evidence 與 engine-derived eligibility

- Priority: must
- Acceptance: AC-016, AC-017, AC-026
- Description: 每筆 verification evidence 必須綁定 Effective Plan digest、command definition digest、argv、cwd、current source fingerprint、input/output fingerprint、實際 exit code、actual changed paths、declared outputs、execution channel 與 engine 計算的 `gate_eligible`/reason。Caller 不得指定 `gate_eligible`；command definition、project policy 或 source fingerprint 不符時 evidence deterministic stale/拒絕。

## REQ-009: Configured command 的唯一受控執行邊界

- Priority: must
- Acceptance: AC-019, AC-020
- Description: configured verification command 必須由 DevWeave executor 以 `shell=false`、固定 canonical argv/cwd、bounded timeout、policy evaluation、output reconciliation 與 evidence recording 執行。相同 argv 的一般 Bash direct call 不得取得 execution authority，必須 deny 並提示 `devweave verify`；G2 前 `writes != none`、release-only、outputs 或特定 cwd command 不得正式執行。

## REQ-010: Project policy mutation 的 deterministic stale contract

- Priority: must
- Acceptance: AC-016, AC-021
- Description: project command policy 的新增、修改與刪除必須透過 Router/typed mutation path 比較 old/new policy digest；在 active Work Item 期間允許 controlled mutation，但所有受影響 Work Item 的 G2/G3 gate、Effective Plan、required evidence 與 source-bound command evidence 必須 deterministic stale，不能靜默繼續使用舊定義。

## REQ-011: Execution stage、dependency 與 parallel safety

- Priority: must
- Acceptance: AC-022, AC-023
- Description: runner 必須使用 Effective Plan 的 dependency closure 與 execution stage；writes command 依 dependency 順序 serial 執行，writer stage 完成後凍結 candidate fingerprint，只有 `writes=none` command 可平行。共享 output boundary 自動形成 exclusive group 或拒絕不安全設定；每筆 command 前後比較 repository state，未宣告變更必須 failed。

## REQ-012: Cross-shell read-only allowlist

- Priority: must
- Acceptance: AC-024, AC-027
- Description: read-only 判斷必須使用 argv-based allowlist 或同等 typed parser。POSIX、Windows CMD、PowerShell 的 operator、command substitution、expression invocation、redirection、未知 flag、output-producing flag、config/helper/preprocessor injection 與無法安全 parse 的輸入一律 fail closed；既有明確安全 read-only command 維持可用。

## REQ-013: Doctor、atomic machine state 與一致性契約

- Priority: must
- Acceptance: AC-025, AC-026, AC-028, AC-029, AC-030, AC-031, AC-032
- Description: Doctor 必須檢查 policy version/digest、command metadata、dependency、outputs、writes、trusted executable 與 profile/plan consistency；新增 machine state 必須使用 atomic write 並禁止直接編輯 state/events/evidence ledger。Contracts、Skill、AGENTS、README、Wiki 與實際 engine 行為必須一致，並由完整測試、extension checks、diff check 與 high-risk independent review 驗證。

## NFR-003: Gate evidence integrity

- Priority: must
- Acceptance: AC-017, AC-018, AC-020, AC-021, AC-022
- Description: G3 Required Command、AC coverage 與 Required Evidence Kind 只能使用 `gate_eligible=true` 且 plan/command/source digest current 的 evidence。`expect=nonzero`、`expect=any`、reproduction、diagnostic、failed、timeout、execution error、undeclared writes、stale source 或 digest mismatch 永遠不可 gate-eligible。

## NFR-004: Policy lifecycle determinism

- Priority: must
- Acceptance: AC-015, AC-016, AC-018, AC-021, AC-023
- Description: 相同 repository、policy、plan、context 與 input 下，Runner 與 G3 必須得到相同 selected/skipped/not-applicable、plan digest、decision、exit class、changed paths 與 eligibility；policy mutation、source change、definition drift 的 stale 邊界不得依執行順序漂移。

## NFR-005: Atomicity and bounded execution

- Priority: must
- Acceptance: AC-022, AC-026, AC-032
- Description: executor、promotion、evidence、plan 與狀態寫入均須 bounded、可回復且 atomic；postcondition 前不污染 current artifact，snapshot/error/promotion failure fail closed，不得以 direct ledger edit 或未界定 shell fallback 修復。

## AC-014: 所有入口使用同一 Policy Evaluator

- Requirement: REQ-006
- Scenario: Given the same command, argv, cwd, Work Item phase/risk, gate status, session, release context and policy digest, Guard, `verify --command`, `verify --profile`, Doctor, command mutation validation and G3 must return the same canonical decision/reason code; configured direct Bash is denied at the Guard boundary.

## AC-015: G2 建立並凍結 Effective Verification Plan

- Requirement: REQ-007, NFR-004
- Scenario: Given a Work Item approved at G2, state contains a plan ID/digest, project policy digest, per-command definition digests, required/selected/skipped/not-applicable reasons, dependency closure, stage and eligibility policy; changing the live project policy without a controlled stale transition cannot leave that plan current.

## AC-016: Command definition/policy drift 使舊 evidence stale

- Requirement: REQ-008, REQ-010, NFR-003, NFR-004
- Scenario: Given passing evidence for a command, changing any argv, cwd, writes, outputs, depends_on, timeout, release policy or project policy digest makes the old evidence and affected G2/G3 plan deterministic stale; G3 rejects it even when command ID is unchanged.

## AC-017: expectation 與 evidence eligibility 分離

- Requirement: REQ-008, NFR-003
- Scenario: Given a non-zero command with `--expect nonzero`, or any-result command with `--expect any`, the execution may be useful reproduction/diagnostic evidence, but engine sets `gate_eligible=false`; it cannot satisfy required verification, AC coverage, regression evidence or G3 acceptance.

## AC-018: Runner 與 G3 重用完全相同的 plan

- Requirement: REQ-007, NFR-003, NFR-004
- Scenario: Given a selective standard profile containing release-only, legacy, unrelated and dependent commands, Runner returns selected/skipped/not-applicable from the frozen plan and G3 accepts exactly that same set and plan digest; G3 does not reconstruct a broader required set from project metadata.

## AC-019: Configured command 不得 direct Bash bypass

- Requirement: REQ-006, REQ-009
- Scenario: Given a configured command with writes, release-only, outputs or canonical cwd metadata, an argv-identical direct Bash request is denied regardless of binding/G2 status/cwd spelling, with a `devweave verify` handoff; only the controlled executor can start the process.

## AC-020: G2 前禁止正式 side-effect verification

- Requirement: REQ-009
- Scenario: Given an unbound or pre-G2 Work Item, a configured command with `writes != none`, `release_only=true`, outputs or restricted cwd is denied before process start and produces no gate-eligible evidence.

## AC-021: Policy mutation 產生 deterministic stale

- Requirement: REQ-010, NFR-003, NFR-004
- Scenario: Given an active Work Item with current G2/G3/evidence, a Router-mediated command add/set/remove updates the policy digest and marks every affected plan, gate and evidence stale; a mutation cannot silently preserve current status.

## AC-022: writer stage 與 observed effect boundary

- Requirement: REQ-011, NFR-005
- Scenario: Given a build writer and a writes:none test with no declared dependency, runner serializes or rejects the unsafe graph; it freezes candidate fingerprint after writer completion, compares before/after state for every command, and undeclared writes fail without promotion.

## AC-023: shared output boundary 形成 exclusive safety

- Requirement: REQ-011, NFR-004
- Scenario: Given two commands whose declared outputs overlap or whose actual output boundary is shared, the plan assigns an exclusive group or rejects the configuration; a writes:none command never runs concurrently with an active writer on that boundary.

## AC-024: read-only prefix/substitution/operator bypass 全部 fail closed

- Requirement: REQ-004, REQ-012
- Scenario: `git status & echo`, `git status $(...)`, backticks, `git diff --output`, unknown/helper flags, PowerShell expression invocation/chaining, CMD/POSIX equivalents and redirection are denied by payload grammar without executing the payload; known-safe exact reads remain allowed.

## AC-025: Doctor 與 mutation validator 檢查完整 policy

- Requirement: REQ-006, REQ-013
- Scenario: Doctor and command mutation validation report missing/invalid policy version, trusted executable/hash, dependency closure, cwd, writes, outputs, release metadata or digest consistency as machine failures rather than allowing a legacy/partial command.

## AC-026: evidence 欄位完整且由 engine 計算

- Requirement: REQ-008, REQ-013, NFR-003, NFR-005
- Scenario: Each recorded verification execution contains plan/command/source/input/output fingerprints, argv/cwd, actual exit code, declared/actual paths, execution channel and engine-derived eligibility; caller-supplied eligibility is ignored or rejected and state/ledger writes are atomic.

## AC-027: Windows/POSIX read-only 行為一致

- Requirement: REQ-012
- Scenario: Equivalent CMD, PowerShell and POSIX shell operator, substitution, redirection, unknown-flag and wrapper payloads receive the same fail-closed policy result; no platform-specific parser normalizes an unsafe payload into an allowed argv.

## AC-028: full Python regression suite 通過

- Requirement: REQ-013
- Scenario: `python -B -m unittest discover -s tests -v` passes after the regression conversion without weakening existing safe read-only or `shell=False` verification assertions.

## AC-029: extension verification 經 controlled executor

- Requirement: REQ-009, REQ-011, REQ-013
- Scenario: extension typecheck/tests/package/smoke execute through the registered DevWeave executor with policy/evidence/plan fields; package requires explicit release context and promotes only declared outputs.

## AC-030: repository contract and diff hygiene

- Requirement: REQ-013
- Scenario: repository contract tests, Doctor/hook launcher checks and `git diff --check` pass; no direct state/events/evidence ledger edits are introduced.

## AC-031: high-risk independent review

- Requirement: REQ-013
- Scenario: Before G3, exactly one isolated read-only independent review is run through the Router; every Critical finding is resolved or explicitly handled before acceptance validation.

## AC-032: documents and Wiki match engine behavior

- Requirement: REQ-013, NFR-005
- Scenario: README, Contracts, Skill, AGENTS, Wiki and baseline describe the same evaluator, frozen plan, evidence eligibility, executor boundary, mutation stale and write reconciliation behavior; Knowledge Review records promote/no-update and seals affected pages.

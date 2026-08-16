# 系統設計：建立 Guard Policy Engine v2 並修正 Side-effect Command Policy

<!-- DEVWEAVE:artifact=design version=1 work=20260814-233520-bug-guard-policy-engine-v2-side-effect-comma -->

## 設計摘要

本方案把 Guard Policy Engine v2 做成一個由 `command_policy.py` 擁有的 deep module，讓 policy model、admission、typed argv grammar、canonical path/executable trust、environment normalization 與 controlled execution observation 有單一權威 seam。`guard.py` 是 Codex PreToolUse payload adapter；`devweave_core.py` 是 Work Item、profile selection、snapshot/evidence 與 gate coordinator；`devweave.py` 是 typed CLI adapter。三者不各自猜測 command 是否安全。

project schema 維持 v1，新增 root-level `command_policy_version: 2` 與 `trusted_executables`。每個 configured command 以完整 `CommandPolicy` 表示：

```json
{
  "id": "extension-package",
  "resolved_executable": "C:/Program Files/nodejs/npm.cmd",
  "argv_schema": {"kind": "exact", "tokens": ["run", "package"]},
  "cwd": "vscode-extension",
  "min_phase": "implementation",
  "allowed_risk": ["low", "standard", "high"],
  "writes": "tracked-artifact",
  "outputs": ["vscode-extension/dist", "vscode-extension/devweave-control-center-0.2.3.vsix"],
  "release_only": true,
  "network": "deny",
  "env_allowlist": ["PATH", "SystemRoot", "TEMP", "TMP"],
  "timeout": 300
}
```

`argv_schema.kind=exact` 的 `tokens` 不含 executable；executor 永遠以 trusted canonical executable 加上 tokens 建立 `argv`，不經 shell。read-only Git/rg/必要 PowerShell command 使用 code-owned typed grammar，不再使用 `READ_ONLY_PREFIXES`，也不把它們當成 registered write command。

關鍵不變量：未知 policy/command/subcommand/flag、parse exception、非 canonical cwd、未登錄或 hash 不符 executable、缺少 explicit release context、phase/risk 不符、非法環境與 snapshot/postcondition error 一律 fail closed；G2 前 `writes != none` 一律 Deny；registered command 不可由任意 Bash 直接執行；Work Item artifacts 仍只走既有 typed patch seam。

## 選項比較

### 選項 A：延伸現有 argv 比對與 prefix regex

拒絕。它能修補少數 flag，卻無法把 cwd、真實 executable、symlink/junction、環境、release context 與實際 output effect 綁在同一個 decision，也無法安全推理任意 shell string 的寫入路徑。

### 選項 B：完全依賴外部 OS/container sandbox

拒絕作為唯一方案。外部 sandbox 可隔離 process，但會引入目前 repository 未宣告的 runtime/dependency、Windows/POSIX 行為差異與難以追溯的 promotion seam；它也不能取代 typed argv grammar 與 policy evidence。

### 選項 C：stdlib controlled executor + typed policy + temporary full-tree sandbox（選定）

選定。policy admission 先以純 deterministic seam 驗證 identity/context，writes command 再由 controlled executor 在 temporary full-tree sandbox 執行，前後比較 filesystem/Git snapshot，通過 postcondition 後只 promotion declared outputs。這保留目前 Python/Windows runtime 邊界、可用 fake runner 做 unit test，並將未宣告效果變成可觀測 failure；代價是 full-tree copy/hash 有效能成本，且 `network: deny` 是 policy/environment boundary，不冒充 OS-level network firewall。

## 介面與資料流

### Module、interface 與 seam

- `command_policy.py`：`TrustedExecutable`、`CommandPolicy`、`ExecutionContext`、`PolicyDecision`、`ExecutionObservation` dataclass；`load_command_policies()`、`admit_command()`、`parse_shell_argv()`、`evaluate_read_only()`、`resolve_trusted_executable()`、`build_sanitized_environment()`、`snapshot_tree()`、`diff_snapshots()` 與 `run_in_sandbox()`。此 module 不依賴 Work Item ledger，錯誤以 typed `PolicyError` 回傳。
- `guard.py`：只負責 hook payload decode、repo/session lookup 與 path mutation boundary。read-only Bash 交給 `evaluate_read_only()`；configured command/ad-hoc side-effect 一律回傳 deny；guard exception 仍輸出 deny JSON，維持 exact hook matcher 與 exit-0 policy-result boundary。
- `devweave_core.py`：`load_project()` 要求 v2 model；verification coordinator 建立 `ExecutionContext`（current phase/risk、invocation cwd、explicit release context、work scope），呼叫 controlled executor，將 observation/decision 放入 bounded evidence；profile selection 保留 required/depends/affected path，但不再用 profile 或 command ID 推斷 release。
- `devweave.py`：`verify` 增加 typed `--release-context`，`command set` 要求 canonical `--resolved-executable`/exact argv schema inputs；CLI envelope 不變。side-effect waiver 增加 typed target digest/expiry/identity 欄位，waiver 只允許 controlled executor。

### Policy model 與 canonicalization

`trusted_executables` 以 canonical absolute path、SHA-256、platform/kind（direct 或 explicitly registered wrapper）保存。load 時解析 real path、拒絕 symlink/reparse-point escape、重新 hash 並要求與 registry 相符；PATH lookup 只能得到同一 canonical path/hash。`.cmd`/`.bat` 只在 registry 明確登錄時可作 configured executable，read-only grammar 不接受 wrapper、相對路徑或 quoted executable。

`cwd` 與 output/work-scope 都先以 repository root 的 canonical path 解析；cwd 的每一個 ancestor 不得是 symlink/junction/reparse point，解析結果必須在 repository 內，且 canonical repo-relative value 必須與 policy 完全相符。Nested repository cwd、`..`、absolute repository escape 與不同 spelling 都拒絕。`env_allowlist` 只複製列名環境；executor 另外清除 Git external diff/pager/config、ripgrep config/preprocessor 與 executable replacement 變數。

### Data flow 與 state transition

1. `verify --command/--profile` 讀取 v2 project 與 bound Work Item；profile 只決定 selection，不產生 release authority。
2. admission 驗證 command policy、phase/risk、explicit release context、cwd、executable/hash、network/env/timeout，以及 G2 前 writes rule。
3. read-only command 由 grammar direct allow，registered command 進入 temporary sandbox；pre-run snapshot 保存 deterministic tree hash、Git status/diff/tracked-state hash。
4. `subprocess.run(argv, shell=False, cwd=sandbox_cwd, env=sanitized_env, timeout=policy.timeout)` 執行；不執行 arbitrary shell string。
5. post-run snapshot 產生 `actual_changed_paths`、Git state delta、`declared_outputs`、`work_scope` 與 postcondition result。writes:none 的任何 delta、未宣告 output、scope 外變更或 tracked-state 改變都是 violation。
6. 只有 declared outputs 全部在 scope 內且 postcondition 通過，才用 atomic promotion adapter 將 sandbox bytes 帶回；失敗則丟棄 sandbox、保留 current artifact/worktree，並先記錄 evidence。
7. evidence 保存 policy fingerprint、context、decision、snapshot/output摘要、exit class、stdout/stderr bounded log 與 promotion result；不保存完整環境或 secrets。

## 失敗模式與回復

### Pre-run deny（exit class 2）

malformed project/policy、unknown input、argv parse failure、missing trusted executable、hash/path mismatch、cwd escape、phase/risk/release/env/network 不符、G2 前 write command 或未授權 Bash 都不啟動 process。Guard 直接 deny；CLI 回傳 machine error/policy decision，不能 fall through 到舊 allow path。

### Post-run failure（exit class 4）

timeout、process/OSError、snapshot exception、writes:none effect、tracked-state effect、undeclared output、scope mismatch、postcondition failure 或 promotion failure 都是 verification failure。controlled executor 不 promotion，保留 bounded failure evidence 與 deterministic reason code；temporary sandbox 由 context manager 清理。

### Rollback 與降級

promotion 先在同一 parent 建立 private backup/staging，所有 declared targets 成功 replace 後才刪除 backup；任一 replace 失敗立即 restore current bytes。不可 fallback 到 direct working-tree execution。若 snapshot/evidence ledger 寫入失敗，視為 fail closed 並禁止 promotion。唯一例外是明確 typed one-shot `side-effect` waiver，但它仍須 exact policy identity、canonical argv/cwd、output/scope、timeout、actor、expiry、digest，不能略過 sandbox 或 postcondition。

觀測使用 stable `policy_decision`、`failure_class`、`actual_changed_paths`、`declared_outputs`、`work_scope`、`snapshot_digest`、`promotion` 與 bounded metrics；temporary directory 名稱不進 fingerprint，確保連續 clean run 可比較。

## 高風險分析

### Migration

採 strict in-place v2 migration：project 仍是 schema v1，但所有現有 configured commands、fixtures、CLI command contract 與 tests 一次改成完整 policy；缺少 `command_policy_version: 2` 或任何 required field 時不讀 legacy `argv`，直接 fail closed。沒有隱式 runtime migration，也不修改既有 Work Item ledger schema。

### Rollback

程式/config 變更由 Git diff 供使用者回復；執行期只使用 temporary sandbox 與 current-artifact-preserving promotion transaction。postcondition 前不寫 user worktree；promotion failure 恢復 current bytes。不得用 Git branch/worktree 或直接 destructive cleanup 作 rollback。

### Security

Admission 將 identity、context、environment 與 effect 綁為一個 decision；清除 `GIT_EXTERNAL_DIFF`、Git pager/helper/config、`RIPGREP_CONFIG_PATH`、response/alias/preprocessor 與 PATH replacement；grammar 對 unknown command/subcommand/flag、shell operator、newline/Unicode whitespace、quoted/relative executable、wrapper、symlink/junction、nested repo 一律拒絕。Work Item artifact 使用既有 typed mutation path。`network` 是 explicit policy field；本批 command 全部 deny，且不宣稱 stdlib 能取代 OS network isolation。

### Compatibility

保留 exact `.codex/hooks.json` matcher、CLI JSON envelope、profiles/dependencies/affected-path selection、existing evidence schema v1 的可讀性與 extension product behavior；只把 command execution 改成 v2 controlled path。既有 old-format command 不相容，必須由本 Work Item 遷移；read-only direct commands 只保留 grammar 明確列出的 Git/rg/PowerShell forms。

### Performance

full-tree copy/hash 是刻意的 high-risk cost；executor 使用 sorted traversal、streaming SHA-256、bounded logs 與每命令 timeout，並把 selection/profile parallelism 留在 policy admission 之後。連續三次 determinism run 使用相同 clean fixture；若 snapshot/copy 超時或資源錯誤，失敗而非縮小 scope。

## 設計決策

## DEC-001: Strict v2 typed policy model

- Requirements: REQ-001, NFR-001
- Decision: 以 `command_policy_version: 2`、`CommandPolicy` dataclass 與 trusted executable registry 作為唯一 configured command contract；不保留 argv-only fallback。
- Rationale: 把 schema、identity、context 與 failure semantics 固定在一個 deep module，避免 optional metadata 被誤當成授權。
- Consequences: 現有 project/fixtures 必須遷移；parse failure 更早暴露，但可在 G1/G2 前阻止不可信 command。

## DEC-002: Typed grammar admission

- Requirements: REQ-002, REQ-004, NFR-001
- Decision: 以 git/rg/必要 PowerShell 的 executable/subcommand grammar 取代 `READ_ONLY_PREFIXES`；unknown input fail closed，grammar 不執行 shell。
- Rationale: prefix matching 無法排除 config/helper/preprocessor/flag injection；typed allowlist 可逐項測試。
- Consequences: 允許的 read-only surface 變窄，新增 command 必須新增 grammar 與 adversarial tests。

## DEC-003: Temporary full-tree sandbox

- Requirements: REQ-003, NFR-002
- Decision: 所有 `writes != none` command 在 temporary full-tree copy 執行，前後比較 filesystem/Git snapshot；不建立 Git worktree，不在 user worktree 直接執行。
- Rationale: 實際 changed paths 比 regex 猜測可靠，且 sandbox 可在 postcondition 前丟棄。
- Consequences: copy/hash 成本增加；需要 atomic promotion adapter 與 sandbox fixture seam。

## DEC-004: Canonical identity and explicit context

- Requirements: REQ-002, REQ-001
- Decision: cwd 必須 canonical exact/in-repository，executable 必須 registry path/hash 相符，release-only 只接受 typed explicit release context，risk/phase/env/network/timeout 均由 `ExecutionContext` 驗證。
- Rationale: command ID、profile 或 ambient PATH 都不是 release/identity authority。
- Consequences: command set/configuration 需要 host-specific executable registry；環境差異會 fail closed 而非自動替換。

## DEC-005: Layered violation and evidence contract

- Requirements: REQ-003, NFR-001, NFR-002
- Decision: pre-run deny 使用 exit class 2 且不啟動 process；post-run effect/postcondition/promotion failure 使用 exit class 4、保存 evidence 且阻擋 G3。
- Rationale: 使用者可區分「沒有執行」與「執行後未通過治理」，同時保留可稽核證據。
- Consequences: CLI/verification result 與 evidence model 增加 policy fields；既有 tests 必須檢查兩層行為。

## DEC-006: Bash categories and typed mutation boundary

- Requirements: REQ-005, REQ-003
- Decision: read-only grammar direct allow；registered command 只能 controlled executor；ad-hoc side-effect 預設 deny，waiver 也只能進 typed executor；Work Item artifact 維持 apply_patch/Edit/Write seam。
- Rationale: 不把 arbitrary shell string 當作可信 mutation transport。
- Consequences: 直接 Bash 驗證命令的舊用法停止，使用者必須用 `devweave verify`；artifact workflow 不受 side-effect shell bypass 影響。

## DEC-007: Deterministic test and evidence surface

- Requirements: NFR-001, NFR-002
- Decision: policy pure seams 使用 fake runner/synthetic trees 測試，integration 使用 real Windows paths/wrappers/nested repo matrix；evidence canonicalize random sandbox details。
- Rationale: 同時隔離 policy logic 與驗證真實 process boundary，讓三次 clean run 可精確比較。
- Consequences: tests 會增加 fixture setup 與 Windows conditional cases；full suite runtime 上升但 failure evidence 更具體。

## G2 補充：Single Verification Policy deep module

### Module、Interface、Seam 與 Depth

`command_policy.py` 是本次唯一的 deep Module。它隱藏 policy schema normalization、canonical path/executable identity、typed argv admission、phase/risk/gate/session/release context、dependency closure、policy/command digest、Effective Verification Plan 與 evidence eligibility；caller 不再自行判斷「這個 command 是否可以執行」或「這筆 evidence 是否能進 G3」。

其穩定 Interface 是以下六個小而完整的 pure/coordinator operations：

```text
normalize_project_policy(raw_project, repo) -> NormalizedPolicy
policy_digest(normalized_policy) -> str
command_definition_digest(command_definition) -> str
evaluate(PolicyContext) -> PolicyDecision
build_effective_plan(PlanContext) -> EffectiveVerificationPlan
derive_evidence_eligibility(EligibilityContext) -> EvidenceEligibility
```

`PolicyContext` 包含 Work Item、phase、gate status、session binding、command definition、requested argv/cwd、writes、outputs、affected paths、release stage、dependency closure 與 current policy digest。`PolicyDecision` 至少包含 `allowed`、stable `reason_code`、`execution_channel`、policy digest、command digest 與 plan identity；任何 parse、canonicalization、snapshot 或 policy exception 都是 deny/fail-closed decision。

外部 Seam 只有 `command_policy.py` 的 Interface。`guard.py`、`devweave.py`、`devweave_core.py` 的 Guard/CLI/Runner/G3/Doctor/Mutation code 都是 adapters/coordinators，不複製 policy predicate。執行副作用藏在 private executor seam：production 使用 subprocess/filesystem/git adapters，tests 使用 fake runner、synthetic tree 與 deterministic snapshot adapter；這是兩個真實 adapter，保留 seam 的 testability 與 locality。Interface 測試只檢查 decision、plan、observation 與 eligibility，避免測試穿透 implementation。

### Effective Verification Plan freeze

G2 `approve_gate(build)` 透過既有 atomic state writer，在 `state.json` 內建立唯一 `verification_plan` snapshot，不建立第二份 plan ledger。其 canonical shape 為：

```json
{
  "schema_version": 1,
  "plan_id": "plan-<stable-id>",
  "plan_digest": "sha256:<canonical-plan>",
  "project_policy_digest": "sha256:<project-policy>",
  "profile": "standard",
  "risk": "high",
  "required_commands": ["unit-tests-core", "extension-tests"],
  "selected_commands": ["unit-tests-core"],
  "skipped": [{"id": "extension-package", "reason": "release-context-required"}],
  "not_applicable": [{"id": "docs-check", "reason": "no-affected-path-intersection"}],
  "dependency_closure": {"unit-tests-core": []},
  "commands": {
    "unit-tests-core": {
      "definition_digest": "sha256:<command>",
      "stage": 0,
      "writes": "none",
      "outputs": [],
      "exclusive_group": null,
      "expected_success_exit_codes": [0],
      "gate_eligibility": "zero-only"
    }
  },
  "source_fingerprint_at_plan": "sha256:<source>",
  "frozen_at": "<utc>"
}
```

`plan_digest` canonicalizes sorted keys, command IDs, reasons and dependency closure. Runner 的 selected/skipped/not-applicable response 與 G3 required set 只讀這份 snapshot；selective `--path` 若改變 selection basis，必須產生 deterministic diagnostic/ineligible result 或要求 revise，不能偷偷建立另一份 required set。Project policy digest 或任何 command definition digest 改變時，plan、G2/G3 status 與受影響 evidence 由 typed mutation path 一起 stale。

### Evidence contract 與 engine-derived eligibility

Verification evidence 會保存 `plan_id`、`plan_digest`、`project_policy_digest`、`command_definition_digest`、canonical argv/cwd、source fingerprint、input fingerprint、output fingerprint、實際 exit code、declared outputs、`actual_changed_paths`、execution channel、status、`gate_eligible` 與 `eligibility_reason`。`gate_eligible` 不接受 caller input，只由 `derive_evidence_eligibility()` 計算。

Eligibility 的必要條件是：execution channel 為 DevWeave controlled executor、plan/command/source digest current、exit code 命中正式 success policy、無 timeout/execution error、observed effects 僅在 declared outputs/work scope、postcondition/promotion 成功，且 expectation 是 zero-only。`expect=nonzero`、`expect=any`、reproduction、diagnostic、failed、timed out、undeclared writes、source stale 或 digest mismatch 一律 `gate_eligible=false`。G3 Required Command、AC coverage 與 Required Evidence Kind 只查 `gate_eligible=true`。

### Execution stage、snapshot 與 promotion

Effective Plan 先對 dependency closure 做 deterministic topological staging，再加入 shared output boundary 的 exclusive group。`writes != none` 的 command 只能依 dependency 順序 serial 執行；writer stage 結束後凍結 candidate fingerprint。只有 `writes=none`、同一 stage、沒有 shared boundary 的 commands 可平行。任何 writer 與 writes:none command 的不安全 overlap 都自動 exclusive 或在 plan construction deny。

每個 command 執行前後都取得 full-tree filesystem、tracked Git state 與 declared output snapshot。writer 在 temporary full-tree sandbox 中以 `shell=false` 執行，post-run reconciliation 計算 `actual_changed_paths`；writes:none 的任何變更、writer 的 undeclared path、scope 外變更、postcondition 或 promotion failure 都產生 failed evidence 且不 promotion。只有 declared output 在 scope 內、postcondition 通過並完成 atomic promotion 才能更新 current artifact；candidate fingerprint 在 writer stage 後固定，後續 read-only tests 的 input fingerprint 必須引用它。

### Policy mutation lifecycle

`command set/remove` 仍是唯一 project policy mutation path。它在 project lock 下先 normalize old/new policy 並計算 digest；在 active Work Item 期間採「允許 controlled mutation，但 deterministic stale」決策：所有引用受影響 command 或 project policy digest 的 active state，透過 core typed state/evidence writer 標記 verification plan、G2/G3、required evidence 與 command evidence stale，並寫入 bounded event。mutation 不直接編輯 state/events/evidence JSON/JSONL，也不能保留舊 evidence current。

## DEC-008: Effective Plan embedded in state

- Requirements: REQ-007, REQ-008, NFR-004
- Decision: G2 frozen plan 嵌入 Work Item `state.json`，由同一 atomic state mutation path 寫入；Runner 與 G3 不建立平行 plan 檔。
- Rationale: 保持 plan、gate fingerprint 與 Work Item lifecycle 同一 ownership，避免第二份 plan ledger drift。
- Consequences: state schema 需要 additive `verification_plan` contract；project policy mutation 必須透過 typed invalidation 使 plan stale。

## DEC-009: Engine-derived gate eligibility

- Requirements: REQ-008, NFR-003
- Decision: `gate_eligible` 是 evidence engine output，不是 CLI、Guard、caller 或 test fixture 可指定的欄位；G3 只消費 engine-eligible evidence。
- Rationale: expectation match、status passed 與 gate trust 是不同概念，必須避免 nonzero/any/reproduction 被誤升格。
- Consequences: evidence schema 增加 eligibility reason 與 observed effect fields；既有 raw passed filter 必須移除。

## DEC-010: Controlled mutation with deterministic stale

- Requirements: REQ-010, NFR-004, NFR-005
- Decision: active Work Item 期間允許 project command policy mutation，但 old/new digest 改變會使所有受影響 plan、gate 與 evidence deterministic stale。
- Rationale: 不阻塞必要 policy repair，同時不允許既有 G2/G3/evidence 靜默沿用舊 definition。
- Consequences: mutation path 需要跨 Work Item 的 typed invalidation helper 與 machine tests。

## DEC-011: Writer barrier and output exclusivity

- Requirements: REQ-011, NFR-004, NFR-005
- Decision: Effective Plan 對 writer 建立 dependency/stage barrier；只有 writes:none commands 可平行，shared output boundary 自動 exclusive 或 deny。
- Rationale: test evidence 的 source/input fingerprint 必須代表 writer 完成後的 stable candidate，而非 race 中的 repository。
- Consequences: profile runner 不再對所有 ready commands 使用同一個 thread pool；parallelism 受 plan stage 約束。

## DEC-012: Cross-shell typed read-only grammar

- Requirements: REQ-004, REQ-012
- Decision: 以 argv allowlist/typed grammar 取代 string prefix；POSIX、CMD、PowerShell operator、substitution、redirection、unknown/output flags、wrapper/helper/config injection 一律 fail closed。
- Rationale: lexical prefix 無法證明 command 不會啟動 helper 或寫入 output。
- Consequences: read-only surface 變窄；既有 safe exact forms 以 public evaluator tests 固定，新增形式必須同時加入 allowlist 與 adversarial test。

## DEC-013: Configured commands require DevWeave executor

- Requirements: REQ-006, REQ-009
- Decision: Guard 對 argv-identical configured command 的 direct Bash request 一律 deny，只有 `devweave verify` 能建立 controlled execution channel。
- Rationale: command identity alone is not execution authority；executor 必須綁定 policy、context、snapshot 與 evidence。
- Consequences: CLI/Guard message 需提供 verify handoff；existing shell=False verification path 維持，但不能由 Bash bypass。

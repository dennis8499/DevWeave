<!-- canonical-topic: product -->
# Product contract

DevWeave 2.0.0 embeds Codex inside a governed software-delivery workflow. Users can start, resume, steer, interrupt, review, and cancel work from VS Code while retaining explicit authority over consequential actions. Agents receive enough repository context and exactly eight MCP tools to execute an approved plan, but cannot approve their own Gates or expand their authority.

## User-visible guarantees

- The Control Center shows connection/preflight, run/thread/turn, plan/diff, tool approval, pending decision, Gate, verification, review, usage, and diagnostic state.
- Projection/stale state is visibly distinct from authoritative/current state.
- Missing Codex is a hard, machine-readable blocker; a missing same-distribution code-mode host companion is treated identically, with no download, isolated-binary, or clipboard fallback.
- Risk can escalate automatically and determines human Gate/review depth.
- A run can restart from its canonical plan without treating conversation history as workflow truth.
- V1 recovery uses a deterministic read-only index and the recorded Git base ref, never a dual runtime.

## Stable surfaces

The public CLI verbs are `doctor`, `inspect`, `check`, `verify`, `export-v1`, and `mcp-serve`. Agent MCP tools are `run_inspect`, `context_read`, `plan_save`, `decision_request`, `task_update`, `verification_run`, `verification_read`, and `completion_request`. Host-only operations are `run_start`, `run_resume`, `decision_resolve`, `gate_decide`, and `run_cancel`.

## Acceptance catalog

### AC-001: App-server lifecycle round-trip
Initialize app-server and exercise thread/turn start, resume, steering, interruption, and event reduction without a clipboard path.

### AC-002: CLI preflight fail-closed
Resolve PATH or an absolute Codex path with executable and same-directory code-mode host provenance; reject unavailable, incomplete, or invalid installations before run, branch, network session, or process mutation.

### AC-003: MCP allowlist and guard
Expose exactly eight tools and reject unknown, stale, malformed, traversal, or out-of-scope calls without state mutation.

### AC-004: Host/agent capability isolation
Allow only the authenticated host to start/resume runs, resolve decisions, decide Gates, or cancel.

### AC-005: Risk matrix
Require plan; plan plus acceptance; or scope plus design plus acceptance for low, standard, and high risk respectively, with matching review depth.

### AC-006: Git lifecycle
Reject dirty/detached/colliding starts and otherwise create a fixed-base run branch whose task/Gate/archive commits include the post-transition canonical plan, with no remote/merge/reset/switch-back side effect.

### AC-007: ExecPlan restart
Resolve saved task/Gate/archive checkpoint refs into equivalent canonical snapshots and replay an interrupted mutation without duplicating state transitions or commits, including an acceptance crash after completed state is durable but before its active-to-completed archive move.

### AC-008: Pending decision round-trip
Resolve only a valid option or allowed custom answer at the current revision; cancellation or malformed/stale input leaves the task pending.

### AC-009: Docs truth contract
Reach architecture, product, reliability, security, quality, and ExecPlan authority from the root map within bounded hops, with no broken links or duplicate canonical topic.

### AC-010: V1 export determinism
Produce byte-stable export artifacts for the recorded 21 work items and 411 evidence files without modifying V1 inputs.

### AC-011: CLI/schema contract
Keep six verbs and five strict public schema envelopes stable across valid, unknown-field, invalid-version, and malformed fixtures.

### AC-012: Rich client state coverage
Render and operate every key lifecycle state from scripted app-server events without calling a projection authoritative.

### AC-013: Verification safety parity
Select deterministic DAG stages, serialize writers, disable shells, enforce declarations, and admit only current zero-exit reconciled evidence.

### AC-014: Bounded independent review
Use detached reviewer identity; run one standard review or no more than three high-risk fix/reverify rounds, then block unresolved critical work.

### AC-015: Clean 2.0.0 package
Align public versions, generate but do not track VSIX output, and remove V1 runtime/UI mutation surfaces while retaining export recovery.

### AC-016: Adversarial authorization
Reject unknown methods, forged roles, stale revisions, traversal, symlink/junction escape, physical filesystem aliases including NTFS short names, scope violations, and task globs that cannot map exactly to directory-subtree sandbox roots before repository/process mutation.

### AC-017: Deterministic state
Produce identical canonical snapshots/hashes from identical ordered transcripts and recover atomically around injected write failures or duplicate delivery.

### AC-018: Telemetry privacy
Redact secrets, bound payloads, omit prompts/reasoning, and keep unavailable usage null without estimates.

### AC-019: Mechanical architecture checks
Pass the healthy repository and report concrete code/path failures for oversized modules, reverse dependencies, long root guidance, schema drift, broken links, and untraced acceptance.

### AC-020: UI evidence bundle
Produce bounded DOM/accessibility/log/screenshot evidence with run, commit, Codex version, and protocol schema provenance.

### AC-021: Certification boundary
Mark only the executed Windows x64/VS Code matrix certified and label all other environments unverified.

### AC-022: Recovery drill
Identify the last current phase, source-only diff, evidence, export, and canonical-plan checkpoint after injected state/commit failure; recover a lost working plan from Git while leaving the base ref and remotes untouched.

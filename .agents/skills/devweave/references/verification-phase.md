# Verification and Acceptance Phase

Read this reference only while the work item phase is verification or acceptance_review.

## Verify

1. Inspect the full diff against the work item's base source.
2. Run every command required by the current risk profile through the CLI verify command. Prefer one profile batch, for example `verify --profile standard --max-parallel 3`, which preserves per-command evidence while running independent commands concurrently; use individual `verify --command <id>` calls only for legacy or intentionally isolated commands.
3. Add profile evidence: acceptance for new; acceptance plus regression for feature; equivalence plus regression for refactor; regression for bug. Review evidence is separate and is required only for high-risk G3.
4. Cover every AC with current passing evidence bound to the present source fingerprint.
5. When all product, Wiki, baseline, diff, scope and existing evidence are stable, high-risk work must run exactly one isolated, read-only Independent Review Agent before the G3 summary. Standard and low-risk work must not start this reviewer. The reviewer must not modify source, Wiki, ledgers or gates, and must not run approve, revise or close.
6. Record the reviewer response through the machine-only `review record` interface; Python engine does not spawn an Agent and the VS Code Extension does not invoke one. Do not pass the main Agent's reasoning into the isolated reviewer.
7. Run `knowledge status --work <id>`. Review `affected_pages`, `covered_changed_paths`, `uncovered_changed_paths`, bootstrap recommendation, and review currentness. Refresh or delete each affected page before G3; unrelated stale pages remain warnings.
8. For every new-format work item, record `knowledge review --work <id> --disposition promote|no-update --rationale <text>`. This Knowledge Review is mandatory even when the Wiki remains unchanged. A later product-source fingerprint change invalidates both the review and knowledge plan; rerun the review after implementation stabilizes. Legacy work without the marker is not retrospectively blocked. G3 approval may be collected through the native Gate question when `request_user_input` is visible; the existing explicit `approve` contract and complete acceptance validation remain authoritative.
9. Choose `no-update` only for non-bootstrap work with no affected page and no Wiki diff, and record a concrete non-empty rationale. Do not create a knowledge plan. Uncovered changed paths may remain only when the review concludes they contain no durable reusable knowledge.
10. Choose `promote` when the work produced durable reusable knowledge. Call `knowledge plan` once with the complete set of one to five content upserts/deletes. Existing affected pages must be refreshed or deleted; durable uncovered changes may be covered by one or more new pages and do not require one page per file.
11. For a planned new upsert, call `knowledge scaffold` with its canonical type, title, and one to five sources. Dependency pages also require package name/version; decision pages require date/status. Scaffold never overwrites and creates a `placeholder` page. Replace every template token, set the page active, update only planned content pages plus coupled index/log, append exactly one `promote` heading containing the work ID without rewriting existing log body, then seal all upserts plus index/log. Seal rejects placeholder pages, template tokens, invalid sources, and critical lint.
12. A bootstrap profile must change no product source and promote three to five content pages: `wiki/overview.md`, at least one architecture page, at least one module page, plus at most two evidence-backed high-value topics. Every completed page must be active, sourced, current, sealed, indexed, and logged. `no-update` and deletes are invalid for bootstrap.
13. Update accepted living truth under `.devweave/baseline`, or record why no baseline update is needed. Declare every changed baseline path through `baseline --target`; undeclared changes and declared-but-unchanged targets block G3. `new` work must make and declare an architecture baseline update.
14. Complete `acceptance.md` in Traditional Chinese with the AC/TASK/EVID matrix, Knowledge Review disposition/rationale, Wiki promotion and warnings, baseline changes, Independent Review result/warnings/findings/report evidence, any named `review-critical` waivers, residual risks, and conclusion.

## Independent Review Agent

The single DevWeave router owns this invocation. Python engine does not spawn an Agent and the VS Code Extension does not invoke it. After final artifacts are stable and before the G3 summary, the router starts exactly one reviewer for a high-risk G3 attempt in an isolated, read-only context. Do not pass the main Agent's reasoning, conclusions, hidden chain-of-thought, or conversational speculation into the reviewer.

The reviewer may read only approved artifacts, the complete diff, risk analysis, scope, accepted baselines, recorded Wiki context, current source fingerprint, Git HEAD, and existing evidence. It must not write source, tests, Wiki, artifacts, state, events, evidence JSON/JSONL, baseline, or cache logs; run `approve`, `revise`, or `close`; or delegate another Agent. The router should use its Agent tool's isolated-context option (for example `fork_context: false`) and provide no mutation-capable workspace context.

The reviewer returns exactly one UTF-8 JSON object:

```json
{
  "result": "passed | unavailable | critical",
  "severity": "none | advisory | critical",
  "summary": "bounded reviewer summary",
  "source_fingerprint": "current source fingerprint",
  "covers": ["AC-001"],
  "tasks": ["TASK-001"],
  "findings": [{
    "id": "F-001",
    "severity": "advisory | critical",
    "title": "bounded finding title",
    "evidence": "bounded supporting observation",
    "recommendation": "bounded recommendation"
  }]
}
```

The router writes the response, or a generated `unavailable` response for timeout/no output/format failure, to `.devweave/cache/incoming/<work-id>/` and invokes:

```text
python -B .agents/skills/devweave/scripts/devweave.py --repo . review record \
  --work <work-id> --reviewer-id <opaque-agent-id> \
  --report-file .devweave/cache/incoming/<work-id>/<attempt>.json
```

The engine validates containment, bounded size, fixed fields, AC/TASK IDs and current source fingerprint, redacts secrets, hashes the redacted stored report, and creates `kind: review` evidence plus provenance. Agents must never edit the evidence ledger directly. Malformed input must never become `passed`.

G3 handling is deterministic: current `passed` is accepted; missing, `unavailable`, timeout-shaped or malformed-fallback review is a warning; `passed` with advisory findings is a warning; critical security, data-loss, irreversible or scope findings block G3 until each named finding ID has an exact narrow `review-critical` waiver on the acceptance gate; a source fingerprint change makes review evidence stale and requires a new review. Human G3 approval remains mandatory.

Treat G3 as a conformance check against the approved requirements, design, task plan, and evidence. Do not silently resolve a newly discovered product or design decision during verification; record the decision and use `revise` from the earliest affected phase, then rerun the invalidated validation and evidence.

Run validate with gate acceptance. A changed product-source fingerprint makes post-implementation evidence, Knowledge Review, and plan stale; rerun affected checks. A later Wiki-only change leaves product evidence current but invalidates G3 through its separate knowledge fingerprint. Critical Wiki lint, undeclared/unchanged knowledge targets, more than five content targets, missing index/log coupling, stale affected pages, placeholder/template content, and log rewrites block G3. Out-of-scope product changes require removal, scope revision, or an explicit waiver.

## G3

Present the behavior delivered, verification commands, manual evidence, baseline changes, waivers, residual risks, and any approved-decision conformance findings in Traditional Chinese. Record G3 only after explicit human approval or an explicit `$devweave approve` request; silence or an inferred acceptance is not approval. Then run close immediately.

When acceptance is rejected, record revise from requirements, design, or implementation according to the reason and continue from that phase.

Complete when G3 is current, close succeeds, and the work item remains in place with status closed.

## Verification Policy v2 operating rules

Before executing a configured command, confirm that the Work Item has a current
G2-backed `verification_plan`. Run `verify --command` or `verify --profile` only
through the Router; do not paste a configured argv into Bash. The profile result's
`selection.effective_plan_digest` must match the Work Item plan and the recorded
evidence digests.

The engine derives `gate_eligible`; callers cannot set it. A matching non-zero or
`any` expectation may be useful diagnostic evidence, but it cannot satisfy a required
command, AC coverage, regression evidence or G3. A changed command definition,
project policy, source fingerprint or declared-output reconciliation makes old command
evidence stale or ineligible.

Write commands run in serial dependency stages and are reconciled in a candidate
repository before declared outputs are promoted. Only `writes=none` commands can be
parallelized. Any undeclared path change fails the execution evidence. Release-only
commands require an explicit `--release-context`; selective profile skips and
not-applicable reasons are the same frozen-plan data consumed by G3.

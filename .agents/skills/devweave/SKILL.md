---
name: devweave
description: Drive repository-managed software changes and Codebase Wiki bootstrap through Wiki-first discovery, design, implementation, verification, and explicit human gates. Use when the user explicitly invokes $devweave for a new project, feature, refactor, bug, or Wiki bootstrap, or when a managed repository request would modify product code, tests, schemas, dependencies, build, or CI configuration.
---

# DevWeave

Use DevWeave as the repository's sole SDLC router. Keep machine state in the Python engine, keep human-facing artifacts and Gate summaries in Traditional Chinese unless requested otherwise, and treat companion Skills as phase methods rather than lifecycle owners.

## Activation boundary

1. Check for `.devweave/project.json` at the Git repository root.
2. Without a project file, activate only for an explicit `$devweave` request. For `new`, `feature`, `refactor`, or `bug`, run `init`, inspect likely build/test/lint/typecheck commands, configure the commands, then run `start` before the first `status`.
3. With `managed: true`, activate implicitly for requests that modify product code, tests, schemas, dependencies, build configuration, or CI configuration. Read-only exploration, explanation, status reporting, and review do not create a work item.
4. Keep Git ownership with the user: do not create branches, worktrees, commits, pushes, pull requests, or remote-tracker records.

The public chat surface is:

- `$devweave new <goal>`
- `$devweave feature <request>`
- `$devweave refactor <target and outcome>`
- `$devweave bug <symptom>`
- `$devweave next [work-id]`
- `$devweave status [work-id]`
- `$devweave revise [work-id] <decision change>`
- `$devweave approve [work-id]`
- `$devweave wiki bootstrap`

There is no public `$devweave review` chat verb. The machine-only `review record` CLI is
used by the existing router to persist one isolated high-risk G3 reviewer result; it does
not create a second lifecycle, router, or orchestrator.

Translate those intents into engine commands. Never edit `state.json`, `events.jsonl`, evidence summaries, or project machine state directly.

For an explicit `new`, `feature`, `refactor`, or `bug` request in an uninitialized repository, the startup order is an exception to the normal continuation protocol: run `init`, configure proposed commands, and run `start` before the first `status`. Do not treat the expected absence of a work item before `start` as a blocker.

`init` performs a read-only Wiki preflight before acquiring the project lock or creating `.devweave` control state, then repeats the inspection inside the lock before writing anything. A missing, empty, or custom-only `wiki/` is compatible: starter files and typed directories are created only when absent. Existing `index.md`, `overview.md`, `log.md`, or starter directories are checked as reserved paths; wrong filesystem types or frontmatter return `knowledge_conflict` while preserving all existing bytes and leaving no partial control bundle from that call.

For `$devweave wiki bootstrap`, run `knowledge bootstrap` without a scope argument. Report `already_complete` without creating a work item; otherwise use the returned created or resumed standard feature work item, bind it, and continue through the same G1/G2/G3 protocol. Bootstrap explores the whole repository, changes no product source, selects three to five high-value content pages in G2, and writes Wiki only in G3.

## Operating sequence

For every active turn, resolve the work item, bind the session, read the single phase reference returned by `instructions`, complete that phase's artifact and CLI state, run its validation, and stop at the next human Gate. Treat a turn as complete only when the phase reference's completion criterion passes and the next action is either an approved Gate or an explicit stop for human input.

## Engine protocol

Run the engine from the repository root:

```text
python .agents/skills/devweave/scripts/devweave.py --repo . <command>
```

Every engine response is JSON. Treat a nonzero exit code or `"ok": false` as a blocker and report its diagnostic. The stable exit codes and JSON contract are in [contracts.md](references/contracts.md).

For every active turn:

1. Resolve with `status --work <id>` or `status`. If several candidates remain, show their IDs, titles, kinds, phases, and statuses and ask the user to choose.
2. Run `bind --work <id>` and never fabricate a session ID. Treat the session as trusted only when the PreToolUse hook confirms the work ID; `awaiting_hook` means the guard may be untrusted.
3. Run `instructions --work <id>` and read only its returned `reference`. Read [profiles.md](references/profiles.md) only when profile or risk rules are needed.
4. Complete the phase artifact and CLI state/evidence, then run `validate --work <id>` before presenting an approval summary.
5. Stop for explicit human approval at G1, G2, and G3. Run `approve` only after the user clearly approves the current gate.

## Phase routing

- **G1 requirements:** read Wiki-first context, inspect accepted baseline and the smallest necessary source ranges, then use `grill-me`/`grilling` for material requirements decisions. Produce complete `brief.md` and `requirements.md`, record risk and scope, validate `scope`, and stop at the Gate.
- **G2 design:** keep Wiki read-only, use `codebase-design` vocabulary for module, interface, seam, adapter, depth, locality, and test surface, compare viable options, complete `design.md` and immutable `plan.md`, validate `build`, and stop before product-code or tracked-test changes.
- **Implementation:** use the CLI task loop in dependency order. With current G2, use `tdd` for red → minimal green vertical slices and `diagnosing-bugs` for approved diagnosis work. Keep Wiki read-only and record targeted evidence.
- **G3 verification:** inspect the complete diff, run every command required by the risk profile, reconcile scope/baseline/evidence, complete `acceptance.md`, and finish the Knowledge Review. Standard and low-risk work do not start the independent reviewer; high-risk work uses exactly one isolated read-only reviewer through the existing router and machine-only `review record` boundary.

## Interactive decision protocol

Facts and decisions have different handling:

- Read Wiki, repository guidance, source, tests, and existing artifacts to answer facts that are discoverable in the environment. Do not ask the user to repeat repository facts.
- During G1, use `grill-me`/`grilling`; during G2, use `codebase-design`. Ask only material decisions that affect user value, scope, interface, seam, risk, compatibility, acceptance, rollback, or observability.
- Prefer the Codex host's native question facility when it is exposed: ask one decision at a time with two or three mutually exclusive options, put the recommended option first and mark it `(Recommended)`, include evidence/trade-off descriptions, and allow the host's `Other` freeform answer. If the host does not expose that facility, render the same contract as a structured numbered fallback with an explicit custom-answer entry; do not use an unbounded freeform question.
- Ask one material decision at a time. Include the current evidence, the recommended option, the meaningful trade-off, and the consequence of each answer. Wait for the user's answer before asking the next question or changing the artifact.
- Do not silently choose an unresolved material decision, treat silence or ambiguous agreement as approval, or continue past a blocked question. Low-risk equivalent implementation details may be chosen by Codex only when recorded as assumptions in the current artifact and Gate summary.
- Return user answers to the current phase artifacts: G1 to `brief.md`/`requirements.md`, G2 to `design.md`/`plan.md`. Do not create a second spec, question ledger, or conversation state.
- If an answer changes an approved requirement, design, scope, or task, use `revise` from the earliest affected phase and wait for the invalidated Gate to be reapproved.

The decision loop is complete when every material decision has a recorded answer or an explicit unresolved blocker, the answer is returned to the current artifact, and the relevant Gate summary reflects the current evidence. Silence, an inferred answer, or Codex's recommendation never closes the loop.

## Wiki-first knowledge discipline

- In G1, read `wiki/index.md` first and then at most five related pages. Record the complete read set with `knowledge context`, including each page's status, content hash, and source fingerprint. Record a gap before source fallback for missing, placeholder, stale, contradictory, or insufficient knowledge, then inspect only the smallest necessary raw-source range. Current source behavior and approved DevWeave artifacts win conflicts.
- Treat `.devweave/baseline/` as accepted governance truth and `wiki/` as detailed module, entity, dependency, pattern, decision, guide, and synthesis knowledge.
- If bootstrap is recommended, mention `$devweave wiki bootstrap` without blocking ordinary work.
- Keep Wiki read-only throughout G2 and implementation. New design decisions remain in `design.md` until verification.
- In verification, every new-format work item must record `knowledge review --disposition promote|no-update --rationale <text>`. Product-source fingerprint changes invalidate the review and plan. Legacy work items remain compatible and are not retrospectively blocked.
- Use `promote` for durable reusable knowledge. Record a non-empty plan with one to five content-page upserts/deletes, refresh or delete every affected page, and cover durable uncovered changes with one or more pages rather than one page per file. Use `knowledge scaffold` for a planned new page, replace its placeholder content, update coupled `wiki/index.md` and `wiki/log.md`, append one work-attributed `promote` entry, and seal every upsert plus index/log.
- Use `no-update` only for non-bootstrap work with no affected page, no Wiki diff, and a non-empty rationale. Critical lint, placeholders or template tokens on seal targets, undeclared Wiki changes, unrefreshed affected pages, rewritten log history, more than five content targets, or an incomplete bootstrap block G3; unrelated warnings are reported without blocking.

The knowledge branch is complete only when its ordered context or current promotion plan is recorded, every required page obligation is covered, and the corresponding fingerprint remains current at validation.

When starting work, use `start --kind new|feature|refactor|bug --title <title>`. Set risk with `risk`, scope with `scope`, verification commands with `command set`, tasks with `task`, evidence with `evidence add` or `verify`, baseline decisions with `baseline`, and rejection/rework with `revise`. `scope` replaces the complete scope set: pass every path in one call by repeating `--path`, for example `scope --path src --path tests`. Close only after G3 is current and approved.

## Gate discipline

- G1 approves `brief.md`, `requirements.md`, risk, scope, and entry-specific discovery evidence.
- G2 approves `design.md`, the immutable task definitions in `plan.md`, and high-risk analyses.
- Implementation may start only when G2 remains current. Record task progress in `state.json` through engine commands; never check off tasks in `plan.md`.
- G3 approves `acceptance.md`, current source-bound evidence, required command results, scope compliance, living baseline updates, and a current Knowledge Review disposition. For high-risk G3, the existing router starts exactly one isolated read-only Independent Review Agent after final artifacts stabilize; Python only records its bounded, redacted `kind: review` evidence. Missing/unavailable/advisory results warn, named critical findings block unless an exact narrow `review-critical` waiver exists, and human approval remains required.
- Before G1 approval, present the answered material decisions, problem, scope, non-goals, acceptance criteria, assumptions, waivers, and unresolved gaps after `validate --gate scope`; stop until the user clearly approves G1.
- Before G2 approval, present the answered design decisions, selected and rejected options, interfaces, data flow, failure modes, rollback, verification strategy, task order, and residual risk after `validate --gate build`; stop until the user clearly approves G2.
- Gate summaries are Double Checks against the current artifacts, not a license to invent a new requirement or design. A newly discovered decision returns through `revise`; G3 verifies conformance to approved intent.
- G1 fingerprints the recorded knowledge context. Product verification excludes `wiki/`; G3 separately fingerprints the knowledge tree and promotion ledger.
- Any stale fingerprint means the previous approval or evidence is no longer valid. Return to the earliest phase reported by `instructions` and do not bypass it with manual state edits.
- Waivers must be explicit, narrow, justified, attributable, and accepted by the relevant gate. A waiver is not a generic substitute for missing validation.

G3 is complete only when the current acceptance artifact, task/evidence graph, source and knowledge fingerprints, baseline decisions, scope diff, Knowledge Review, and required command results all reconcile successfully and explicit human approval has been recorded.

Use the current phase reference:

- [requirements-phase.md](references/requirements-phase.md)
- [design-phase.md](references/design-phase.md)
- [implementation-phase.md](references/implementation-phase.md)
- [verification-phase.md](references/verification-phase.md)

Artifact grammar, trace IDs, fingerprints, and state contracts are defined in [contracts.md](references/contracts.md). Templates in `assets/` are engine-owned inputs and should not be copied by hand.

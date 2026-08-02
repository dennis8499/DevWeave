# Verification and Acceptance Phase

Read this reference only while the work item phase is verification or acceptance_review.

## Verify

1. Inspect the full diff against the work item's base source.
2. Run every command required by the current risk profile through the CLI verify command.
3. Add profile evidence: acceptance for new; acceptance plus regression for feature; equivalence plus regression for refactor; regression for bug. Add review evidence for high risk.
4. Cover every AC with current passing evidence bound to the present source fingerprint.
5. Run `knowledge status --work <id>`. Refresh or delete each affected page before G3. Unrelated stale pages remain warnings.
6. When promoting knowledge, call `knowledge plan --upsert ... --delete ... --rationale ...` once with the complete content-target set. Update those pages and the automatically coupled index/log only; append exactly one `promote` heading containing the work ID without rewriting existing log body. Seal all upserts plus index/log with `knowledge seal --page ...`. If nothing is affected and Wiki stays unchanged, do not create an empty plan or no-update rationale. `new` work must promote `wiki/overview.md` to active with real sources.
7. Update accepted living truth under .devweave/baseline, or record why no baseline update is needed. Declare every changed baseline path through `baseline --target`; undeclared changes and declared-but-unchanged targets block G3. `new` work must make and declare an architecture baseline update.
8. Complete acceptance.md in Traditional Chinese with the AC/TASK/EVID matrix, Wiki promotion and warnings, baseline changes, waivers, residual risks, and conclusion.

Run validate with gate acceptance. A changed product-source fingerprint makes post-implementation evidence stale; rerun affected checks. A later Wiki-only change leaves product evidence current but invalidates G3 through its separate knowledge fingerprint. Critical Wiki lint, undeclared/unchanged knowledge targets, missing index/log coupling, stale affected pages, and log rewrites block G3. Out-of-scope product changes require removal, scope revision, or an explicit waiver.

## G3

Present the behavior delivered, verification commands, manual evidence, baseline changes, waivers, and residual risks in Traditional Chinese. Record G3 only after explicit human approval or an explicit $devweave approve request. Then run close immediately.

When acceptance is rejected, record revise from requirements, design, or implementation according to the reason and continue from that phase.

Complete when G3 is current, close succeeds, and the work item remains in place with status closed.

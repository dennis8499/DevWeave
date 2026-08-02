# Verification and Acceptance Phase

Read this reference only while the work item phase is verification or acceptance_review.

## Verify

1. Inspect the full diff against the work item's base source.
2. Run every command required by the current risk profile through the CLI verify command.
3. Add profile evidence: acceptance for new; acceptance plus regression for feature; equivalence plus regression for refactor; regression for bug. Add review evidence for high risk.
4. Cover every AC with current passing evidence bound to the present source fingerprint.
5. Update accepted living truth under .devweave/baseline, or record why no baseline update is needed. Declare every changed baseline path through `baseline --target`; undeclared changes and declared-but-unchanged targets block G3. `new` work must make and declare an architecture baseline update.
6. Complete acceptance.md in Traditional Chinese with the AC/TASK/EVID matrix, baseline changes, waivers, residual risks, and conclusion.

Run validate with gate acceptance. A changed source fingerprint makes post-implementation evidence stale; rerun affected checks. Out-of-scope changes require removal, scope revision, or an explicit waiver.

## G3

Present the behavior delivered, verification commands, manual evidence, baseline changes, waivers, and residual risks in Traditional Chinese. Record G3 only after explicit human approval or an explicit $devweave approve request. Then run close immediately.

When acceptance is rejected, record revise from requirements, design, or implementation according to the reason and continue from that phase.

Complete when G3 is current, close succeeds, and the work item remains in place with status closed.

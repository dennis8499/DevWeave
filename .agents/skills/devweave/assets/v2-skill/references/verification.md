# Verification and completion phase

## Goal

Prove the current source conforms to the approved plan using current controlled evidence, then obtain the risk-selected review and human Gate.

## Sequence

1. Inspect the complete approved plan, source diff, task graph, decisions, Git base/run refs, and prior evidence.
2. Run the frozen verification plan through `verification_run`. Selection, dependency closure, writer barriers, timeout, executable provenance, network policy, and effect reconciliation remain engine-owned.
3. Use `verification_read` to confirm every required result is current and gate-eligible. A zero exit alone is insufficient.
4. Reconcile declared scope, no undeclared writes, canonical plan revision, docs/architecture checks, package/version checks, privacy bounds, and recovery evidence.
5. Call `completion_request`. Low risk performs self-review. Standard starts one detached review. High risk may start a detached review/fix/reverify loop but stops after three rounds.
6. For each fix round, implement only the specific finding in the implementation thread, rerun the frozen plan, and require current successful verification before another detached review.
7. Unresolved critical findings or exhausted rounds become a host blocker. Advisory findings remain visible.
8. Present the final acceptance summary and stop for the human Gate. Never approve it as the agent.

## Evidence privacy

Persist verdicts, finding IDs/severity/paths/traces, bounded diagnostics, durations/counters, explicit usage availability, and artifact hashes. Discard reviewer reasoning, full prompts, secrets, and inferred token/cost values.

Completion is final only when RunService reports the run completed at the accepted revision and all required human Gates are current.

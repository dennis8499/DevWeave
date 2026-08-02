# Implementation Phase

Read this reference only while the work item phase is implementation.

## Task loop

1. Bind the current Codex session to the selected work item.
2. Select one pending task in dependency order and mark it started through the CLI.
3. Make the smallest coherent code and test change that satisfies its traced requirements.
4. Keep `wiki/` read-only during implementation. Knowledge promotion begins only after all tasks enter verification.
5. Run targeted repository verification and add evidence when useful.
6. Mark the task complete only with evidence IDs or a concrete completion note.
7. Continue until every approved task is complete or one explicit blocker remains.

Treat plan.md as immutable after G2. If the task definition, requirement, or design must change, invoke revise at the earliest affected phase and stop implementation until the invalidated gate is reapproved.

Keep Git ownership with the user. Inspect HEAD, branch, status, and diff; do not create branches, worktrees, commits, pushes, or PRs unless separately requested.

Complete when every task in state.json is completed, the implementation matches the approved scope, and the phase advances to verification. A blocker is complete only when its task, evidence, cause, and needed decision are recorded.

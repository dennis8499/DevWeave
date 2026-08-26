# Planning phase

## Goal

Produce one strict `RunPlanDraft` whose approved content is sufficient for implementation without guessing.

## Sequence

1. Inspect the current RunSnapshot and the smallest relevant docs/source/test surface.
2. Record the goal, repository-relative scope, non-goals, requirement IDs, acceptance IDs, durable decisions, and explicit assumptions.
3. Slice immutable tasks with declared paths, dependencies, requirement/acceptance links, and vertical verification value.
4. Select the project-defined verification commands and risk. Risk may escalate from effects; do not silently downgrade it.
5. If a material product choice remains, create one typed `PendingDecision` with two or three mutually exclusive options, the recommendation, meaningful trade-offs, and optional custom-answer policy. Stop the affected task until the host resolves it.
6. Save the complete replacement through `plan_save`, inspect the new revision, and stop at the required planning Gate.

## Gate summary

Present goal, scope/non-goals, acceptance, decisions/assumptions, task/dependency order, verification plan, risk/Gates, rollback, and unresolved blockers. Do not call a Gate operation or interpret silence as approval.

Planning is complete only when the authoritative plan validates, every task is traced/scoped, no material decision is pending, and the host records all required planning approvals.

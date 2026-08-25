---
name: devweave
description: Govern repository changes with typed plans, risk-adaptive Gates, scoped tasks, controlled verification, and Codex app-server. Trigger on `$devweave`, DevWeave run/status/check/verify requests, or managed product changes.
---

# DevWeave

DevWeave is the only project workflow skill. Read the repository [knowledge map](../../../docs/index.md) and [architecture](../../../ARCHITECTURE.md); do not load all references by default.

## Route first

1. Inspect `.devweave/project.json` without mutating it.
2. For schema version 2, use the V2 public CLI for diagnostics and the project MCP tools for agent work. Host-only lifecycle operations remain in the VS Code controller.
3. Read the current ExecPlan and load only the reference for its phase.
4. If a fact is discoverable in docs, source, schemas, or tests, inspect it. Ask the user only for a material product decision.
5. Stop at every required human Gate. Agent output never counts as approval.

## Capability split

Agent MCP tools are exactly:

- `run_inspect`
- `context_read`
- `plan_save`
- `decision_request`
- `task_update`
- `verification_run`
- `verification_read`
- `completion_request`

Only the authenticated host may start or resume a run, resolve a pending decision, decide a Gate, or cancel. Do not discover or invoke an alternate mutation path.

## Lifecycle

- Planning produces a strict `RunPlanDraft`, immutable task definitions, scoped paths, acceptance IDs, a frozen verification plan, and risk rationale. Start implementation only after every planning Gate is current.
- Implementation takes ready tasks in dependency order, changes only declared paths, and records progress through `task_update`. A material requirement/design/scope change returns to planning.
- Verification executes only the frozen plan. A successful process is evidence only when source, plan, command definition, outputs, and declared effects reconcile.
- Completion requires risk-selected review: low self-review, standard one detached review, high no more than three detached fix/reverify rounds. Unresolved critical findings block acceptance.

## Safety invariants

- Use structured argv with `shell=False`; never turn a configured command into shell permission.
- Reject stale revisions, unknown fields/methods, traversal, symlink escape, undeclared writes, and destructive Git commands before mutation.
- Keep the network denied unless an approved verification command explicitly declares otherwise.
- Do not persist raw reasoning, full prompts, secrets, or invented usage/cost. Bound and redact diagnostics.
- Do not push, open a PR, merge, reset, or switch back without separate user authorization.
- Never hand-edit canonical plan/runtime/evidence state.

## Phase references

The V2-only release skill is prepared under `assets/v2-skill/` and installed by the hash-bound finalizer. During the one authorized transition run, use these existing engine-returned references:

- [Requirements](references/requirements-phase.md)
- [Design](references/design-phase.md)
- [Implementation](references/implementation-phase.md)
- [Verification and legacy G3](references/verification-phase.md)

## Transition exception

Only run `20260825-163914-feature-devweave-v2-app-server-harness` may use the legacy CLI to finish its already-approved TASK-010 through TASK-012 and high-risk G3. Do not start, revise, or mutate any other V1 work item. Its state/event files remain engine-owned. After G3, use only the reviewed hash-bound finalizer; then run the V2 `check` and complete verification again before release.

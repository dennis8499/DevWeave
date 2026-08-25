<!-- canonical-topic: design -->
# Design decisions

## Codex integration

App-server is the interactive execution plane because the agent is part of the product experience and DevWeave needs persistent threads, streamed events, interruption, tools, and approval handling. The SDK/one-shot CLI layers were rejected for this rich lifecycle. Only stable protocol methods are allowlisted; startup probes the locally installed schema bundle before a run exists.

The product owns the Control Center, canonical plan, workflow tools, approvals, and business constraints. Codex owns the reusable agent loop and configured sandboxed execution.

## Authority split

The agent facade contains eight task-level operations. The host facade contains five lifecycle mutations. Both converge on one RunService and one reducer, so authorization is not duplicated in transport-specific code. The private host bridge uses a per-process stdin challenge/HMAC exchange; its token never appears in argv, environment, disk, or Webview state.

## State and decisions

A strict `RunPlanDraft` becomes one canonical ExecPlan. Atomic replace plus append-only event records provide restart; revision and mutation IDs provide optimistic concurrency/idempotency. Runtime thread/turn handles are replaceable hints.

Questions that block a task become typed `PendingDecision` records with two or three options, a recommendation, optional custom answer, and created revision. Only the host can answer them.

## Risk and review

- Low: planning Gate and self-review.
- Standard: planning plus acceptance Gates and one detached review.
- High: scope, design, and acceptance Gates plus at most three detached fix/reverify rounds.

Risk automatically escalates for broad/sensitive effects. It does not silently downgrade. A reviewer cannot reuse the implementation thread identity, and raw reviewer reasoning is not persisted.

## Git and migration

Each run fixes a base branch/ref and creates one same-checkout run branch after a clean preflight. Phase or vertical-slice commits include declared paths only. DevWeave never pushes, opens a PR, merges, resets, or switches back automatically.

V1 is exported from the recorded base ref into a deterministic summary/index. A hash-bound allowlist finalizer performs the clean tracked-tree cutover only after legacy high-risk acceptance; Git history remains the raw recovery mechanism.

## Verification

The project config names portable executable candidates, not resolved machine paths. A command definition contains tokenized argv, relative cwd/paths, declared writes/outputs, dependencies, timeout, profiles, expected exits, release policy, and a digest. Runtime resolution records executable provenance. Writer stages are serial; read-only stages may be bounded-parallel.

## Knowledge design

The repository map points into a small indexed docs tree. Architecture and product topics have one canonical page; generated catalogs are explicitly derived; ExecPlans are first-class active/completed artifacts; technical debt has a single tracker. The checker enforces navigation, links, topic uniqueness, size, layers, schemas, and traces.

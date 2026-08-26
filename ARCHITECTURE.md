<!-- canonical-topic: architecture -->
# DevWeave architecture

DevWeave separates the Codex harness from the workflow system of record. Codex app-server owns conversation state, turns, streaming, tool execution, sandbox enforcement, and approval requests. DevWeave owns product context, typed plans, task/Gate policy, verification evidence, Git constraints, and the user-facing Control Center.

The [documentation index](docs/index.md) maps product, operational, and quality details. This file defines dependency direction and authority boundaries.

## Authority model

```text
Human decision / approval
          │
          ▼
VS Code host ── authenticated host bridge ── RunService host facade
          │                                      │
          │ app-server JSONL                     ▼
          ├──────────────────────────────► canonical ExecPlan
          │                                      ▲
          ▼                                      │
Codex thread/turn ── exact MCP allowlist ── RunService agent facade
          │
          ▼
event reducer ──► explicitly labelled UI projection
```

The canonical ExecPlan is authoritative. App-server deltas are projections until an authoritative completion event arrives. Ignored runtime records may help reconnect but never decide a Gate or task.

## Python dependency layers

Imports may point within the same layer or toward a lower-numbered layer only.

1. Foundation: errors and version constants.
2. Contract utilities: canonical JSON, strict parsing, redaction.
3. Domain contracts: plans, snapshots, risk, schema registry, project configuration, fingerprints, reducer rules.
4. Storage and execution: plan/evidence stores, Git port, verification engine, V1 exporter, architecture checker.
5. Application services: RunService, Git transaction, Codex doctor, service factory.
6. Adapters and entrypoints: CLI, MCP, authenticated host bridge, host operations.

The exact module map is encoded in `architecture_check.py`. An import from a lower layer into a higher layer fails `REVERSE_DEPENDENCY`.

## TypeScript dependency layers

1. Versioned contracts and app-server protocol types.
2. Transport and event reduction.
3. App-server session plus narrow approval/review/host clients.
4. Workspace controller.
5. UI projection, intent parsing, and evidence collection.
6. VS Code host and Webview rendering.

The Webview cannot access the filesystem, shell, network, host token, or raw app-server channel. It sends exact validated intents and renders a bounded projection.

## Boundary invariants

- Every public schema is strict, versioned, bounded, canonically serialized, and traced to requirements/acceptance.
- Agent and host capabilities are separate facades; transport discovery never grants authority.
- Verification uses tokenized argv, `shell=False`, dependency closure, serial writer barriers, bounded resources, and declared-effect reconciliation.
- A writable Codex turn is representable only by an existing physical `directory/**` task declaration. Exact-file and other glob shapes stay read-only instead of being widened, and approval checks reject traversal plus symlink/junction components.
- Git work is based on a fixed base ref and scoped local commits. Task, Gate, and completed-archive transitions write the post-transition ExecPlan before a crash-recoverable commit, then bind its deterministic `refs/devweave/checkpoints/...` ref to that commit. No implicit remote operation, merge, reset, or branch restoration exists.
- Durable documentation is indexed under `docs/`; run/runtime artifacts do not become a second knowledge system.
- Privacy boundaries discard reasoning and avoid storing prompts, credentials, or inferred usage.

## Mechanical enforcement

The public `check` command validates navigation depth, local links, canonical topics, root/skill/module size, layer direction, schema catalog parity, acceptance traceability, and exception metadata. See [quality](docs/quality.md) for commands and [architecture exceptions](docs/architecture-exceptions.json) for the strict waiver format.

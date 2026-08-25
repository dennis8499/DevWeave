# DevWeave 2.0.0

DevWeave is a repository-owned SDLC harness for Codex. Its VS Code Control Center embeds the Codex app-server lifecycle, while a project-scoped MCP server exposes a small agent-safe workflow surface. The application owns product context, approvals, Gates, verification policy, and the canonical ExecPlan.

Start with the [documentation map](docs/index.md) and [architecture](ARCHITECTURE.md).

## What changed in 2.0.0

- Codex app-server is the interactive execution plane: persistent threads, turns, streamed events, steering, interruption, review, and approval requests.
- Agent workflow access is exactly eight allowlisted MCP tools; consequential lifecycle mutations are host-only.
- One schema-v2 ExecPlan is authoritative and crash-recoverable. Runtime logs, locks, and thread handles are ignored state.
- Verification is a frozen DAG with `shell=False`, bounded execution, declared writes, deterministic selection, and source-bound evidence.
- Risk selects required human Gates and review depth. High risk permits at most three detached fix/reverify rounds.
- Repository knowledge lives in a bounded `docs/` tree. Root guidance is intentionally short and architecture constraints are executable.
- V1 is a clean cutover, not a dual reader. A deterministic export index plus Git history preserve recovery.

## Prerequisites

- Windows x64 and VS Code 1.90+ are the first certification target.
- Python 3.11+, Git, Node.js/npm for extension development, and a locally installed Codex CLI.
- Codex must be discoverable on `PATH` or configured as an absolute `devweave.codexPath`.

DevWeave never downloads Codex or silently falls back to a clipboard workflow.

## Public CLI

The stable public surface has six verbs:

```text
python -B .agents/skills/devweave/scripts/devweave_v2_cli.py --repo . doctor
python -B .agents/skills/devweave/scripts/devweave_v2_cli.py --repo . inspect
python -B .agents/skills/devweave/scripts/devweave_v2_cli.py --repo . check
python -B .agents/skills/devweave/scripts/devweave_v2_cli.py --repo . verify --run <run-id>
python -B .agents/skills/devweave/scripts/devweave_v2_cli.py --repo . export-v1 --source-ref <git-ref> --output <path>
python -B .agents/skills/devweave/scripts/devweave_v2_cli.py --repo . mcp-serve
```

All commands emit a stable schema-v2 JSON envelope. Workflow start/resume, decision resolution, Gate decisions, and cancellation are intentionally absent; the authenticated extension host owns them.

## Development checks

```text
python -B -m unittest discover -s tests -p "test_v2_*.py" -v
```

In `vscode-extension/`:

```text
npm run typecheck
npm test
npm run build
```

The release workflow additionally requires a real Codex app-server walkthrough, UI evidence with commit/protocol provenance, a disposable-clone finalizer rehearsal, and the risk-selected review/Gate policy.

## Design basis

The repository structure follows OpenAI's [Harness Engineering](https://openai.com/zh-Hant/index/harness-engineering/) guidance: give agents a map, keep knowledge versioned and progressively disclosed, make the application observable, and encode architecture as mechanical invariants. The product boundary follows [Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform): app-server supplies the agent loop and sandboxed execution; DevWeave supplies workflow context, tools, business rules, consent, and its system of record.

License: MIT.

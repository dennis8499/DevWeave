# DevWeave repository map

DevWeave 2.0.0 is a repository-owned SDLC harness built around Codex app-server. This file is a map, not a handbook.

## Read order

1. Start with the [documentation index](docs/index.md).
2. Read [architecture](ARCHITECTURE.md) before changing boundaries or dependencies.
3. Use the [DevWeave skill](.agents/skills/devweave/SKILL.md) for governed work.
4. Load only the phase reference and source files needed for the current task.

## Sources of truth

- Product intent and acceptance: [product](docs/product.md).
- System decisions and interfaces: [design](docs/design.md).
- Runtime and recovery guarantees: [reliability](docs/reliability.md).
- Trust boundaries: [security](docs/security.md).
- Checks and traceability: [quality](docs/quality.md).
- Active and completed work: [ExecPlans](docs/exec-plans/active/README.md).

Code and typed schemas define current behavior. Documentation explains intent and navigation. A canonical ExecPlan defines one run; ignored runtime data is never workflow truth.

## Non-negotiable boundaries

- Parse and validate every external data shape at its boundary; reject unknown privileged methods and fields.
- Agent-facing MCP exposes exactly eight workflow tools. Start/resume, human decisions, Gates, and cancel remain host-only.
- Run verification only through the frozen plan with tokenized argv, `shell=False`, bounded time/output, declared effects, and network denied by default.
- Keep repository-relative scope; reject traversal, symlink escape, undeclared writes, stale revisions, and destructive Git operations.
- Never persist raw reasoning, full prompts, credentials, or estimated usage/cost. Redact and bound diagnostics.
- Do not push, open a pull request, merge, reset, or switch branches unless the user separately authorizes that action.
- Do not edit canonical run JSON by hand. Use MCP, the public CLI, or the authenticated host bridge.

## Mechanical checks

Run from the repository root:

```text
python -B .agents/skills/devweave/scripts/devweave_v2_cli.py --repo . check
python -B -m unittest discover -s tests -p "test_v2_*.py" -v
```

For the Extension, run `npm run typecheck`, `npm test`, and `npm run build` in `vscode-extension/`. Architecture exceptions require an exact code/path plus owner, reason, and unexpired date in [the exception ledger](docs/architecture-exceptions.json).

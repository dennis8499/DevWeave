<!-- canonical-topic: docs-index -->
# DevWeave knowledge map

Start here, then open only the page needed for the current task.

| Need | Canonical page |
| --- | --- |
| System boundaries and dependency direction | [Architecture](../ARCHITECTURE.md) |
| Product behavior and acceptance catalog | [Product](product.md) |
| Chosen interfaces and rejected alternatives | [Design](design.md) |
| Restart, verification, Git, and release recovery | [Reliability](reliability.md) |
| Authorization, sandbox, privacy, and threats | [Security](security.md) |
| Test matrix, architecture checks, and traces | [Quality](quality.md) |
| Current work | [Active ExecPlans](exec-plans/active/README.md) |
| Finished work | [Completed ExecPlans](exec-plans/completed/README.md) |
| Known structural debt | [Tech debt](exec-plans/tech-debt.md) |
| Generated machine references | [Generated references](generated/README.md) |

The root [repository map](../AGENTS.md) stays short by design. The project [DevWeave skill](../.agents/skills/devweave/SKILL.md) routes governed work and progressively discloses phase instructions.

## Truth rules

- Typed schemas and current source define behavior.
- Product and design pages define durable intent and decisions.
- One canonical ExecPlan defines each run and carries its approved requirements, tasks, Gates, and verification plan.
- Generated files are derived references and say how to regenerate or validate them.
- A contradiction is fixed at the canonical source; it is not patched by creating another overview.

---
name: devweave
description: Govern repository changes with typed ExecPlans, risk-adaptive human Gates, scoped tasks, controlled verification, and Codex app-server. Trigger on `$devweave`, DevWeave run/status/check/verify requests, or managed product changes.
---

# DevWeave

DevWeave is this repository's only workflow skill. Begin at the [knowledge map](../../../docs/index.md) and [architecture](../../../ARCHITECTURE.md), then load one phase reference.

## Route

1. Run the public `doctor`/`check` diagnostics before starting work. Missing Codex or required MCP readiness blocks a run; never download or substitute another harness.
2. The authenticated VS Code host starts/resumes runs and handles decisions, Gates, and cancellation. Agents cannot call those operations.
3. Use `run_inspect` to read the current snapshot. Load only context allowed by `context_read` and the current task.
4. Follow [planning](references/planning.md), [implementation](references/implementation.md), or [verification](references/verification.md) according to the authoritative phase.
5. Stop for each required human Gate. Agent/reviewer output is evidence, never approval.

## Exact agent surface

The project MCP server exposes only `run_inspect`, `context_read`, `plan_save`, `decision_request`, `task_update`, `verification_run`, `verification_read`, and `completion_request`. Reject any passthrough or unknown tool.

## Universal invariants

- Validate strict schema version 2 and unknown fields at every privileged boundary.
- Use expected revision plus mutation ID for state changes; never edit plans/events/evidence directly.
- Work only in the current immutable task's declared paths and dependencies.
- Use tokenized argv, `shell=False`, bounded resources, declared effects, and the frozen verification plan.
- Reject traversal, symlink escape, stale revisions, out-of-scope writes, and destructive/remote Git operations.
- Never persist raw reasoning, complete prompts, credentials, or estimated usage/cost.
- Do not push, open a PR, merge, reset, or switch branches without separate user authorization.
- A material change to approved intent returns to planning and invalidates downstream approvals/evidence.

## Completion

Low risk uses self-review; standard uses one detached review; high risk permits at most three detached fix/reverify rounds. Unresolved critical findings, failed/currentness checks, or missing required evidence block acceptance. Human acceptance remains mandatory whenever the plan requires it.

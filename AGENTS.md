# DevWeave repository policy

DevWeave is the repository-managed SDLC workflow. Its single router skill is `.agents/skills/devweave/SKILL.md`.

If `.devweave/project.json` does not exist or its `managed` field is false, activate DevWeave only when the user explicitly invokes `$devweave`.

If `.devweave/project.json` exists and `managed` is true, use DevWeave before modifying product source, tests, schemas, dependencies, build configuration, or CI configuration. Read-only exploration, explanation, status reporting, and review do not create a work item. The hook conservatively guards major write tools because it cannot reliably classify every language-neutral file type.

For managed changes:

1. Resolve or create a work item through the DevWeave Python CLI.
2. Bind the current Codex session through `devweave bind`.
3. Follow `devweave instructions` and load only its current phase reference.
4. During G1, read `wiki/index.md` before at most five related pages and record the full knowledge context. Use raw sources only to resolve a recorded missing, placeholder, stale, or contradictory Wiki gap.
5. Do not implement until G2 is approved and current. Keep Wiki read-only through G2 and implementation.
6. During verification, refresh or delete only affected/planned Wiki pages, synchronize index, append a work-attributed promote log entry, and seal the promoted pages before G3.
7. Do not close until G1, G2, and G3 are approved and current.
8. Never edit DevWeave JSON state, event, or evidence ledgers directly.

`.devweave/baseline/` is accepted governance truth; root `wiki/` is detailed, source-bound codebase knowledge. Wiki-first controls read order, not factual priority: current source behavior and approved DevWeave artifacts win conflicts, which must be recorded as gaps.

Machine keys and protocols are English. User-facing discovery, approval summaries, artifacts, and acceptance reports are Traditional Chinese unless the user asks otherwise. DevWeave observes Git state but never implicitly creates branches, worktrees, commits, or pushes.

The single PreToolUse hook is a Codex guardrail, not an operating-system sandbox. It rejects Wiki writes before verification and allows only the exact knowledge plan plus coupled index/log paths afterward. It requires repository trust and cannot prevent edits made outside Codex or after hooks are disabled; G3 rechecks the complete Wiki diff.

## Companion engineering skills

DevWeave remains the sole SDLC router. The only approved project-local companion skills are `grill-me`, `grilling`, `codebase-design`, `diagnosing-bugs`, and `tdd`. They provide methods inside the current DevWeave phase; they never create a parallel work-item lifecycle or replace DevWeave artifacts, state, evidence, or human gates.

DevWeave instructions take precedence whenever a companion skill conflicts with repository policy:

1. Resolve the work item, request session binding, and follow the current `devweave instructions` response before invoking a companion skill for a managed change.
2. Use `grill-me`/`grilling` during requirements, `codebase-design` during G2 design, `diagnosing-bugs` for bug discovery and post-G2 diagnosis, and `tdd` only during implementation with a current G2 approval.
3. Use the Wiki context and approved DevWeave artifacts already loaded for the work item. Do not independently create or update `CONTEXT.md`, ADRs, `docs/agents/`, specs, tickets, or alternate planning documents.
4. Before G2, do not modify tracked product source or tests. Bug discovery must use an existing command or a temporary/cache harness; convert it into a tracked regression test only after G2.
5. Keep Wiki read-only until verification. During verification, only DevWeave's declared knowledge plan may update Wiki content, index, or log.
6. Do not create issues, branches, worktrees, commits, pushes, pull requests, deployments, or production instrumentation unless a separate, explicit user authorization covers that action. A companion skill's suggestion is not authorization.
7. Never edit DevWeave JSON/JSONL ledgers directly. Record useful companion-skill outcomes in the current work artifact or through the DevWeave evidence CLI.
8. If a companion skill reveals a needed requirement, design, scope, or task change, run `$devweave revise` from the earliest affected phase and wait for the invalidated gate to be reapproved.

Companion skill updates are executable policy changes. Do not update them automatically: open a new DevWeave feature work item, review the upstream instruction diff and `skills-lock.json`, rerun repository verification, and complete G3.

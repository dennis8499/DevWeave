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

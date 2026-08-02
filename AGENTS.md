# DevWeave repository policy

DevWeave is the repository-managed SDLC workflow. Its single router skill is `.agents/skills/devweave/SKILL.md`.

If `.devweave/project.json` does not exist or its `managed` field is false, activate DevWeave only when the user explicitly invokes `$devweave`.

If `.devweave/project.json` exists and `managed` is true, use DevWeave before modifying product source, tests, schemas, dependencies, build configuration, or CI configuration. Read-only exploration, explanation, status reporting, and review do not create a work item. The hook conservatively guards major write tools because it cannot reliably classify every language-neutral file type.

For managed changes:

1. Resolve or create a work item through the DevWeave Python CLI.
2. Bind the current Codex session through `devweave bind`.
3. Follow `devweave instructions` and load only its current phase reference.
4. Do not implement until G2 is approved and current.
5. Do not close until G1, G2, and G3 are approved and current.
6. Never edit DevWeave JSON state, event, or evidence ledgers directly.

Machine keys and protocols are English. User-facing discovery, approval summaries, artifacts, and acceptance reports are Traditional Chinese unless the user asks otherwise. DevWeave observes Git state but never implicitly creates branches, worktrees, commits, or pushes.

The PreToolUse hook is a Codex guardrail, not an operating-system sandbox. It requires repository trust and cannot prevent edits made outside Codex or after hooks are disabled.

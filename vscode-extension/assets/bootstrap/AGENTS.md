# DevWeave repository policy

This repository uses DevWeave as its single SDLC router. Read `.agents/skills/devweave/SKILL.md` before changing managed project files.

## Managed workflow

- Resolve or create a work item, bind the current session, and follow `devweave instructions`.
- Read `wiki/index.md` and the smallest relevant Wiki context during G1.
- Do not modify product source or tracked tests before G2 is approved.
- Complete G1, G2, verification, Knowledge Review, and G3 before closing a work item.
- Never edit `.devweave` JSON or JSONL state, event, or evidence ledgers directly.

## Repository boundaries

DevWeave observes Git state but does not create branches, worktrees, commits, pushes, pull requests, or deployments implicitly. The Extension is a filesystem projection and prompt handoff surface; it must not execute shell, process, CLI, or network operations.

## Companion skills

`codebase-design`, `diagnosing-bugs`, `grill-me`, `grilling`, and `tdd` are methods inside the current DevWeave phase. They do not replace DevWeave artifacts, gates, evidence, or human approval.

Machine keys and protocols remain English. User-facing discovery, approvals, and acceptance reports use Traditional Chinese unless the user asks otherwise.

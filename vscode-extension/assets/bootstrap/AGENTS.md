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

## Interactive decisions

During G1/G2, ask only material requirements/design decisions. Prefer the Codex host's native question facility with two or three mutually exclusive options, the recommended option first marked `(Recommended)`, evidence/trade-off descriptions, and `Other` freeform. If native questions are unavailable, use the same structured numbered fallback with an explicit custom-answer entry. Ask one question at a time, wait for the answer, and return it to the current artifact; do not create a second question state or ledger.

Initial Plan Mode preflight applies before every pre-G2 Work Item mutation: `new`, `feature`, `refactor`, `bug`, `wiki bootstrap`, and `revise` returning to G1/G2. The Router uses visible `request_user_input` as the only host capability evidence; if it is unavailable, stop before `start`, `bind`, `revise`, or bootstrap Work Item creation and ask the user to switch to Plan Mode. Only an explicit compatibility choice permits the structured numbered fallback. The Extension cannot inspect or switch host mode.

Machine keys and protocols remain English. User-facing discovery, approvals, and acceptance reports use Traditional Chinese unless the user asks otherwise.

## Initialization order

- DevWeave `init` checks Wiki compatibility before the project lock and repeats the check inside the lock before creating `.devweave` control state.
- Missing, empty, or custom-only Wiki content is compatible and receives only missing starters; incompatible reserved starter paths return `knowledge_conflict` without overwriting user bytes or leaving a partial control bundle.

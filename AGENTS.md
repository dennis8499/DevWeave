# DevWeave repository policy

DevWeave is the repository-managed SDLC workflow. Its single router skill is `.agents/skills/devweave/SKILL.md`.

If `.devweave/project.json` does not exist or its `managed` field is false, activate DevWeave only when the user explicitly invokes `$devweave`.

If `.devweave/project.json` exists and `managed` is true, use DevWeave before modifying product source, tests, schemas, dependencies, build configuration, or CI configuration. Read-only exploration, explanation, status reporting, and review do not create a work item. The hook conservatively guards major write tools because it cannot reliably classify every language-neutral file type.

For managed changes:

1. Resolve or create a work item through the DevWeave Python CLI.
2. Bind the current Codex session through `devweave bind`.
3. Follow `devweave instructions` and load only its current phase reference.
4. During G1, read `wiki/index.md` before at most five related pages and record the full knowledge context, including page content hashes and source fingerprints. Use raw sources only after recording a missing, placeholder, stale, contradictory, or insufficient Wiki gap, and inspect the smallest necessary source range.
5. Do not implement until G2 is approved and current. Keep Wiki read-only through G2 and implementation.
6. During verification, every new-format work item must complete a current Knowledge Review. Use `promote` for durable reusable knowledge; use `no-update` only for non-bootstrap work with a rationale, no affected page, no Wiki diff, and no knowledge plan.
7. A promote plan may upsert/delete at most five content pages. Refresh or delete every affected page, cover durable uncovered changes with one or more pages, synchronize index, append one work-attributed promote log entry, and seal active pages before G3. Scaffolded placeholders and template tokens cannot be sealed.
8. Do not close until G1, G2, and G3 are approved and current.
9. Never edit DevWeave JSON state, event, or evidence ledgers directly.

High-risk G3 review contract:

- After final product/Wiki/baseline/diff/scope/evidence stabilization, the single DevWeave router starts exactly one isolated, read-only Independent Review Agent. Standard and low-risk G3 do not start it; G2 `Design It Twice` remains the separate conditional 3+ sub-agent design comparison.
- The reviewer receives only approved artifacts, complete diff, risk analysis, scope, accepted baseline, Wiki context, source fingerprint, Git HEAD, and existing evidence. It must not inherit main-Agent reasoning, modify source/Wiki/ledger, delegate, or run approve/revise/close.
- The Python engine never spawns the reviewer. The router records the fixed result through machine-only `review record`; the VS Code Extension only projects missing/unavailable/advisory/critical readiness and never starts Agent or mutates workflow.
- `passed` is accepted; unavailable/timeout/malformed fallback and advisory findings are warnings; named critical security, data-loss, irreversible, or scope findings block G3 unless each exact `F-###` target has a narrow acceptance `review-critical` waiver. Source fingerprint changes stale the review. Human G3 approval remains required.

`.devweave/baseline/` is accepted governance truth; root `wiki/` is detailed, source-bound codebase knowledge. Wiki-first controls read order, not factual priority: current source behavior and approved DevWeave artifacts win conflicts, which must be recorded as gaps.

Initialization preflight is ordered before the project lock and before any `.devweave` control write, then repeated inside the lock. Missing, empty, or custom-only Wiki content is compatible; reserved starter type/frontmatter conflicts preserve Wiki bytes and leave no partial control bundle from that init call.

`$devweave wiki bootstrap` is the only public Codebase Wiki bootstrap entry. It routes through `knowledge bootstrap`, explores the whole repository, and uses a normal feature work item with `knowledge_profile: bootstrap` plus the existing G1/G2/G3 lifecycle. An already complete core Wiki creates no work item; a missing bootstrap is advisory and does not block ordinary work. Bootstrap may write three to five planned Wiki content pages in G3 but must not modify product source.

Machine keys and protocols are English. User-facing discovery, approval summaries, artifacts, and acceptance reports are Traditional Chinese unless the user asks otherwise. DevWeave observes Git state but never implicitly creates branches, worktrees, commits, or pushes.

The single PreToolUse hook is a Codex guardrail, not an operating-system sandbox. It rejects Wiki writes before verification and allows only the exact knowledge plan plus coupled index/log paths afterward. It requires repository trust and cannot prevent edits made outside Codex or after hooks are disabled; G3 rechecks the complete Wiki diff.

## Companion engineering skills

DevWeave remains the sole SDLC router. The only approved project-local companion skills are `grill-me`, `grilling`, `codebase-design`, `diagnosing-bugs`, and `tdd`. They provide methods inside the current DevWeave phase; they never create a parallel work-item lifecycle or replace DevWeave artifacts, state, evidence, or human gates. The maintenance-only `writing-great-skills` Skill helps maintain these instructions; it is outside the five-companion allowlist, never routes work, and is excluded from product SDLC behavior.

DevWeave instructions take precedence whenever a companion skill conflicts with repository policy:

Interactive decision contract:

- Facts that can be discovered from Wiki, source, tests, or approved artifacts are resolved by inspection; they are not delegated back to the user as questions.
- During G1, `grill-me`/`grilling` asks only material requirements decisions; during G2, `codebase-design` asks only material design decisions. Follow `.agents/skills/devweave/references/native-question-contract.md`: the canonical host tool is `request_user_input`, one question at a time, two or three mutually exclusive options, the recommended option first and marked `(Recommended)`, evidence/trade-off descriptions, and host `Other`.
- Plan-first is mandatory for G1/G2/Gate decisions before current G2. If an ordinary-mode Skill needs a material decision and the native tool is not visible, stop and request Plan Mode; only when the host cannot switch modes or the user explicitly chooses compatibility may the same question become a structured numbered fallback. After current G2, ordinary mode is limited to approved implementation tasks; new material decisions return through `$devweave revise`.
- Each question is asked one at a time with a recommendation and trade-off, and the agent waits for the answer.
- Tool visibility is a Codex host capability. Skills and the VS Code Extension cannot register `request_user_input`, create a fake question UI, or claim ordinary-mode native support without host evidence. The complete request/result and Gate safety contract is in the shared reference above.
- User answers return to the current DevWeave artifacts. An unanswered material decision, silence, or ambiguous agreement never permits the agent to invent a decision or approve a Gate.
- G1/G2 summaries are Double Checks after validation. New requirements, design, scope, or task decisions use `$devweave revise` from the earliest affected phase; G3 verifies approved intent rather than silently redefining it.

1. Resolve the work item, request session binding, and follow the current `devweave instructions` response before invoking a companion skill for a managed change.
2. Use `grill-me`/`grilling` during requirements, `codebase-design` during G2 design, `diagnosing-bugs` for bug discovery and post-G2 diagnosis, and `tdd` only during implementation with a current G2 approval.
3. Use the Wiki context and approved DevWeave artifacts already loaded for the work item. Do not independently create or update `CONTEXT.md`, ADRs, `docs/agents/`, specs, tickets, or alternate planning documents.
4. Before G2, do not modify tracked product source or tests. Bug discovery must use an existing command or a temporary/cache harness; convert it into a tracked regression test only after G2.
5. Keep Wiki read-only until verification. During verification, only DevWeave's declared knowledge plan may update Wiki content, index, or log.
6. Do not create issues, branches, worktrees, commits, pushes, pull requests, deployments, or production instrumentation unless a separate, explicit user authorization covers that action. A companion skill's suggestion is not authorization.
7. Never edit DevWeave JSON/JSONL ledgers directly. Record useful companion-skill outcomes in the current work artifact or through the DevWeave evidence CLI.
8. If a companion skill reveals a needed requirement, design, scope, or task change, run `$devweave revise` from the earliest affected phase and wait for the invalidated gate to be reapproved.

Companion skill updates are executable policy changes. Do not update them automatically: open a new DevWeave feature work item, review the upstream instruction diff and `skills-lock.json`, rerun repository verification, and complete G3.

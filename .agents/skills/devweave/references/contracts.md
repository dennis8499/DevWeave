# DevWeave v1 Contracts

Read this reference for CLI usage, artifact grammar, state recovery, or an ambiguous workflow. The Python engine is the executable source of truth.

## Runtime and persistence

- Runtime: Python 3.11 or newer, standard library only, inside a Git repository.
- Schema version: integer `1` in both `project.json` and every `state.json`.
- Encoding: UTF-8 for JSON, JSONL, Markdown, and hook output.
- Writes: atomic temporary-file plus `os.replace` for JSON and generated text.
- Concurrency: one atomic directory lock per work item and a separate project lock.
- Events: append-only `events.jsonl`; never use it as mutable state.
- Raw command output: `.devweave/cache/logs/<work-id>/<EVID-id>.log`, limited by project policy and excluded from Git.
- Independent review output: the existing router writes a bounded report under `.devweave/cache/incoming/<work-id>/`; the engine alone redacts, hashes, and persists it as `kind: review` evidence under `.devweave/cache/logs/<work-id>/`.

Machine state is authoritative. Update state, tasks, approvals, evidence, scope, risk, baseline decisions, commands, and waivers only through the CLI. Codex edits the five Markdown artifacts and product files.

## Project model

`.devweave/project.json` contains:

- `schema_version`, `managed`, and `locale`.
- `commands[]`, each with unique `id`, string-array `argv`, repo-relative `cwd`, positive `timeout_seconds`, and `required_for[]` risk levels. Optional `depends_on[]` lists command IDs that must pass first; optional `exclusive_group` serializes commands that share a mutable build/output boundary.
- `verification_profiles.low|standard|high`, containing required command IDs.
- `protected_mutations[]` and evidence storage policy.
- `knowledge.enabled: true` and the normalized fixed `knowledge.root: wiki`. Missing knowledge settings are supplied in memory and persisted by the next explicit `init` or `start`.

Commands are executed with `shell=false`. Never convert `argv` to a shell string. `verify --profile <risk> --max-parallel <n>` schedules independent profile commands concurrently, respects `depends_on` and `exclusive_group`, and records one normal evidence entry per executed command. A failed dependency blocks its dependents without fabricating passing evidence; `verify --command <id>` remains the compatibility path for one command.

## Work-item model

`.devweave/work-items/<id>/state.json` contains:

- identity: `id`, `kind`, `title`, `schema_version`, timestamps, and active/closed status;
- lifecycle: `phase`, three gate records, and optional blocker;
- scope: risk classification, risk rationale, downgrade rationale, paths, and scope rationale;
- provenance: `base_source`, `base_baseline`, optional `base_knowledge`, Git HEAD/branch/diff fingerprint, and `last_verification`;
- ledgers: machine task state, evidence summaries, waivers, and baseline-update decisions.
- knowledge-aware work adds optional `knowledge_profile: "bootstrap"`, `knowledge_review_required`, `knowledge_context` (`pages`, ordered `records`, `gaps`, `recorded_at`), `knowledge_review` (`disposition`, `rationale`, affected/covered/uncovered paths, change fingerprint, timestamps), and `knowledge_updates` (`upserts`, `deletes`, `coupled`, `rationale`, `sealed`, change fingerprint, `recorded_at`). New work defaults `knowledge_review_required: true`; missing review fields identify a legacy active item and never add retrospective G1/G3 blockers.

Valid phases are:

```text
requirements -> design -> implementation -> verification -> acceptance_review -> closed
       ^            ^             ^
       |            |             +-- G3 rejection or source/evidence change
       |            +---------------- G2 rejection or design/plan change
       +----------------------------- G1 rejection or brief/requirements/risk/scope change
```

`scope_review` and `build_review` are valid review aliases. Gate status is `pending`, `approved`, or `stale`. Every approval records the artifact fingerprint, Git identity, UTC timestamp, and an append-only event.

## Fingerprints and invalidation

- G1 fingerprint: exact `brief.md`, `requirements.md`, risk, scope, G1 waivers, and—when knowledge-aware—the recorded index-first knowledge context.
- G2 fingerprint: G1 material plus exact `design.md`, `plan.md`, and G2 waivers.
- G3 fingerprint: G2 material plus exact `acceptance.md`, current product-source fingerprint, evidence ledger, the complete living-baseline tree fingerprint, knowledge-tree fingerprint and promotion ledger, and G3 waivers.
- Product-source fingerprint: Git HEAD plus path/content/staged/unstaged diff material, excluding DevWeave machine state, its skill implementation, Codex configuration, and the configured Wiki root.
- Knowledge fingerprint: sorted path/content hashes of every file under the Wiki root. A Wiki-only change therefore invalidates G3 without staling product verification evidence.

Invalidation is monotonic until reapproval:

- G1 material change invalidates G1, G2, and G3 and returns to requirements.
- G2 material change keeps G1 and invalidates G2 and G3 and returns to design.
- Post-verification source change marks source-bound evidence stale, clears the verification snapshot, invalidates G3, and returns to verification while G2 remains current.
- A product-source fingerprint change invalidates a recorded Knowledge Review and clears its knowledge plan. Wiki-only changes do not change the product-source fingerprint but are reconciled independently at G3.
- G3 artifact, evidence, baseline, or waiver change invalidates G3.
- Closed work remains in place and cannot be reopened; start a new work item.

## Wiki knowledge model

`init` and `start` non-destructively ensure root `wiki/` contains `index.md`, `overview.md`, `log.md`, and typed directories for architecture, modules, entities, patterns, decisions, dependencies, guides, and synthesis. A missing, empty, or custom-only Wiki is compatible and receives only missing starters; reserved starter files/directories are adopted only when their filesystem type and frontmatter are compatible. A wrong reserved type or frontmatter returns `knowledge_conflict`; `doctor` reports the same condition.

Supported page types are `overview`, `architecture`, `module`, `entity`, `pattern`, `decision`, `dependency`, `guide`, `synthesis`, `index`, and `log`. Every page retains `title`, `type`, `sources`, `last_updated`, `tags`, and `status`, plus:

- `source_fingerprint`: `sha256:<hex>` for sourced pages and `none` for an empty source list;
- `verified_by`: the work ID that most recently promoted the page.

Sources are normalized, unique, repo-relative paths and may not enter Wiki, `.devweave`, or `.git`. A page lists at most five. Files hash current bytes; symlinks hash their target text. Directories expand sorted Git-tracked and non-ignored untracked files, including tracked missing entries, then hash canonical path/content material. Source deletion, dirty content, rename, or directory membership changes therefore stales the page.

G1 records `wiki/index.md` first and at most five related pages through `knowledge context`; missing, placeholder, stale, invalid, or contradictory knowledge requires a gap before raw-source fallback. G2 and implementation keep Wiki read-only. Source behavior and approved artifacts outrank conflicting Wiki claims.

Project initialization runs a read-only Wiki reserved-starter preflight before the project lock and repeats it inside the lock before creating `.devweave/project.json`, baselines, cache, or work-item directories. An incompatible reserved path therefore preserves Wiki bytes and does not leave a partial control bundle.

`knowledge bootstrap` assesses the whole repository Wiki. If an active, sourced, current overview, architecture page, and module page already exist, it returns `already_complete` without creating work. Otherwise it resumes the single active bootstrap profile or creates a normal feature work item with `knowledge_profile: "bootstrap"`. Bootstrap follows the same G1/G2/G3 lifecycle, accepts no scope argument, changes no product source, plans three to five content pages, and never permits `no-update` or deletion.

Every new-format work item records a current Knowledge Review during verification. `promote` requires a non-empty plan of one to five content upserts/deletes. `no-update` requires a non-bootstrap item, non-empty rationale, no affected page, no Wiki diff, and no plan. Coverage separates changed product paths into covered and uncovered paths using active page-source overlap; durable uncovered changes may be represented by one or more pages rather than one page per source file.

`knowledge scaffold` creates only a planned new upsert, only after current G2 and a current promote review. It renders one of the nine canonical content templates with valid repo-relative sources through an exclusive no-overwrite write. The new page remains `placeholder` until edited active. Dependency scaffolds require package name/version; decision scaffolds require date and `proposed|accepted|deprecated|superseded` status. Seal rejects placeholders, unreplaced template tokens, invalid sources, and critical lint.

At verification, affected pages are computed only from this work's changed product paths against each page's sources captured in `base_knowledge`. Affected pages must be an active/current sealed upsert or a declared deletion. Other stale pages are warnings. A work item may upsert/delete at most five content pages total. Any content target automatically authorizes `wiki/index.md` and `wiki/log.md`; both must actually change and be sealed. The log body must preserve its base prefix and append exactly one `promote` heading containing the work ID. `new` also requires an active, sourced, sealed overview.

Wiki lint treats malformed frontmatter, invalid/missing sources, invalid source fingerprints, ambiguous or broken wikilinks, missing/duplicate index entries, and rewritten log history as critical. Placeholder, unsealed, orphan, stale, coverage-review, and semantic-review findings are warnings unless the page is affected or a declared promotion target.

## Artifact grammar and traceability

Human-facing artifacts are `brief.md`, `requirements.md`, `design.md`, `plan.md`, and `acceptance.md`. Required prose is Traditional Chinese by default.

- Use contiguous, unique second-level `REQ-###` and `NFR-###` headings.
- Use contiguous, unique second-level `AC-###` headings. Every requirement links to an existing AC, and every AC links to an existing requirement.
- Use contiguous, unique second-level `DEC-###` headings linked to existing requirements.
- Use contiguous, unique second-level `TASK-###` headings linked to existing requirements, ACs, and decisions.
- Keep approved task definitions immutable in `plan.md`; keep `pending`, `in_progress`, `blocked`, and `completed` status only in `state.json`.
- Store versioned `EVID-###` JSON summaries. Current implementation evidence links to existing AC and TASK IDs and carries the source fingerprint and Git HEAD.
- `acceptance.md` accounts for every current source-bound evidence ID and every AC.

Discovery-only bug reproduction and refactor baseline evidence may predate an approved TASK ledger. They retain AC and source provenance but do not count as green, source-bound G3 evidence.

## Profiles and risk

- `new`: current acceptance evidence for the first end-to-end vertical slice and an accepted architecture baseline decision.
- `feature`: current acceptance and regression evidence.
- `refactor`: passing pre-change baseline before G1; current equivalence and regression evidence at G3.
- `bug`: observed failing reproduction before G1 or an explicit narrow unreproducible waiver; current regression evidence at G3.
- `high`: all profile evidence plus current independent review evidence and applicable migration, rollback, security, compatibility, or performance analysis.
- High-risk independent review is exactly one isolated, read-only router-owned reviewer per G3 attempt. `passed` is accepted; unavailable or advisory is a warning; named critical security/data-loss/irreversible/scope findings block until an exact `review-critical` acceptance waiver exists. Source fingerprint changes stale the review.

Risk changes are fingerprinted. Any downgrade, including high to standard, records a separate rationale.

## Gate requirements

- G1: complete brief/requirements grammar, risk, scope, Wiki-first context, and profile discovery evidence.
- G2: current G1, complete design/plan grammar, trace graph, high-risk analysis, and explicit approval.
- G3: current G2, completed task ledger exactly matching approved plan, current AC/TASK/source-bound evidence, all required command results or narrow waivers, in-scope product diff, valid declared Wiki promotion when applicable, baseline decision, complete acceptance report, and explicit approval.
- Every baseline path changed since work-item creation must be declared as a target; every declared target must contain an attributable addition, update, or deletion.
- `close`: succeeds only when the exact current G3 fingerprint is approved.

Waivers contain `id`, `gate`, `kind`, `target`, reason, approver, and timestamp. Adding or changing one invalidates the gate whose decision it affects.

`review-critical` waivers are acceptance-gate-only and must target one named `F-###` finding. Wildcard or broad targets are invalid.

## CLI contract

Run `scripts/devweave.py --repo <path> <command>`. Output is always one JSON document on stdout.

Commands are `init`, `start`, `status`, `instructions`, `validate`, `bind`, `risk`, `scope`, `baseline`, `task start|complete|block`, `evidence add`, machine-only `review record`, `verify`, `waiver add`, `approve`, `revise`, `close`, `doctor`, `project`, `command set|list|remove`, and the router-only `knowledge` namespace. `review record` is not a public chat verb and does not add a lifecycle.

Knowledge machine commands are:

```text
knowledge status [--work <id>]
knowledge bootstrap
knowledge context --work <id> --page wiki/index.md [--page ...] [--gap ...]
knowledge review --work <id> --disposition promote|no-update --rationale <text>
knowledge plan --work <id> [--upsert ...] [--delete ...] --rationale <text>
knowledge scaffold --work <id> --page <wiki-path> --type <content-type> --title <title> --source <repo-path> ... [type fields]
knowledge seal --work <id> --page ...
```

`bootstrap` is repository-wide and idempotent. `context` and `plan` replace their complete ledgers. `context` is valid only before G1 and records page content/source observations. `review` is valid only in verification/acceptance with current G2. `plan` additionally requires a current promote review for new-format work and couples index/log automatically. `scaffold` accepts only a planned new upsert and never overwrites. `seal` accepts only planned upserts and coupled pages and preserves the page body and unknown frontmatter fields while writing date, current source fingerprint, and work provenance.

`scope` is a replace operation, not an append operation. Supply the entire intended set in one command by repeating the option: `scope --path src --path tests --rationale "..."`.

`bind` without `--session-id` deliberately returns `binding.status: awaiting_hook`. The invoking Codex session is considered bound only if the PreToolUse hook confirms the work ID through additional context. A trusted integration may supply its real session ID and receive `binding.status: bound`; agents must never invent one.

Success envelope:

```json
{
  "ok": true,
  "work": {}
}
```

Diagnostic envelope:

```json
{
  "ok": false,
  "error": {
    "code": "validation_failed",
    "message": "Human-readable diagnostic",
    "details": {}
  }
}
```

`validate` and `verify` may return domain-specific payloads with `ok: false` rather than the generic error envelope. Stable process exit codes are:

- `0`: command completed and its requested assertion passed.
- `2`: validation, artifact, state, or gate failure.
- `3`: no eligible item or ambiguous work-item selection.
- `4`: command execution failure, failed verification, or unexpected internal failure.
- `130`: interrupted by the operator.

## Public chat verbs and selection

- `new`, `feature`, `refactor`, `bug`: initialize if necessary, start one work item, bind it, then perform requirements work.
- `next`: resolve and bind one work item, obtain instructions, and execute only the returned phase.
- `status`: report state, gates, task progress, stale evidence, blocker, and next action in Traditional Chinese.
- `revise`: record the earliest affected phase and reason before changing an approved artifact.
- `approve`: validate and approve the current human gate; after G3, close.
- `wiki bootstrap`: route to `knowledge bootstrap`; report an already complete Wiki, or bind and continue the returned bootstrap work item through the normal lifecycle.

Resolve an explicitly named item first, then an item unambiguously established by the conversation, then the only eligible active item. If multiple candidates remain, show ID, title, kind, phase, and status and ask the user to choose.

`status` is informational: an initialized repository with zero eligible items returns exit `0` and an empty `work_items` array. Commands that require a work item still use exit `3` when none can be resolved.

## Language and ownership

Keep skill instructions, Python, JSON keys, IDs, and internal contracts in English. Write chat summaries and human-facing Markdown in Traditional Chinese unless the user requests another language. Inspect Git state but leave branches, worktrees, commits, pushes, PRs, deployment, and remote trackers to an explicitly authorized workflow.

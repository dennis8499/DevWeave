# Requirements Phase

Read this reference only while the work item phase is requirements or scope_review.

## Ground

1. Read `wiki/index.md` first, then choose at most five related Wiki pages.
2. Record the complete ordered set with `knowledge context --page wiki/index.md [--page ...]`. This is a replace operation.
3. When a page is missing, placeholder, stale, or contradicts current behavior, record the gap with `--gap` and inspect the smallest relevant raw-source slice. Source behavior and approved DevWeave artifacts are authoritative; preserve the contradiction as a gap.
4. Inspect accepted DevWeave baseline for governance truth, then inspect repository guidance, manifests, CI, tests, and relevant code only as needed to close gaps. Prefer concrete evidence over generic questions.

For an existing repository, propose language-neutral verification commands from commands the repository already documents or runs. `knowledge status --work <id>` reports health, placeholders, stale pages, and affected-page status without changing Wiki content.

## Produce

1. Complete brief.md in Traditional Chinese with problem, current evidence, scope, non-goals, and risk.
2. Apply the selected entry profile from profiles.md.
3. Complete requirements.md with unique REQ/NFR and AC headings. Make every requirement observable and trace it to at least one acceptance criterion.
4. Record risk and scope through the Python CLI. Configure missing project verification commands through the command subcommand.
5. For bug work, record failing reproduction evidence. For refactor work, record baseline evidence.

Run validate with gate scope. G1 validation requires the recorded index-first knowledge context; gaps are fingerprinted with the other discovery material. Resolve every error, surface waivers separately, and never infer one.

## G1

Present a concise Traditional Chinese summary of the problem, scope, non-goals, acceptance criteria, risk, assumptions, and waivers. Record G1 only after explicit human approval or an explicit $devweave approve request.

Complete when scope validation passes and G1 is recorded against the current brief, requirements, risk, and scope fingerprint. Stop at the gate if approval is absent.

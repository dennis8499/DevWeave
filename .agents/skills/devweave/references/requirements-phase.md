# Requirements Phase

Read this reference only while the work item phase is requirements or scope_review.

## Ground

1. Read `wiki/index.md` first, then choose at most five related Wiki pages.
2. Record the complete ordered set with `knowledge context --page wiki/index.md [--page ...]`. This replace operation captures each page path, status, content hash, stored source fingerprint, and observed source fingerprint.
3. When a page is missing, placeholder, stale, contradictory, or insufficient, record the gap with `--gap` before source fallback and inspect only the smallest relevant raw-source slice. Source behavior and approved DevWeave artifacts are authoritative; preserve contradictions as gaps.
4. Inspect accepted DevWeave baseline for governance truth, then inspect repository guidance, manifests, CI, tests, and relevant code only as needed to close gaps. Prefer concrete evidence over generic questions.

For an existing repository, propose language-neutral verification commands from commands the repository already documents or runs. `knowledge status --work <id>` reports health, placeholders, stale pages, bootstrap recommendation and reasons, affected-page coverage, and review state without changing Wiki content. A missing bootstrap is advisory and never blocks an ordinary work item; mention `$devweave wiki bootstrap` and continue from recorded gaps when necessary.

Summarize discovery as four explicit groups: Wiki facts, source-backed facts, inferences, and unresolved gaps. Do not present Wiki inference as source truth.

## Produce

1. Complete brief.md in Traditional Chinese with problem, current evidence, scope, non-goals, and risk.
2. Apply the selected entry profile from profiles.md.
3. Complete requirements.md with unique REQ/NFR and AC headings. Make every requirement observable and trace it to at least one acceptance criterion.
4. Record risk and scope through the Python CLI. Configure missing project verification commands through the command subcommand.
5. For bug work, record failing reproduction evidence. For refactor work, record baseline evidence.

Run validate with gate scope. G1 validation requires the recorded index-first knowledge context; context records and gaps are fingerprinted with the other discovery material. A changed page, content hash, or source observation invalidates current G1 discovery before G2. Resolve every error, surface waivers separately, and never infer one.

## G1

Present a concise Traditional Chinese summary of the problem, scope, non-goals, acceptance criteria, risk, assumptions, and waivers. Record G1 only after explicit human approval or an explicit $devweave approve request.

Complete when scope validation passes and G1 is recorded against the current brief, requirements, risk, and scope fingerprint. Stop at the gate if approval is absent.

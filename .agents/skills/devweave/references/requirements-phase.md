# Requirements Phase

Read this reference only while the work item phase is requirements or scope_review.

## Ground

1. Read `wiki/index.md` first, then choose at most five related Wiki pages.
2. Record the complete ordered set with `knowledge context --page wiki/index.md [--page ...]`. This replace operation captures each page path, status, content hash, stored source fingerprint, and observed source fingerprint.
3. When a page is missing, placeholder, stale, contradictory, or insufficient, record the gap with `--gap` before source fallback and inspect only the smallest relevant raw-source slice. Source behavior and approved DevWeave artifacts are authoritative; preserve contradictions as gaps.
4. Inspect accepted DevWeave baseline for governance truth, then inspect repository guidance, manifests, CI, tests, and relevant code only as needed to close gaps. Resolve discoverable facts from evidence; do not ask the user to provide facts already available in the repository.
5. Invoke `grill-me`/`grilling` for material requirements decisions. Prefer the Codex host's native question facility with two or three mutually exclusive options, the recommended option first marked `(Recommended)`, descriptions, and host `Other`; if unavailable, use the same structured numbered fallback with an explicit custom answer. Ask one decision at a time with current evidence, a recommendation, and the meaningful trade-off; wait for the user's answer before recording the next decision.

For an existing repository, propose language-neutral verification commands from commands the repository already documents or runs. `knowledge status --work <id>` reports health, placeholders, stale pages, bootstrap recommendation and reasons, affected-page coverage, and review state without changing Wiki content. A missing bootstrap is advisory and never blocks an ordinary work item; mention `$devweave wiki bootstrap` and continue from recorded gaps when necessary.

Summarize discovery as four explicit groups: Wiki facts, source-backed facts, inferences, and unresolved gaps. Do not present Wiki inference as source truth.

## Produce

1. Complete brief.md in Traditional Chinese with problem, current evidence, scope, non-goals, and risk.
2. Apply the selected entry profile from profiles.md and use the requirements interview to resolve material decisions.
3. Complete requirements.md with unique REQ/NFR and AC headings. Make every requirement observable and trace it to at least one acceptance criterion; return user answers to the artifact.
4. Record risk and scope through the Python CLI. Configure missing project verification commands through the command subcommand.
5. For bug work, record failing reproduction evidence. For refactor work, record baseline evidence.

Run validate with gate scope. G1 validation requires the recorded index-first knowledge context; context records and gaps are fingerprinted with the other discovery material. A changed page, content hash, or source observation invalidates current G1 discovery before G2. Resolve every error, surface waivers separately, and never infer one.

## G1

Present a concise Traditional Chinese summary of the problem, scope, non-goals, acceptance criteria, risk, assumptions, waivers, answered material decisions, and unresolved gaps. Run `validate --gate scope` before the summary. Record G1 only after explicit human approval or an explicit `$devweave approve` request; silence, ambiguous agreement, or Codex's own recommendation is not approval.

Complete when scope validation passes and G1 is recorded against the current brief, requirements, risk, scope, and knowledge context fingerprint. Stop at the Gate if approval is absent or a material question remains unanswered. If the user changes a decision after the summary, update the artifact, revalidate, and present the revised Gate summary.

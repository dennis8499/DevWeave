# Requirements Phase

Read this reference only while the work item phase is requirements or scope_review.

## Ground

Inspect the live repository, its guidance, manifests, CI, tests, relevant code, and accepted DevWeave baseline. Prefer concrete evidence over generic questions. For an existing repository, propose language-neutral verification commands from commands the repository already documents or runs.

## Produce

1. Complete brief.md in Traditional Chinese with problem, current evidence, scope, non-goals, and risk.
2. Apply the selected entry profile from profiles.md.
3. Complete requirements.md with unique REQ/NFR and AC headings. Make every requirement observable and trace it to at least one acceptance criterion.
4. Record risk and scope through the Python CLI. Configure missing project verification commands through the command subcommand.
5. For bug work, record failing reproduction evidence. For refactor work, record baseline evidence.

Run validate with gate scope. Resolve every error; surface waivers separately and never infer one.

## G1

Present a concise Traditional Chinese summary of the problem, scope, non-goals, acceptance criteria, risk, assumptions, and waivers. Record G1 only after explicit human approval or an explicit $devweave approve request.

Complete when scope validation passes and G1 is recorded against the current brief, requirements, risk, and scope fingerprint. Stop at the gate if approval is absent.

# Verification and Acceptance Phase

Read this reference only while the work item phase is verification or acceptance_review.

## Verify

1. Inspect the full diff against the work item's base source.
2. Run every command required by the current risk profile through the CLI verify command.
3. Add profile evidence: acceptance for new; acceptance plus regression for feature; equivalence plus regression for refactor; regression for bug. Add review evidence for high risk.
4. Cover every AC with current passing evidence bound to the present source fingerprint.
5. Run `knowledge status --work <id>`. Review `affected_pages`, `covered_changed_paths`, `uncovered_changed_paths`, bootstrap recommendation, and review currentness. Refresh or delete each affected page before G3; unrelated stale pages remain warnings.
6. For every new-format work item, record `knowledge review --work <id> --disposition promote|no-update --rationale <text>`. This Knowledge Review is mandatory even when the Wiki remains unchanged. A later product-source fingerprint change invalidates both the review and knowledge plan; rerun the review after implementation stabilizes. Legacy work without the marker is not retrospectively blocked.
7. Choose `no-update` only for non-bootstrap work with no affected page and no Wiki diff, and record a concrete non-empty rationale. Do not create a knowledge plan. Uncovered changed paths may remain only when the review concludes they contain no durable reusable knowledge.
8. Choose `promote` when the work produced durable reusable knowledge. Call `knowledge plan` once with the complete set of one to five content upserts/deletes. Existing affected pages must be refreshed or deleted; durable uncovered changes may be covered by one or more new pages and do not require one page per file.
9. For a planned new upsert, call `knowledge scaffold` with its canonical type, title, and one to five sources. Dependency pages also require package name/version; decision pages require date/status. Scaffold never overwrites and creates a `placeholder` page. Replace every template token, set the page active, update only planned content pages plus coupled index/log, append exactly one `promote` heading containing the work ID without rewriting existing log body, then seal all upserts plus index/log. Seal rejects placeholder pages, template tokens, invalid sources, and critical lint.
10. A bootstrap profile must change no product source and promote three to five content pages: `wiki/overview.md`, at least one architecture page, at least one module page, plus at most two evidence-backed high-value topics. Every completed page must be active, sourced, current, sealed, indexed, and logged. `no-update` and deletes are invalid for bootstrap.
11. Update accepted living truth under .devweave/baseline, or record why no baseline update is needed. Declare every changed baseline path through `baseline --target`; undeclared changes and declared-but-unchanged targets block G3. `new` work must make and declare an architecture baseline update.
12. Complete acceptance.md in Traditional Chinese with the AC/TASK/EVID matrix, Knowledge Review disposition/rationale, Wiki promotion and warnings, baseline changes, waivers, residual risks, and conclusion.

Run validate with gate acceptance. A changed product-source fingerprint makes post-implementation evidence, Knowledge Review, and plan stale; rerun affected checks. A later Wiki-only change leaves product evidence current but invalidates G3 through its separate knowledge fingerprint. Critical Wiki lint, undeclared/unchanged knowledge targets, more than five content targets, missing index/log coupling, stale affected pages, placeholder/template content, and log rewrites block G3. Out-of-scope product changes require removal, scope revision, or an explicit waiver.

## G3

Present the behavior delivered, verification commands, manual evidence, baseline changes, waivers, and residual risks in Traditional Chinese. Record G3 only after explicit human approval or an explicit $devweave approve request. Then run close immediately.

When acceptance is rejected, record revise from requirements, design, or implementation according to the reason and continue from that phase.

Complete when G3 is current, close succeeds, and the work item remains in place with status closed.

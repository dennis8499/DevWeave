# Design Phase

Read this reference only while the work item phase is design or build_review.

## Design

1. Re-read the approved brief and requirements plus the relevant live code.
2. Treat Wiki as read-only input throughout G2. Keep new decisions in `design.md`; do not promote them into persistent Wiki pages yet.
3. Complete design.md in Traditional Chinese, using `codebase-design` vocabulary for the module, interface, seam, adapter, depth, locality, and test surface where relevant.
4. Compare viable options. For each material design choice, ask one question at a time with a recommendation and trade-off, wait for the answer, and record DEC headings that trace to REQ or NFR IDs.
5. Specify interfaces, data flow, state changes, compatibility, failure modes, rollback, and observability.
6. For high risk, explicitly decide the applicable migration, rollback, security, compatibility, and performance treatment.

## Plan

1. Complete plan.md with immutable TASK headings only after the material design decisions are answered.
2. Trace every task to REQ/NFR, AC, and DEC IDs.
3. Give every task a focused output, dependencies, and targeted verification.
4. Plan living-baseline updates and the full verification set.
5. For a `knowledge_profile: bootstrap` work item, select three to five evidence-backed content pages in the immutable plan: `wiki/overview.md`, at least one architecture page, at least one module page, and at most two additional high-value topics. Plan no product-source modification; Wiki remains read-only until verification.

Run validate with gate build. Reconcile design or requirements when implementation uncertainty exposes a planning defect.

## G2

Present a Traditional Chinese summary of the answered design decisions, chosen and rejected options, interfaces, data flow, failure modes, rollback, compatibility, observability, task order, verification strategy, and residual risk. Run `validate --gate build` before the summary. Record G2 only after explicit human approval or an explicit `$devweave approve` request; silence, ambiguous agreement, or Codex's own recommendation is not approval.

Complete when build validation passes, G2 is recorded, and the CLI has created a pending machine task ledger that exactly matches plan.md. Stop before product-code or tracked-test changes when approval is absent or a material design question remains unanswered. If the user changes an approved design decision, use `revise`, regenerate affected design/plan artifacts, and obtain G2 approval again.

# Design Phase

Read this reference only while the work item phase is design or build_review.

## Design

1. Re-read the approved brief and requirements plus the relevant live code.
2. Treat Wiki as read-only input throughout G2. Keep new decisions in `design.md`; do not promote them into persistent Wiki pages yet.
3. Complete design.md in Traditional Chinese.
4. Compare viable options. Record DEC headings that trace to REQ or NFR IDs.
5. Specify interfaces, data flow, state changes, compatibility, failure modes, rollback, and observability.
6. For high risk, explicitly decide the applicable migration, rollback, security, compatibility, and performance treatment.

## Plan

1. Complete plan.md with immutable TASK headings.
2. Trace every task to REQ/NFR, AC, and DEC IDs.
3. Give every task a focused output, dependencies, and targeted verification.
4. Plan living-baseline updates and the full verification set.
5. For a `knowledge_profile: bootstrap` work item, select three to five evidence-backed content pages in the immutable plan: `wiki/overview.md`, at least one architecture page, at least one module page, and at most two additional high-value topics. Plan no product-source modification; Wiki remains read-only until verification.

Run validate with gate build. Reconcile design or requirements when implementation uncertainty exposes a planning defect.

## G2

Present a Traditional Chinese summary of the chosen design, rejected options, interfaces, task order, verification strategy, rollback, and residual risk. Record G2 only after explicit human approval or an explicit $devweave approve request.

Complete when build validation passes, G2 is recorded, and the CLI has created a pending machine task ledger that exactly matches plan.md. Stop before product-code changes when approval is absent.

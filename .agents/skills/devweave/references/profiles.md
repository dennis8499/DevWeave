# Entry Profiles and Risk

Read this reference when starting a work item or reassessing risk.

## Shared rule

Use one state machine for every profile. Change the required discovery and evidence, not the three human gates.

## Profiles

### new

- Discover users, outcomes, constraints, architecture boundaries, roadmap, and the first vertical slice.
- Keep the first work item bounded to one end-to-end usable slice.
- Require current acceptance evidence for that slice before G3.
- Update `.devweave/baseline/architecture.md` with the accepted initial architecture before G3.

### feature

- Ground the request in current behavior and code.
- Map affected interfaces, data, users, compatibility, and explicit non-goals.
- Require current acceptance and regression evidence before G3.

### knowledge bootstrap modifier

- Keep `kind: feature` and add `knowledge_profile: bootstrap`; do not create another lifecycle or work kind.
- Explore the whole repository and prohibit product-source changes.
- In G2 select three to five core/high-value content pages; in G3 require promote, complete overview plus architecture plus module, and reject no-update or deletion.
- A missing or incomplete bootstrap is advisory for ordinary `new`/`feature` work; recommend `$devweave wiki bootstrap` without hard-blocking the ordinary work lifecycle.

### refactor

- Freeze observable behavior and relevant performance or quality baselines before G1.
- Identify the safe seam, test gaps, and reversible increments.
- Require current equivalence and regression evidence before G3.

### bug

- Capture expected and actual behavior, deterministic reproduction steps, and root-cause evidence.
- Require observed failing reproduction evidence before G1. Use an unreproducible waiver only after exhausting safe diagnostics.
- Require a regression result that is green on the fixed source before G3.

## Risk

- low: isolated, reversible, compatible, well-tested, and free of security, migration, or public-contract impact. Record a downgrade rationale.
- standard: the default for normal product work.
- high: authentication, security, privacy, destructive data change, public contracts, multi-service behavior, weak test baselines, or difficult rollback.

High risk keeps the same gates and adds a high-risk design analysis plus current independent review evidence. Record every risk override in machine state. Any movement to a lower risk rank records a separate downgrade rationale.

Complete profile selection when the kind, first verifiable outcome, risk level, rationale, and approved scope paths are explicit.

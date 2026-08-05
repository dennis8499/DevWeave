---
name: tdd
description: Run test-first development through public seams using red → minimal green vertical slices. Use when the user wants to build a feature or fix a bug test-first, mentions "red-green-refactor", or requests integration tests.
---

# Test-Driven Development

Use this method only for a current G2-approved implementation task. TDD is the red → green loop, and this skill is the reference that makes each loop produce a test worth keeping: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle — consult them before and during the loop, not after.

If implementation reveals a material requirement, design, scope, or task decision, stop the ordinary task loop and follow the shared native question contract at `../devweave/references/native-question-contract.md` through Plan Mode, then use `$devweave revise` before further mutation. TDD does not create a question state or a second router.

When exploring the codebase, use the current DevWeave Wiki and approved artifacts for interface vocabulary and precedence. Read an existing `CONTEXT.md` and relevant ADRs when they exist; create or update no parallel context or decision document.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification — "user can checkout with valid cart" tells you exactly what capability exists — and survives refactors because it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams — where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Use the seams recorded in the current approved `design.md` and task artifact. If no seam is approved, pause implementation and use `devweave revise` to return the decision to G2; do not invent an ad hoc seam. Testing effort then lands on critical paths and complex logic instead of every edge case.

## Anti-patterns

- **Implementation-coupled** — mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological** — the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth — a known-good literal, a worked example, the spec.
- **Horizontal slicing** — writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead — one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It is a separate review step in the current work item; use `codebase-design` if architecture or seam changes are needed.

## Completion criterion

The implementation is TDD-complete when every vertical slice has an observed red result, an independent oracle at an approved public seam, a minimal green implementation, and targeted evidence. Refactoring is recorded separately after the loop in the current work item review.

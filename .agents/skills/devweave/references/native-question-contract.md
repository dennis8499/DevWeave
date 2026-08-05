# Native Question Contract

This reference defines the shared interaction seam for DevWeave and its governed
project-local Skills. It does not add engine state, a CLI command, a JSON ledger, or
a second router.

## Host interface

The canonical host tool name is `request_user_input`. The host owns the dialog and
the `Other` freeform entry; the repository owns the decision content and lifecycle
rules. Skills must not invent a camelCase alias, a fake adapter, or a private
question UI.

The router sends one question per call:

```text
QuestionRequest {
  questions: [
    {
      header: string,
      id: string,
      question: string,
      options: [
        { label: string, description: string },
        { label: string, description: string }
      ]
    }
  ]
}
```

The request contract is:

- `questions` contains exactly one item.
- `options` contains two or three mutually exclusive choices.
- The first option is the recommendation and its label contains `(Recommended)`.
- Every option explains its meaningful trade-off or consequence.
- The host-provided `Other` entry remains available for a custom answer.
- The router waits for the result before asking another question, changing an
  artifact, starting implementation, or invoking a Gate action.

## Initial mutation preflight

The initial preflight is an ordering contract owned by the single DevWeave Router. Before any Work Item can be created or modified, it applies to `$devweave new`, `$devweave feature`, `$devweave refactor`, `$devweave bug`, `$devweave wiki bootstrap`, and `revise` when the requested target returns the work to G1 or G2. The preflight must happen before `start`, `bind`, the mutating `revise`, or a bootstrap create/resume path.

The Router treats only actual visibility of the canonical host tool `request_user_input` as evidence that the current host can provide native Plan Mode interaction. A policy statement, Skill invocation, Extension UI, or repository setting is not evidence. When the tool is visible, the Router continues with the existing work-item lifecycle and Gate contracts.

When the tool is not visible in an ordinary context, the Router tells the user to switch to Plan Mode and stops before the mutation boundary. It must not resolve a mutable Work Item, bind a session, invoke `start`/`revise`, or create a bootstrap Work Item as part of that stopped path. The uninitialized `init` startup exception remains allowed, but `start` still requires this preflight.

If the host cannot switch modes, or the user explicitly chooses compatibility, the Router may present the same decision as a structured numbered fallback. The user must explicitly select compatibility before that fallback is used; the fallback itself still follows the one-question contract below. No answer, cancellation, timeout, malformed result, empty answer, or ambiguity permits mutation or Gate progress. Read-only `status`/`next` inspection may explain the stop.

## Plan-first routing

- Before current G2, use Plan Mode for the initial mutation preflight, G1/G2
  material requirements and design decisions, and Gate choices whenever the host
  exposes the native tool.
- If an ordinary-mode Skill needs a material decision before G2 and the native tool
  is not visible, stop and ask the user to return to Plan Mode.
- If the host cannot switch modes or the user explicitly chooses compatibility
  fallback, render the same question as one structured numbered fallback with the
  same option order, recommendation, descriptions, and explicit custom-answer
  entry. Never replace it with an unbounded prose question.
- After current G2, ordinary mode may execute only approved implementation tasks.
  A newly discovered material requirement, design, scope, or task decision stops the
  task and uses `$devweave revise` from the earliest affected phase.

## Result and safety rules

Normalize a host result to the current question `id` and one of `selectedOption`,
`customText`, `cancelled`, `timeout`, or `malformed`. An invalid, empty, cancelled,
or ambiguous result is not an answer: keep the decision/Gate pending, report the
blocker, and do not guess.

Gate answers are intents only. A valid approve/revise choice still passes through
the existing validation and CLI `approve`/`revise` contract. Native UI never bypasses
fingerprints, explicit human approval, G2 write protection, or Knowledge Review.

Facts discoverable from Wiki, source, tests, or approved artifacts are resolved by
the router and are not converted into user questions. This contract applies only to
material decisions and choices that genuinely require user input.

## Capability boundary

Tool visibility is a host capability, not repository state. Plan Mode native support
is the current guaranteed path. Ordinary-mode and Skill-context support may be added
by the host later and must be verified by host integration/manual evidence. Policy
text, a Skill invocation, or the VS Code Extension cannot register the host tool.

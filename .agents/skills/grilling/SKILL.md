---
name: grilling
description: Stress-test a plan, decision, or idea one question at a time. Use when the user wants to examine trade-offs, resolve dependencies, or reach shared understanding.
---

# Grilling

Use this skill to turn an idea or plan into an explicit decision tree.

## Procedure

1. Inspect the repository, Wiki, and approved artifacts for facts; resolve discoverable facts yourself.
2. Identify the next material decision and its dependencies.
3. Follow the shared native question contract at `../devweave/references/native-question-contract.md`. Before current G2, use Plan Mode and `request_user_input` when visible. Ask exactly one question with two or three mutually exclusive options; put the recommended option first and mark it `(Recommended)`, explain the evidence and trade-off, and allow the host's `Other` freeform answer. If an ordinary-mode context cannot see the tool, request Plan Mode; use a structured numbered fallback only when the mode switch is unavailable or compatibility is explicit.
4. Wait for the answer, record it in the current artifact, and re-evaluate dependent branches.
5. Keep execution paused until the user explicitly confirms shared understanding.

## Completion criterion

The session ends only when every material decision has an answer or an explicit blocker, the answers are returned to the current artifact, and the user confirms shared understanding.

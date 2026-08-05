---
name: grill-me
description: Interview the user one decision at a time to sharpen a plan or design.
disable-model-invocation: true
---

Start a `$grilling` session for the current plan or design. Follow the shared native question contract at `../devweave/references/native-question-contract.md` for every material user choice.

Keep the session user-invoked: before current G2, use Plan Mode and the host's `request_user_input` when visible; ask one material decision at a time, give a recommended answer and trade-off, and wait for the response before the next question. If the native tool is not visible, request Plan Mode first; use the structured fallback only when the mode switch is unavailable or the user explicitly chooses compatibility. Return confirmed decisions to the current DevWeave artifact; keep execution paused until the user explicitly confirms shared understanding.

Completion criterion: the user has confirmed shared understanding, or an explicit unresolved blocker is recorded.

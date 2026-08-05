---
name: grill-me
description: Interview the user one decision at a time to sharpen a plan or design.
disable-model-invocation: true
---

Start a `$grilling` session for the current plan or design.

Keep the session user-invoked: ask one material decision at a time, give a recommended answer and trade-off, and wait for the response before the next question. Return the confirmed decisions to the current DevWeave artifact; keep execution paused until the user explicitly confirms shared understanding.

Completion criterion: the user has confirmed shared understanding, or an explicit unresolved blocker is recorded.

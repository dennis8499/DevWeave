---
name: openspec-apply-change
description: Apply an OpenSpec change by implementing its pending tasks. Use when the user asks to begin or continue implementation or work through a change's tasks.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Implement every pending task in one selected OpenSpec change, continuing until the change is complete or genuinely blocked.

When the request names a store, or the change is omitted or ambiguous, read the relevant [planning-target](../_shared/openspec-contracts.md#planning-target) and [change-selection](../_shared/openspec-contracts.md#change-selection) contracts before running OpenSpec commands.

## Steps

1. **Resolve the change**

   Follow the shared selection contract. If selection requires a list, run `openspec list --json` and ask the user to choose. Announce `Using change: <name>` and the override form `$openspec-apply-change <other>`.

   **Complete when:** one eligible change and its local or store planning target are unambiguous.

2. **Load operation state**

   Run:

   ```bash
   openspec status --change "<name>" --json
   openspec instructions apply --change "<name>" --json
   ```

   Preserve the selected store flag. Use status to identify the schema and planning scope; use apply instructions for `state`, progress, tasks, `contextFiles`, the dynamic `instruction`, and optional prompt inputs. Read the shared [status and path](../_shared/openspec-contracts.md#status-and-paths) and [instruction-input](../_shared/openspec-contracts.md#instruction-inputs) contracts while interpreting them.

   Route on `state`:

   - `blocked`: report the missing artifacts and stop. Suggest `openspec-continue-change`; when that skill is unavailable, point to `openspec status --change "<name>" --json` and `openspec instructions <artifact-id> --change "<name>" --json`.
   - `all_done`: report completion, suggest `$openspec-archive-change`, and stop.
   - Any ready state: continue.

   **Complete when:** the schema, planning scope, CLI state, current progress, and every applicable prompt input are accounted for, or a terminal state has been reported.

3. **Ground the implementation**

   Read every concrete path under `contextFiles`, regardless of schema or familiar artifact names. Apply relevant `context` and compatible `operationGuidance`; report conflicts with controlling workflow inputs. Show the schema, `N/M tasks complete`, a pending-task overview, and the CLI's dynamic instruction.

   **Complete when:** every listed context file has been read from disk and the implementation constraints for every pending task are understood.

4. **Implement the task loop**

   For each pending task in order:

   - Announce the task.
   - Make the smallest focused code change that satisfies its artifacts and instruction.
   - Run the relevant project verification.
   - After the task is satisfied and verification passes, immediately change its checkbox from `- [ ]` to `- [x]`.
   - Continue to the next pending task.

   Pause with a precise explanation when the task is unclear, verification fails, implementation exposes a design issue, an external blocker appears, or the user interrupts. For a design issue, recommend reconciling the artifacts before implementation resumes. CLI state and task evidence remain authoritative; prompt inputs alone never prove completion.

   **Complete when:** every satisfied task is checked only after verification, and either no pending task remains or one explicit blocker prevents further progress.

5. **Report the outcome**

   Show tasks completed in this invocation and overall progress. When all tasks are complete, recommend archive. When paused, name the blocker and the decision or external change needed to resume.

   **Complete when:** the report matches the task file and distinguishes completed, pending, and blocked work.

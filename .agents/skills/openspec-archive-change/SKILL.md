---
name: openspec-archive-change
description: Archive an implemented OpenSpec change. Use when the user wants to finalize a change, optionally sync its delta specs, and move it into the archive.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Finalize one active change, guard any incomplete work, optionally synchronize its specs, then move the intact change directory into the store-aware archive.

When the request names a store, or the change is omitted or ambiguous, read the relevant [planning-target](../_shared/openspec-contracts.md#planning-target) and [change-selection](../_shared/openspec-contracts.md#change-selection) contracts.

## Steps

1. **Resolve the change and archive inputs**

   Follow the shared selection contract using active, unarchived changes only; include each schema when prompting. Announce `Using change: <name>` and `$openspec-archive-change <other>`.

   With the selected-root flags, attempt:

   ```bash
   openspec instructions archive --change "<name>" --json
   ```

   This lookup is optional and advisory. A non-zero exit or invalid JSON means continue silently without archive context or guidance. For a valid response, apply the shared [instruction-input contract](../_shared/openspec-contracts.md#instruction-inputs).

   **Complete when:** one active change and planning target are fixed, and valid optional archive inputs have been considered or their unavailable lookup has been safely ignored.

2. **Guard incomplete work**

   Run:

   ```bash
   openspec status --change "<name>" --json
   ```

   Read the shared [status and path contract](../_shared/openspec-contracts.md#status-and-paths). Capture schema, planning paths, action context, artifact paths, and all artifact statuses.

   Warn about every artifact whose status is neither `done` nor `skipped`, list it, and obtain explicit confirmation before continuing. Then read the schema-reported task file when one exists (typically `tasks.md`), count `- [ ]` and `- [x]`, and separately obtain confirmation when incomplete tasks remain. Absence of a task file needs no warning.

   **Complete when:** every artifact and task is accounted for and each incomplete-work warning category has explicit permission to proceed.

3. **Resolve spec synchronization**

   Use only `artifactPaths.specs.existingOutputPaths` as delta specs. A missing entry or empty list means proceed without a sync prompt.

   When deltas exist, compare every delta with `<planningHome.root>/openspec/specs/<capability>/spec.md`, determine pending additions, modifications, removals, and renames, then show one combined summary.

   Offer exactly:
   - Pending changes: `Sync now (recommended)` or `Archive without syncing`.
   - Already synchronized: `Archive now`, `Sync anyway`, or `Cancel`.

   `Cancel` stops. A skip/archive choice proceeds without sync. Any unrecognized answer is prompted again.

   For a sync choice, first run once with the selected-root flags:

   ```bash
   openspec instructions specs --change "<name>" --json
   ```

   Require a zero exit and valid artifact-instruction JSON before any main-spec write. On failure, report the error and stop before writing a main spec or moving the change. Read the shared [instruction-input contract](../_shared/openspec-contracts.md#instruction-inputs), then invoke the complete [`openspec-sync-specs` workflow](../openspec-sync-specs/SKILL.md) inline with the exact delta list, comparison, and rules snapshot. Reuse that snapshot, wait for the sync to finish, and keep `changeRoot` in place throughout.

   Recompare every CLI-reported delta after sync. Verify additions and new names are present, modifications are applied with unrelated scenarios intact, removals and old names are absent, and a second merge would make no edit. A failed or mismatched sync stops archive with `changeRoot` untouched.

   **Complete when:** there are no deltas, the user explicitly skips sync, or every delta has passed post-sync verification.

4. **Move the change atomically**

   Ensure `<planningHome.changesDir>/archive` exists. Use the change name unchanged when it already begins with `YYYY-MM-DD-`; otherwise create `YYYY-MM-DD-<change-name>` using the current date.

   Fail before moving when the target exists and suggest renaming that archive or using a different date. Otherwise move the entire `changeRoot`, including `.openspec.yaml`, to the target.

   ```bash
   mkdir -p "<planningHome.changesDir>/archive"
   mv "<changeRoot>" "<planningHome.changesDir>/archive/<target-name>"
   ```

   **Complete when:** the full source directory exists at the unique archive target and no longer exists at its active path.

5. **Report the archive**

   Show change name, schema, archive location, sync outcome (`verified`, `skipped`, or `no delta specs`), and any incomplete artifact or task warnings accepted by the user.

   **Complete when:** the summary matches the archived directory and all confirmations and sync results.

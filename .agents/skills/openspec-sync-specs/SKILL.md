---
name: openspec-sync-specs
description: Sync an OpenSpec change's delta specs into main specs without archiving it. Use for a direct sync or when archive needs an inline intelligent merge.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Merge selected delta specs into store-aware main specs while preserving content outside each delta's intent. The operation is agent-driven and idempotent; the change remains active.

When the request names a store, or the change is omitted or ambiguous, read the relevant [planning-target](../_shared/openspec-contracts.md#planning-target) and [change-selection](../_shared/openspec-contracts.md#change-selection) contracts.

## Steps

1. **Resolve the change and paths**

   Follow the shared selection contract. When prompting, show only changes with delta-spec outputs. Announce `Using change: <name>` and `$openspec-sync-specs <other>`.

   Run:

   ```bash
   openspec status --change "<name>" --json
   ```

   Preserve the selected store flag. Read the shared [status and path contract](../_shared/openspec-contracts.md#status-and-paths). Use `planningHome.root` for all main-spec paths.

   **Complete when:** one change, its planning root, and its `artifactPaths.specs` entry are resolved from CLI state.

2. **Freeze the delta selection**

   Use `artifactPaths.specs.existingOutputPaths` as the only delta source. When the entry is missing or empty, report that there is nothing to sync and stop before requesting instructions or writing.

   Default to every listed path. If the caller supplies an explicit subset, preserve exactly that subset through the merge:
   - An empty subset means there is nothing to sync; stop.
   - A named path absent from `existingOutputPaths` is an error; report it and stop.
   - Paths outside the subset remain untouched.

   **Complete when:** the selected delta paths are an exact, non-empty subset of the CLI-reported concrete paths.

3. **Obtain one rules snapshot**

   Before the first main-spec write, reuse a valid specs-instruction snapshot supplied by archive. Otherwise run once:

   ```bash
   openspec instructions specs --change "<name>" --json
   ```

   Preserve the selected store flag and read the shared [instruction-input contract](../_shared/openspec-contracts.md#instruction-inputs). A non-zero exit or invalid artifact-instruction JSON is fatal: report it and stop before any main-spec write. A valid response without `rules` is the no-rules case.

   **Complete when:** one valid, current snapshot is available and its artifact rules have been isolated from operation flow.

4. **Merge every selected delta**

   Before merging, read the complete [spec merge and format reference](FORMATS.md). For each selected path:
   - Read the delta spec.
   - Read `<planningHome.root>/openspec/specs/<capability>/spec.md` when it exists.
   - Apply ADDED, MODIFIED, REMOVED, and RENAMED intent using the snapshot's rules.
   - Create a missing main spec in the reference format.
   - Preserve every main-spec passage the delta does not target.
   - Show the capability and intended edits as the merge proceeds.

   After writing, compare every selected delta with its resulting main spec. The result must contain each requested addition, modification, and rename; omit each requested removal and old renamed heading; preserve unmentioned content; and contain no delta operation headers. A second comparison must identify no further edit.

   **Complete when:** every selected delta is fully represented in its main spec and the selected merge is idempotent.

5. **Report the merge**

   Summarize each capability and its added, modified, removed, or renamed requirements. Identify new specs and any `TBD` Purpose. State that main specs are updated and the change remains active.

   **Complete when:** the summary matches the verified files and names every placeholder requiring follow-up.

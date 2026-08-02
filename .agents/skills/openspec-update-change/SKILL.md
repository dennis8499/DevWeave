---
name: openspec-update-change
description: Update an OpenSpec change by revising existing planning artifacts. Use when the user changes a decision, asks for a coherence review, or wants artifacts reconciled after an edit.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Revise only existing planning artifacts and restore coherence across the selected change. Application code stays unchanged.

When the request names a store, or the change is omitted or ambiguous, read the relevant [planning-target](../_shared/openspec-contracts.md#planning-target) and [change-selection](../_shared/openspec-contracts.md#change-selection) contracts.

## Steps

1. **Resolve the change**

   Follow the shared selection contract. When prompting, show the 3–4 most recently modified eligible changes with name, schema (default `spec-driven` when absent), task status, and relative modification time. Mark the most recent `(Recommended)`.

   Announce `Using change: <name>` and `$openspec-update-change <other>`.

   **Complete when:** one existing change and its planning target are unambiguous.

2. **Map existing artifacts**

   Run:

   ```bash
   openspec status --change "<name>" --json
   ```

   Read the shared [status and path contract](../_shared/openspec-contracts.md#status-and-paths). Use schema-reported artifact ids and `artifactPaths.<id>.existingOutputPaths`; custom schemas must work without hardcoded artifact names. Treat glob `resolvedOutputPath` values as patterns rather than files.

   **Complete when:** every existing concrete artifact file and every absent schema artifact are accounted for.

3. **Build a coherent revision set**

   For a specific requested revision, start from the artifact it affects. For a general update, review all existing artifacts for contradictions, gaps, and duplicated decisions. Read the touched files and every other existing artifact, then trace consequences in every direction; build order does not restrict which existing file may need revision.

   Propose edits only to files already present in `existingOutputPaths`. Record missing artifacts or new glob outputs as deferred work rather than creating them. If the requested change replaces the change's intent instead of refining it, recommend `$openspec-new-change` and stop.

   When all existing artifacts already agree, report that result and leave files unchanged.

   **Complete when:** every existing artifact has been checked against the requested decision and each necessary edit or deferral is listed with a reason.

4. **Confirm and apply one artifact at a time**

   Present one artifact's proposed revision and rationale, then wait for user confirmation. Preserve rejected artifacts unchanged. Before a substantial accepted rewrite, run:

   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```

   Apply the shared [instruction-input contract](../_shared/openspec-contracts.md#instruction-inputs), write the accepted revision to its concrete existing path, and re-read it before presenting the next artifact. Keep every write inside planning artifacts; implementation implications are handed to `$openspec-apply-change`.

   **Complete when:** every proposed revision is explicitly accepted or rejected, every accepted edit exists at its original concrete path, and the resulting existing artifacts are coherent.

5. **Report state and next action**

   List revised and rejected artifacts plus deferred missing artifacts or files. Recommend:

   - Missing artifacts: `$openspec-continue-change`.
   - Revised planning after implementation began: `$openspec-apply-change`.
   - Complete, implemented change: `$openspec-archive-change`.

   If `$openspec-continue-change` is unavailable, use status to identify the next artifact and `openspec instructions <artifact-id> --change "<name>" --json` to explain its creation. If `$openspec-new-change` is unavailable, use `openspec new change "<new-name>"`.

   **Complete when:** the report distinguishes applied, rejected, and deferred work and points to one appropriate next action.

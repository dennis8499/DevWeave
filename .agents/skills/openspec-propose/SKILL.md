---
name: openspec-propose
description: Propose a complete OpenSpec change from a requested feature or fix. Use when the user wants planning artifacts generated and ready for implementation in one pass.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Create a new change and every artifact its schema transitively requires for implementation.

When the request names a store, read the shared [planning-target contract](../_shared/openspec-contracts.md#planning-target) before running OpenSpec commands.

## Steps

1. **Establish the change**

   Require either a kebab-case change name or a clear description of what to build or fix. With no clear intent, ask open-endedly what the user wants to build and wait. Derive a concise kebab-case name from a description.

   If that name already exists, ask whether to continue it or create a differently named change before writing.

   **Complete when:** the intended outcome and one available change name are explicit.

2. **Create and map the change**

   For a new name, run:

   ```bash
   openspec new change "<name>"
   ```

   If the user chose to continue an existing change, keep its scaffold intact. Then run for either branch:

   ```bash
   openspec status --change "<name>" --json
   ```

   Preserve the selected store flag. Read the shared [status and path contract](../_shared/openspec-contracts.md#status-and-paths). From status, capture `applyRequires`, the complete artifact list, every `requires` edge, schema, planning paths, and action context.

   Compute the required set as `applyRequires` plus every transitive dependency reachable through `requires`. A `done` artifact still contributes its dependency edges because status reflects file existence, not closure.

   **Complete when:** the change exists and every artifact in the transitive required set is identified.

3. **Build the required set**

   Track the required set in a todo list. Repeatedly choose a missing artifact whose non-skipped dependencies are satisfied, then:
   1. Run `openspec instructions <artifact-id> --change "<name>" --json`.
   2. Read the shared [instruction-input contract](../_shared/openspec-contracts.md#instruction-inputs).
   3. Re-read every returned dependency file from disk.
   4. If `instruction` delegates creation, invoke that skill or command and wait for it.
   5. Otherwise apply `context` and `rules`, fill the `template`, and write to `resolvedOutputPath`; when it is a glob, follow `instruction` to choose a concrete path.
   6. Verify every expected concrete file exists, show `Created <artifact-id>`, and rerun status before choosing the next artifact.

   Treat a status of `skipped` as satisfied and keep its files absent. When an instruction response itself returns `skipped` or a skip warning, keep the output absent, rerun status, and choose another artifact. Deliberately skip another artifact only when its own instruction explicitly makes it conditional. In the spec-driven schema, `design` may qualify; `specs` qualifies only through status `skipped`, never through agent judgment. Announce a deliberate conditional skip once. A required artifact blocked only by that skip may still be created because dependencies enable creation rather than veto it.

   When an artifact needs product input that cannot be derived, ask the user, then resume this same loop.

   **Complete when:** every artifact in the required set is `done`, status `skipped`, or explicitly conditional and deliberately skipped, and every expected output marked `done` exists on disk.

4. **Verify readiness**

   Run `openspec status --change "<name>"` and summarize the change location, artifacts created, conditional skips with reasons, and implementation readiness. End with `$openspec-apply-change` as the implementation action.

   **Complete when:** final status agrees with the verified required set and the user can identify what was created, skipped, and ready.

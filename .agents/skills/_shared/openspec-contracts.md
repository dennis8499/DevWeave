# OpenSpec Workflow Contracts

Shared reference for the OpenSpec skills. Read only the sections named by a skill's context pointer.

## Planning target

When the user names a store, or the work lives in a registered standalone OpenSpec repository, run:

```bash
openspec store list --json
```

Resolve the store id, then add `--store <id>` to commands that read or write specs and changes: `new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, and `view`. Other commands do not accept the flag. Preserve the flag in command hints and follow-up commands.

Without a store, commands target the nearest local `openspec/` root.

## Change selection

Resolve one change before running a change-specific command:

1. Use a change explicitly named by the user.
2. Otherwise use an unambiguous change from the conversation.
3. Otherwise auto-select the only eligible active change.
4. Otherwise run `openspec list --json`, apply the invoking skill's eligibility and presentation rules, and ask the user to choose.

After resolution, announce `Using change: <name>` and show the invoking skill's override form. Selection is complete only when one eligible change and its planning target are unambiguous.

## Status and paths

Treat CLI JSON as the source of truth for schema, state, paths, and scope:

- `planningHome.root` is the store-aware planning root; `planningHome.changesDir` is its changes directory.
- `changeRoot` is the selected change directory.
- `actionContext` carries current scope and edit constraints.
- `artifactPaths.<id>.existingOutputPaths` contains concrete, existing files. A glob-shaped `resolvedOutputPath` is a pattern, not a writable file.
- `contextFiles` contains the exact files an operation requires; read every listed path rather than assuming artifact names.

`status` reports file existence. When dependency closure matters, follow every artifact's `requires` edges even when that artifact already reports `done`.

## Instruction inputs

Interpret fields from `openspec instructions ... --json` consistently:

- `instruction` is the schema's authoritative artifact or operation direction, including delegation to another skill or command.
- `context`, when present, is required prompt-level project input. Apply relevant facts, conventions, and constraints.
- `rules` constrain only the content and form of the artifact being written.
- `template` defines the artifact's output structure.
- `operationGuidance` is optional additive advice; consider every entry and follow applicable entries.

Keep these prompt inputs separate from explicit user choices, built-in workflow steps, resolved paths, CLI state, command contracts, and completion evidence. When `context` or `operationGuidance` conflicts with a controlling input, preserve the controlling input, report the conflict, and explain why the guidance was not followed. Artifact rules cannot redirect paths or change operation flow.

Use these fields as constraints, not prose: never copy `context`, `rules`, `operationGuidance`, or wrapper blocks such as `<context>`, `<rules>`, and `<project_context>` verbatim into artifacts, implementation files, or summaries unless the user separately requests that text.

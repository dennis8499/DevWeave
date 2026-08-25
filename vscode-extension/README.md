# DevWeave Control Center 2.0.0

DevWeave Control Center embeds a governed Codex app-server session in VS Code. It displays authoritative run state beside projected thread/turn events and keeps consequential workflow decisions behind explicit host controls.

## Prerequisites and certification

- Windows x64 and VS Code are the only 2.0.0 certified platform boundary.
- VS Code 1.90+, Python 3.11+, Git, and a locally installed Codex CLI are required.
- Set `devweave.codexPath` to an absolute executable or leave it empty for `PATH` resolution.
- Set `devweave.pythonPath` only when the private repository-local host bridge needs a non-default Python launcher.

Missing or incompatible Codex is a hard preflight blocker. The Extension never downloads Codex and has no clipboard fallback. Other operating systems remain unverified even when portable unit tests pass.

## Workflow surface

Open `DevWeave: Open Control Center` or the DevWeave Activity Bar view. The host offers six commands: open, start, resume, steer, interrupt, and cancel. The Control Center covers connection/preflight, run/thread/turn, plan/diff, approval, pending decision, Gates, verification, review, usage, and bounded diagnostics.

The Extension owns host-only start/resume, decision resolution, Gate decisions, and cancellation through an authenticated private bridge. Codex receives exactly the eight allowlisted project MCP tools. A projection is always labelled separately from current authoritative state; agent or reviewer output never counts as human approval.

## Security and privacy

- App-server and host processes use bounded JSONL transports with `shell:false` and hidden Windows child windows.
- Planning is read-only; implementation and review use repository-scoped workspace-write with network denied.
- Tool requests outside the current phase/task/scope or destructive Git policy are declined before mutation.
- The Webview has a strict CSP and no direct filesystem, network, shell, clipboard, MCP, or host-bridge channel.
- Raw prompts, reasoning, credentials, and estimated usage/cost are not persisted or rendered.

## Development

```text
npm run typecheck
npm test
npm run build
```

`npm run package` performs a production build, writes a unique ignored candidate under `.release/`, verifies the exact entry allowlist plus byte hashes and Git provenance, and only then promotes `devweave-control-center-2.0.0.vsix`. A failed build, verification, or promotion does not replace the current artifact.

`npm run test:smoke:current` uses the explicitly cached VS Code 1.131.0 runtime and never downloads a substitute. `npm run evidence:ui` creates bounded, redacted UI evidence with run/commit/Codex/protocol provenance; screenshots and VSIX files remain ignored release artifacts.

See the repository [documentation map](../docs/index.md), [security model](../docs/security.md), and [quality contract](../docs/quality.md) for the authoritative product boundary.

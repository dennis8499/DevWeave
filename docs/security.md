<!-- canonical-topic: security -->
# Security model

## Trust boundaries

| Boundary | Trusted responsibility | Untrusted input |
| --- | --- | --- |
| Webview → extension | Exact `UiIntent` parser | DOM messages and user text |
| Extension → app-server | Stable method allowlist and correlated JSONL | Events, responses, approval requests |
| Codex → MCP | Eight exact schemas and agent facade | Tool names, payloads, paths, revisions |
| Extension → host bridge | Stdin challenge/HMAC and five-method allowlist | Frames, session IDs, parameters |
| Engine → repository/process | Scope, Git, executable, verification, and effect checks | Paths, symlinks, argv, output, filesystem changes |

## Authorization

Agent identity never grants host identity. MCP cannot discover or forward start/resume, decision resolution, Gate decisions, or cancel. App-server command/file requests are assessed against current phase, task declarations, read-only command policy, and destructive Git policy; the user explicitly accepts, declines, or cancels eligible requests. The host reasserts `approvalPolicy: untrusted` and `approvalsReviewer: user` on thread start/resume/reconnect and every turn so a broader machine-level auto-review preference cannot bypass this client-owned decision point.

## Sandbox and process policy

Planning is read-only. Implementation/review use workspace-write limited to the repository and network disabled. Process transports set `shell:false`, hide Windows child windows, bound individual frames and aggregate output, and never concatenate a command string. Codex is resolved locally and never downloaded; its same-distribution code-mode host is also resolved and hash-attested locally, never silently substituted with an isolated executable.

## Path and Git policy

Every workflow path is normalized repository-relative and checked again after physical resolution. Before any run branch or start journal can be created, repository-aware plan validation rejects reparse components, repository escape, and aliases—including NTFS 8.3 short names—whose canonical repository-relative prefix reaches protected authority. Writable task declarations fail closed when their lexical or physical subtree equals, enters, or contains `.git`, `.devweave`, `.codex`, the DevWeave host skill, or `docs/exec-plans`; the shared physical resolver governs both sandbox roots and file approvals. Traversal, absolute paths, symlink/junction escape, undeclared scope, dirty start, detached HEAD, branch collision, and destructive/remote Git commands fail before mutation.

## Secrets and privacy

The host token exists only in process memory and the initial stdin exchange, then is cleared. Diagnostics/logs redact credential-like patterns and truncate with an explicit marker. Raw reasoning, complete prompts, private review reasoning, secrets, and estimated token/cost data are never stored or rendered. Screenshot evidence records a basename, byte count, SHA-256, and run/commit/protocol provenance.

## CSP and Webview

The Webview loads only extension-local CSS and a nonce-bound script under `default-src 'none'`. It has no direct network, filesystem, shell, clipboard, MCP, or host-bridge channel. HTML and attributes are escaped before rendering.

<!-- canonical-topic: reliability -->
# Reliability and recovery

## Atomic state

Canonical JSON uses sorted keys and a trailing newline. Plan writes use a same-directory temporary file, flush/fsync, atomic replacement, and recovery rules that never treat a partial candidate as current. Mutations require both the expected revision and a bounded mutation ID; replaying an accepted mutation finishes any pending Git checkpoint without repeating the transition or creating a second commit.

## Restart behavior

The reducer reconstructs the RunSnapshot from the ExecPlan and ordered events. If app-server conversation continuity is unavailable, the host opens a new thread with current plan/context instead of inventing state. Thread IDs, event cursors, locks, and bounded logs live under ignored runtime storage.

## Verification execution

- Executables resolve at runtime from approved portable candidates; Codex additionally requires and hashes the platform-specific code-mode host beside the selected executable before any process or network session starts.
- Processes receive argv tokens with `shell=False`, a repository-bounded cwd, timeout, bounded stdout/stderr, and denied network by default.
- Child environments contain only the fixed operating-system baseline plus variables named by that command's `env_allowlist`; an unlisted parent variable cannot influence execution.
- Dependency closure and stage ordering are deterministic.
- Commands declaring writes run serially; undeclared effects invalidate evidence.
- Evidence binds the source snapshot, plan digest, definition digest, resolved executable hash, result, and reconciliation.
- Usage remains null when app-server does not provide it.

## Git recovery

Every run records its immutable base ref and run branch. Each decided Gate, completed task slice, and completed-plan archive is committed together with the authoritative post-transition ExecPlan. The plan records a deterministic local `refs/devweave/checkpoints/...` name; a retry-safe journal binds that ref to the exact commit only after the commit contains matching canonical bytes. Before inspect, resume, or mutation exposes authority state, one interprocess authority lock reconciles every intent across commit, ref, journal, and archive-move interruption points. Recovery follows the first-parent run history after HEAD advances, verifies the journaled tree slice, deterministic ref, canonical plan bytes and digest, finalizes every durable journal or fails closed, and atomically restores a missing active/completed plan from the latest valid checkpoint. DevWeave does not move the base, merge, push, reset, or restore another branch.

## Release recovery

The cutover finalizer is manifest- and hash-bound, rehearsed in a disposable clone, and fail-closed on any path/hash drift. Its release-only projector accepts only the authorized, closed V1 transition with current passing verification, exactly one current isolated review, and all three approved Gates; apply then requires that strict completed ExecPlan to be hash-bound as a retained record. Packaging builds a candidate artifact, verifies provenance/content, then promotes it; failed verification leaves the last current release intact. Binary artifacts and runtime evidence stay untracked.

## Bounded operation

JSONL frames, aggregate output, diagnostics, logs, findings, events, screenshots, retries, parallelism, timeouts, and review rounds all have explicit caps. Unknown protocol notifications become bounded diagnostics; malformed protocol or aggregate overflow fails the session.

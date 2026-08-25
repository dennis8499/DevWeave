<!-- canonical-topic: reliability -->
# Reliability and recovery

## Atomic state

Canonical JSON uses sorted keys and a trailing newline. Plan writes use a same-directory temporary file, flush/fsync, atomic replacement, and recovery rules that never treat a partial candidate as current. Mutations require both the expected revision and a bounded mutation ID; replaying an accepted mutation does not repeat external work.

## Restart behavior

The reducer reconstructs the RunSnapshot from the ExecPlan and ordered events. If app-server conversation continuity is unavailable, the host opens a new thread with current plan/context instead of inventing state. Thread IDs, event cursors, locks, and bounded logs live under ignored runtime storage.

## Verification execution

- Executables resolve at runtime from approved portable candidates.
- Processes receive argv tokens with `shell=False`, a repository-bounded cwd, timeout, bounded stdout/stderr, and denied network by default.
- Dependency closure and stage ordering are deterministic.
- Commands declaring writes run serially; undeclared effects invalidate evidence.
- Evidence binds the source snapshot, plan digest, definition digest, resolved executable hash, result, and reconciliation.
- Usage remains null when app-server does not provide it.

## Git recovery

Every run records its immutable base ref and run branch. Scoped phase commits are recovery checkpoints. On interruption, inspect rather than reset: compare HEAD, current plan revision, task state, verification report, and export index. DevWeave does not move the base, merge, push, or restore another branch.

## Release recovery

The cutover finalizer is manifest- and hash-bound, rehearsed in a disposable clone, and fail-closed on any path/hash drift. Packaging builds a candidate artifact, verifies provenance/content, then promotes it; failed verification leaves the last current release intact. Binary artifacts and runtime evidence stay untracked.

## Bounded operation

JSONL frames, aggregate output, diagnostics, logs, findings, events, screenshots, retries, parallelism, timeouts, and review rounds all have explicit caps. Unknown protocol notifications become bounded diagnostics; malformed protocol or aggregate overflow fails the session.

"""Resolve and validate deterministic Git checkpoint proof."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .canonical import dumps
from .errors import DevWeaveError, ErrorCode
from .git_port import GitPort, path_matches
from .run_state import validate_exec_plan


class CheckpointProof:
    def __init__(self, git: GitPort) -> None:
        self.git = git

    def existing_commit(self, journal: dict[str, Any]) -> str | None:
        checkpoint_ref = journal.get("checkpoint_ref")
        before_head = journal.get("before_head")
        if not isinstance(checkpoint_ref, str) or not isinstance(before_head, str):
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint journal lacks Git identity.")
        ref_present = self.git.ref_exists(checkpoint_ref)
        if ref_present:
            candidate = self.git.resolve_ref(checkpoint_ref)
        else:
            if journal.get("status") in {"committed", "finalized"}:
                raise DevWeaveError(ErrorCode.CONFLICT, "Committed checkpoint lost its deterministic ref.")
            head = self.git.head()
            if head == before_head:
                return None
            if not self.git.is_ancestor(before_head, head):
                raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint starting HEAD is not in run history.")
            candidate = head
            for _ in range(2048):
                parent = self.git.parent(candidate)
                if parent == before_head:
                    break
                candidate = parent
            else:
                raise DevWeaveError(ErrorCode.BOUND_EXCEEDED, "Checkpoint history traversal exceeded its bound.")
        if (
            self.git.parent(candidate) != before_head
            or self.git.commit_message(candidate) != journal.get("message")
            or not self.git.is_ancestor(candidate, self.git.head())
        ):
            if journal.get("status") == "intent" and not ref_present:
                return None
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint commit identity does not match its intent.")
        allowed = journal.get("allowed_paths")
        if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) for item in allowed):
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint journal lacks its allowed tree slice.")
        changed = self.git.diff_paths(before_head, candidate)
        if not changed or any(not path_matches(path, allowed) for path in changed):
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint commit escapes its journaled tree slice.")
        return candidate

    def snapshot(
        self, journal: dict[str, Any], commit_sha: str | None = None
    ) -> tuple[dict[str, Any], str, str]:
        commit = commit_sha or self.existing_commit(journal)
        if commit is None:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint intent has no commit.")
        run_id = journal.get("run_id")
        paths = (
            f"docs/exec-plans/active/{run_id}.json",
            f"docs/exec-plans/completed/{run_id}.json",
        )
        tree_paths = set(self.git.list_tree(commit, "docs/exec-plans"))
        found = [path for path in paths if path in tree_paths]
        if len(found) != 1:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint must contain exactly one canonical ExecPlan.")
        control_path = found[0]
        raw = self.git.read_tree_file(commit, control_path)
        try:
            snapshot = validate_exec_plan(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError, DevWeaveError) as exc:
            raise DevWeaveError(ErrorCode.INVALID_JSON, "Checkpoint ExecPlan is invalid.") from exc
        if raw != dumps(snapshot).encode("utf-8"):
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint ExecPlan is not canonical.")
        self._assert_binding(snapshot, journal, control_path)
        return snapshot, control_path, hashlib.sha256(raw).hexdigest()

    def validate_committed(self, journal: dict[str, Any]) -> None:
        commit_sha = journal.get("commit_sha")
        checkpoint_ref = journal.get("checkpoint_ref")
        if (
            not isinstance(commit_sha, str)
            or not isinstance(checkpoint_ref, str)
            or not self.git.ref_exists(checkpoint_ref)
        ):
            raise DevWeaveError(ErrorCode.CONFLICT, "Committed checkpoint ref is unavailable.")
        if self.git.resolve_ref(checkpoint_ref) != commit_sha:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint ref no longer matches its journal.")
        _, control_path, digest = self.snapshot(journal, commit_sha)
        if journal.get("control_path") != control_path or journal.get("plan_digest") != digest:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint journal no longer matches its canonical plan.")

    @staticmethod
    def _assert_binding(snapshot: dict[str, Any], journal: dict[str, Any], control_path: str) -> None:
        identity = ("run_id", "run_branch", "base_branch", "base_ref")
        if any(snapshot[field] != journal.get(field) for field in identity):
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint ExecPlan identity differs from its journal.")
        expected_revision = journal.get("expected_revision")
        if (
            not isinstance(expected_revision, int)
            or snapshot["revision"] != expected_revision + 1
            or journal.get("mutation_id") not in snapshot["applied_mutations"]
        ):
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint ExecPlan does not bind the intended mutation.")
        expected_path = (
            f"docs/exec-plans/completed/{snapshot['run_id']}.json"
            if snapshot["status"] == "completed"
            else f"docs/exec-plans/active/{snapshot['run_id']}.json"
        )
        if control_path != expected_path:
            raise DevWeaveError(ErrorCode.CONFLICT, "Checkpoint ExecPlan is stored at the wrong lifecycle path.")
        ref = journal.get("checkpoint_ref")
        if journal.get("kind") == "task":
            task = snapshot["tasks"].get(journal.get("subject_id"))
            if task is None or task["status"] != "completed" or task["commit_ref"] != ref:
                raise DevWeaveError(ErrorCode.CONFLICT, "Task checkpoint does not bind its completed task.")
            return
        gate = snapshot["gates"].get(journal.get("subject_id"))
        bound = snapshot["status"] == "completed" and snapshot["archive_ref"] == ref
        bound = bound or (gate is not None and gate["status"] != "pending" and gate["commit_ref"] == ref)
        if not bound:
            raise DevWeaveError(ErrorCode.CONFLICT, "Gate checkpoint does not bind its decision or archive.")

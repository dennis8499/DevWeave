"""Run-owned branch creation and scoped local commit policy."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .contract_utils import identifier, relative_path, text
from .errors import DevWeaveError, ErrorCode
from .git_port import GitPort, branch_name, path_matches


class GitTransaction:
    def __init__(self, repository: Path, git: GitPort) -> None:
        self.repository = repository.resolve()
        self.git = git

    def preflight(self, *, run_id: str, slug: str) -> dict[str, str]:
        if self.git.root() != self.repository:
            raise DevWeaveError(ErrorCode.CONFLICT, "Git root does not match the configured repository.")
        base_branch = self.git.branch()
        base_ref = self.git.head()
        dirty = self.git.status()
        if dirty:
            raise DevWeaveError(
                ErrorCode.BLOCKED,
                "Run start requires a clean tracked, staged, and untracked tree.",
                {"paths": sorted({item.path for item in dirty})[:128]},
            )
        run_branch = branch_name(identifier(run_id, "run_id"), slug)
        if self.git.branch_exists(run_branch):
            raise DevWeaveError(ErrorCode.CONFLICT, "Run branch already exists.", {"branch": run_branch})
        return {"base_branch": base_branch, "base_ref": base_ref, "run_branch": run_branch}

    def start_branch(self, *, run_id: str, slug: str) -> dict[str, str]:
        result = self.preflight(run_id=run_id, slug=slug)
        self.start_preflighted(result)
        return result

    def start_preflighted(self, result: dict[str, str]) -> None:
        self.git.switch_new_branch(result["run_branch"])
        if self.git.head() != result["base_ref"]:
            raise DevWeaveError(ErrorCode.CONFLICT, "Run branch did not start at the recorded base ref.")

    def assert_run(self, *, run_branch: str, base_branch: str, base_ref: str) -> None:
        if self.git.root() != self.repository or self.git.branch() != run_branch:
            raise DevWeaveError(ErrorCode.CONFLICT, "Current checkout is not owned by this run.")
        self.assert_base_ref(base_branch=base_branch, base_ref=base_ref)
        if not self.git.is_ancestor(base_ref, self.git.head()):
            raise DevWeaveError(ErrorCode.CONFLICT, "Run HEAD is not descended from its immutable base ref.")

    def assert_base_ref(self, *, base_branch: str, base_ref: str) -> None:
        current = self.git.resolve_ref(base_branch)
        if current != base_ref:
            raise DevWeaveError(
                ErrorCode.CONFLICT,
                "Base branch ref moved during the run.",
                {"base_branch": base_branch, "expected": base_ref, "actual": current},
            )

    def commit_slice(
        self,
        *,
        run_id: str,
        task_id: str,
        run_branch: str,
        base_branch: str,
        base_ref: str,
        declared_paths: Sequence[str],
        ignored_paths: Sequence[str] = (),
    ) -> str:
        identifier(run_id, "run_id")
        identifier(task_id, "task_id")
        message = text(f"devweave({run_id}): complete {task_id}", "commit_message", maximum=256)
        return self._commit_scoped(
            run_branch=run_branch,
            base_branch=base_branch,
            base_ref=base_ref,
            allowed_paths=declared_paths,
            ignored_paths=ignored_paths,
            message=message,
        )

    def commit_checkpoint(
        self,
        *,
        run_id: str,
        run_branch: str,
        base_branch: str,
        base_ref: str,
        allowed_paths: Sequence[str],
        message: str,
    ) -> str:
        identifier(run_id, "run_id")
        return self._commit_scoped(
            run_branch=run_branch,
            base_branch=base_branch,
            base_ref=base_ref,
            allowed_paths=allowed_paths,
            ignored_paths=(),
            message=text(message, "commit_message", maximum=256),
        )

    def _commit_scoped(
        self,
        *,
        run_branch: str,
        base_branch: str,
        base_ref: str,
        allowed_paths: Sequence[str],
        ignored_paths: Sequence[str],
        message: str,
    ) -> str:
        if self.git.branch() != run_branch:
            raise DevWeaveError(ErrorCode.CONFLICT, "Current branch is not owned by this run.")
        self.assert_base_ref(base_branch=base_branch, base_ref=base_ref)
        declarations = tuple(relative_path(item, f"allowed_paths[{index}]") for index, item in enumerate(allowed_paths))
        ignored = tuple(relative_path(item, f"ignored_paths[{index}]") for index, item in enumerate(ignored_paths))
        entries = tuple(
            item for item in self.git.status()
            if not path_matches(item.path, ignored) and (not item.original_path or not path_matches(item.original_path, ignored))
        )
        if not entries:
            raise DevWeaveError(ErrorCode.CONFLICT, "No slice changes are available to commit.")
        changed = sorted({path for item in entries for path in (item.path, item.original_path) if path})
        conflicts = [item.path for item in entries if "U" in item.code or item.code in {"AA", "DD"}]
        if conflicts:
            raise DevWeaveError(ErrorCode.BLOCKED, "Git conflicts block a scoped commit.", {"paths": conflicts})
        unrelated = [path for path in changed if not path_matches(path, declarations)]
        if unrelated:
            raise DevWeaveError(
                ErrorCode.BLOCKED,
                "Unrelated working-tree changes block a scoped commit.",
                {"paths": unrelated[:128]},
            )
        for path in changed:
            candidate = self.repository / path
            if candidate.exists():
                try:
                    candidate.resolve().relative_to(self.repository)
                except ValueError as exc:
                    raise DevWeaveError(ErrorCode.PATH_OUTSIDE_REPOSITORY, "Changed path escapes through a symlink.", {"path": path}) from exc
        self.git.stage(changed)
        staged = self.git.staged_paths()
        unexpected_staged = [path for path in staged if not path_matches(path, declarations)]
        if unexpected_staged or set(staged) != set(changed):
            raise DevWeaveError(
                ErrorCode.BLOCKED,
                "Staged paths differ from the declared slice.",
                {"staged": list(staged), "changed": changed, "unexpected": unexpected_staged},
            )
        commit_ref = self.git.commit(message)
        self.assert_base_ref(base_branch=base_branch, base_ref=base_ref)
        return commit_ref

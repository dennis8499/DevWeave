"""Composition root for V2 adapters."""

from __future__ import annotations

import json
from pathlib import Path

from .git_port import GitAdapter
from .git_transaction import GitTransaction
from .project_config import ProjectConfig
from .run_git_coordinator import RunGitCoordinator
from .run_service import RunService
from .verification_engine import VerificationEngine


def build_run_service(repository: Path) -> RunService:
    root = repository.resolve()
    project_path = root / ".devweave" / "project.json"
    engine = None
    if project_path.is_file():
        raw = json.loads(project_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError("DevWeave project configuration must be an object.")
        if raw.get("schema_version") == 2:
            engine = VerificationEngine(root, ProjectConfig.from_dict(raw))
    coordinator = None
    if (root / ".git").exists():
        coordinator = RunGitCoordinator(root, GitTransaction(root, GitAdapter(root)))
    elif engine is not None:
        raise RuntimeError("Schema-v2 workflow mutations require a Git repository.")
    return RunService(root, verification_engine=engine, git_coordinator=coordinator)


def load_project_config(repository: Path) -> ProjectConfig:
    path = repository.resolve() / ".devweave" / "project.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProjectConfig.from_dict(raw)

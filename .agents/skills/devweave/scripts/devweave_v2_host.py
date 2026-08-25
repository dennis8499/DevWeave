"""Private Extension-host entrypoint; intentionally absent from public CLI."""

from pathlib import Path

from devweave_v2.host_bridge import run_host_stdio

raise SystemExit(run_host_stdio(Path.cwd()))

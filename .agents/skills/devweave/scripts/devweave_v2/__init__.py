"""DevWeave V2 application package.

The package exposes typed contracts and deep application services.  Process
entrypoints are deliberately kept outside the package so an agent-facing MCP
process can never acquire the host facade by importing a shared dispatcher.
"""

from .version import SCHEMA_VERSION, VERSION

__all__ = ["SCHEMA_VERSION", "VERSION"]

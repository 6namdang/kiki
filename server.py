"""Horizon / FastMCP deployment entrypoint.

Use this file (not kiki/server.py) as the Horizon entrypoint:
  server.py:mcp

FastMCP loads the file from disk and adds its *parent directory* to sys.path.
A root-level entrypoint ensures `import kiki` resolves to the installed package.
"""

from kiki.server import mcp

__all__ = ["mcp"]

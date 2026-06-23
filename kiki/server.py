from fastmcp import FastMCP

from kiki.config import SERVER_NAME
from kiki.tools import register_all_tools


def create_server() -> FastMCP:
    mcp = FastMCP(SERVER_NAME)
    register_all_tools(mcp)
    return mcp


# Horizon / `fastmcp run` entrypoint (e.g. kiki/server.py:mcp)
mcp = create_server()

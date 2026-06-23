"""Smoke-test client for a running Kiki HTTP MCP server.

Usage:
  Terminal 1: kiki serve --transport http --port 8000
  Terminal 2: python client.py
"""

import asyncio
import json
import sys

from fastmcp import Client

SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main() -> None:
    client = Client(SERVER_URL)

    try:
        async with client:
            tools = await client.list_tools()
            print("Connected to:", SERVER_URL)
            print("Tools:", [tool.name for tool in tools])

            result = await client.call_tool(
                "get_virus_metadata",
                {"query": "NC_045512.2", "is_accession": True},
            )
            print("\nget_virus_metadata result:")
            print(json.dumps(result.data, indent=2))
    except Exception as exc:
        print(f"Failed to connect to {SERVER_URL}", file=sys.stderr)
        print("Make sure the server is running:", file=sys.stderr)
        print("  kiki serve --transport http --port 8000", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())

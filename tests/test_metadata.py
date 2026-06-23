import asyncio

import pytest
from fastmcp import Client

from kiki.server import create_server


@pytest.mark.asyncio
async def test_metadata_tool_in_process() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools}
        assert "get_virus_metadata" in tool_names
        assert "retrieve_virus_dataset" in tool_names

        result = await client.call_tool(
            "get_virus_metadata",
            {"query": "NC_045512.2", "is_accession": True},
        )
        assert result.data["success"] is True
        assert result.data["returned"] >= 1
        assert result.data["total_available"] >= 1
        assert result.data["records"][0]["accession"] == "NC_045512.2"
        assert result.data["audit"]["pagination_complete"] is True

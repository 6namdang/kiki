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
        assert "count_virus_sequences" in tool_names
        assert "retrieve_virus_dataset" in tool_names

        result = await client.call_tool(
            "get_virus_metadata",
            {"query": "NC_045512.2", "is_accession": True},
        )
        data = result.data
        assert data["success"] is True
        assert data["query_id"]
        assert data["result"]["returned"] >= 1
        assert data["result"]["total_available"] >= 1
        assert data["result"]["records"][0]["accession"] == "NC_045512.2"
        assert data["provenance"]["pagination_complete"] is True

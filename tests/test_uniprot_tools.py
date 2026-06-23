import asyncio

import pytest
from fastmcp import Client

from kiki.server import create_server


@pytest.mark.asyncio
async def test_uniprot_tools_registered() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        for expected in (
            "search_proteins",
            "count_proteins",
            "get_protein",
            "retrieve_protein_dataset",
            "map_protein_ids",
        ):
            assert expected in names


@pytest.mark.asyncio
async def test_get_protein_insulin() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool("get_protein", {"accession": "P01308"})
        data = result.data
        assert data["success"] is True
        assert data["result"]["record"]["accession"] == "P01308"
        assert data["result"]["record"]["gene_names"]


@pytest.mark.asyncio
async def test_count_sars_cov2_spike_preset() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "count_proteins",
            {"preset": "sars_cov2_spike"},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["count"] >= 1


@pytest.mark.asyncio
async def test_map_protein_ids_gene_name() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "map_protein_ids",
            {
                "ids": ["P01308"],
                "from_db": "UniProtKB_AC-ID",
                "to_db": "Gene_Name",
            },
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["mapped_count"] >= 1

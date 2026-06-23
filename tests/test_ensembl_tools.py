import asyncio

import pytest
from fastmcp import Client

from kiki.server import create_server


@pytest.mark.asyncio
async def test_ensembl_tools_registered() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        for expected in (
            "get_sequence",
            "retrieve_sequence_batch",
            "search_genes",
            "get_gene_info",
            "get_reference",
        ):
            assert expected in names


@pytest.mark.asyncio
async def test_search_genes_brca1(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_genes",
            {"searchwords": "BRCA1", "species": "homo_sapiens", "limit": 3},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["returned"] >= 1
        assert data["result"]["records"][0]["gene_name"] == "BRCA1"
        assert data["query_id"]


@pytest.mark.asyncio
async def test_get_gene_info_brca1(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        search = await client.call_tool(
            "search_genes",
            {"searchwords": "BRCA1", "species": "homo_sapiens", "limit": 1},
        )
        ensembl_id = search.data["result"]["records"][0]["ensembl_id"]
        result = await client.call_tool(
            "get_gene_info",
            {"ensembl_id": ensembl_id, "ncbi": False, "uniprot": False, "pdb": False},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["returned"] == 1
        record = next(iter(data["result"]["records"].values()))
        assert record["ensembl_gene_name"] == "BRCA1"


@pytest.mark.asyncio
async def test_get_sequence_brca1(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_sequence",
            {"ensembl_id": "ENSG00000012048", "isoforms": False},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["returned"] >= 1
        assert data["result"]["records"][0]["length"] > 0


@pytest.mark.asyncio
async def test_retrieve_sequence_batch_requires_confirm_for_outfolder(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "retrieve_sequence_batch",
            {
                "ensembl_ids": ["ENSG00000012048"],
                "outfolder": str(tmp_path / "out"),
            },
        )
        data = result.data
        assert data["success"] is False
        assert data["error"]["code"] == "CONFIRM_DOWNLOAD_REQUIRED"


@pytest.mark.asyncio
async def test_get_reference_human_gtf(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_reference",
            {"species": "homo_sapiens", "which": "gtf"},
        )
        data = result.data
        assert data["success"] is True
        refs = data["result"]["references"]
        assert "homo_sapiens" in refs
        assert "annotation_gtf" in refs["homo_sapiens"]

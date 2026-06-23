import pytest
from fastmcp import Client

from kiki.server import create_server


@pytest.mark.asyncio
async def test_blast_tools_registered() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        assert "submit_blast_search" in names
        assert "get_blast_results" in names


@pytest.mark.asyncio
async def test_submit_rejects_nt_database(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "submit_blast_search",
            {"program": "blastn", "query": "NC_045512.2", "database": "nt"},
        )
        data = result.data
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_PARAMETER"


@pytest.mark.asyncio
async def test_get_blast_results_rejects_bad_rid(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool("get_blast_results", {"rid": "bad rid!"})
        data = result.data
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_PARAMETER"


@pytest.mark.integration
@pytest.mark.skip(reason="Opt-in live BLAST submit; run with pytest -m integration")
@pytest.mark.asyncio
async def test_submit_blast_search_live(tmp_path, monkeypatch) -> None:
    """Live NCBI BLAST submit — slow; opt-in via -m integration."""
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "submit_blast_search",
            {
                "program": "blastn",
                "query": "NC_045512.2",
                "database": "core_nt",
                "hitlist_size": 5,
            },
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["rid"]
        assert data["result"]["status"] == "submitted"
        assert data["query_id"]

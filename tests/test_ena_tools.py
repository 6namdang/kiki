import pytest
from fastmcp import Client

from kiki.server import create_server
from kiki.services import ena as ena_service


@pytest.mark.asyncio
async def test_ena_tools_registered() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        for expected in (
            "count_ena_records",
            "search_ena_records",
            "get_ena_sequence",
            "retrieve_ena_dataset",
        ):
            assert expected in names


@pytest.mark.asyncio
async def test_search_rejects_broad_query(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_ena_records",
            {"result": "sequence", "query": 'country="United Kingdom"'},
        )
        data = result.data
        assert data["success"] is False
        assert data["error"]["code"] == "QUERY_TOO_BROAD"


@pytest.mark.asyncio
async def test_retrieve_rejects_unknown_result(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "retrieve_ena_dataset",
            {"result": "assembly", "query": "tax_eq(1)"},
        )
        data = result.data
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_PARAMETER"


@pytest.mark.asyncio
async def test_count_ena_records_mocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setattr(ena_service, "portal_count", lambda result, query: 266)
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "count_ena_records",
            {"result": "sequence", "query": "tax_eq(2697049)"},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["count"] == 266
        assert data["query_id"]
        assert data["provenance"]["api_sequence"] == ["portal_count"]


@pytest.mark.asyncio
async def test_retrieve_sequence_dataset_mocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setattr(ena_service, "portal_count", lambda result, query: 1)
    monkeypatch.setattr(
        ena_service,
        "portal_search",
        lambda result, query, fields=None, limit=0: [{"accession": "BN000065"}],
    )
    monkeypatch.setattr(
        ena_service,
        "browser_fasta_batch",
        lambda accessions: {
            "records": [{"header": ">BN000065", "sequence": "ACGT", "length": 4}],
            "requests_made": 1,
        },
    )
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "retrieve_ena_dataset",
            {"result": "sequence", "query": "tax_eq(1)"},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["api_sequence"] == [
            "portal_count",
            "portal_search",
            "browser_fasta",
        ]
        assert data["result"]["pagination_complete"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_ena_sequence_live(tmp_path, monkeypatch) -> None:
    """Live ENA Browser fetch of a small documented accession; opt-in via -m integration."""
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_ena_sequence",
            {"accession": "BN000065"},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["returned"] >= 1

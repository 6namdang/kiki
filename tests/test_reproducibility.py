import asyncio

import pytest
from fastmcp import Client

from kiki.server import create_server
from kiki.services import ena as ena_service


@pytest.mark.asyncio
async def test_count_is_reproducible_three_runs(tmp_path, monkeypatch) -> None:
    """Same params must yield identical query_id and count across repeated calls."""
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))

    mcp = create_server()
    params = {"query": "NC_045512.2", "is_accession": True}

    async with Client(mcp) as client:
        results = []
        for _ in range(3):
            response = await client.call_tool("count_virus_sequences", params)
            data = response.data
            assert data["success"] is True
            results.append(data)

    query_ids = {item["query_id"] for item in results}
    counts = {item["result"]["count"] for item in results}

    assert len(query_ids) == 1, f"query_id varied across runs: {query_ids}"
    assert len(counts) == 1, f"count varied across runs: {counts}"
    assert results[0]["result"]["count"] >= 1


@pytest.mark.asyncio
async def test_ena_count_is_reproducible_three_runs(tmp_path, monkeypatch) -> None:
    """Same ENA params yield identical query_id and count across repeated calls."""
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setattr(ena_service, "portal_count", lambda result, query: 266)

    mcp = create_server()
    params = {"result": "sequence", "query": "tax_eq(2697049)"}

    async with Client(mcp) as client:
        results = []
        for _ in range(3):
            response = await client.call_tool("count_ena_records", params)
            data = response.data
            assert data["success"] is True
            results.append(data)

    query_ids = {item["query_id"] for item in results}
    counts = {item["result"]["count"] for item in results}

    assert len(query_ids) == 1, f"query_id varied across runs: {query_ids}"
    assert len(counts) == 1, f"count varied across runs: {counts}"


@pytest.mark.asyncio
async def test_query_history_records_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))

    mcp = create_server()
    async with Client(mcp) as client:
        count_result = await client.call_tool(
            "count_virus_sequences",
            {"query": "NC_045512.2", "is_accession": True},
        )
        query_id = count_result.data["query_id"]

        history = await client.call_tool(
            "get_query_history",
            {"query_id": query_id},
        )
        data = history.data
        assert data["success"] is True
        assert data["result"]["count"] == 1
        assert data["result"]["entries"][0]["manifest"]["query_id"] == query_id
        assert "filter_application" in data["result"]["entries"][0]["manifest"]["provenance"]

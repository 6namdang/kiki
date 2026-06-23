import asyncio

import pytest
from fastmcp import Client

from kiki.errors import ErrorCode, KikiError
from kiki.query.genome import validate_assembly_accession, validate_nucleotide_accession
from kiki.server import create_server


def test_validate_nucleotide_accession_accepts_refseq() -> None:
    assert validate_nucleotide_accession("NC_045512.2") == "NC_045512.2"


def test_validate_assembly_accession_accepts_gcf() -> None:
    assert validate_assembly_accession("GCF_000001405.40") == "GCF_000001405.40"


def test_validate_nucleotide_accession_rejects_garbage() -> None:
    with pytest.raises(KikiError) as exc:
        validate_nucleotide_accession("not-an-accession")
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


@pytest.mark.asyncio
async def test_genome_tools_registered() -> None:
    mcp = create_server()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        for expected in (
            "get_nucleotide_sequence",
            "get_nucleotide_metadata",
            "get_assembly_metadata",
            "retrieve_nucleotide_batch",
        ):
            assert expected in names


@pytest.mark.asyncio
async def test_get_nucleotide_sequence_sars_cov2(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_nucleotide_sequence",
            {"accession": "NC_045512.2"},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["returned"] == 1
        assert data["result"]["records"][0]["length"] == 29903
        assert data["query_id"]


@pytest.mark.asyncio
async def test_get_nucleotide_metadata_sars_cov2(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_nucleotide_metadata",
            {"accession": "NC_045512.2"},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["record"]["length"] == 29903
        assert "Severe acute respiratory syndrome coronavirus 2" in data["result"]["record"]["title"]


@pytest.mark.asyncio
async def test_get_assembly_metadata_human(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    mcp = create_server()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_assembly_metadata",
            {"accession": "GCF_000001405.40"},
        )
        data = result.data
        assert data["success"] is True
        assert data["result"]["record"]["assembly_name"] == "GRCh38.p14"
        assert data["result"]["record"]["taxid"] == "9606"

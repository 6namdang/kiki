import json

import pytest

from kiki.services import ena as ena_service


class FakeResponse:
    def __init__(self, *, text: str = "", status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def test_portal_count_parses_integer(monkeypatch) -> None:
    monkeypatch.setattr(ena_service, "_ena_get", lambda url, params=None: FakeResponse(text="266"))
    assert ena_service.portal_count("sequence", "tax_eq(2697049)") == 266


def test_portal_search_returns_rows(monkeypatch) -> None:
    rows = [{"accession": "AB000001", "description": "x"}]
    monkeypatch.setattr(
        ena_service, "_ena_get", lambda url, params=None: FakeResponse(text=json.dumps(rows))
    )
    out = ena_service.portal_search("sequence", "tax_eq(1)", limit=10)
    assert out == rows


def test_parse_browser_fasta_multi_record() -> None:
    text = ">A description one\nACGT\nACGT\n>B description two\nTTTT\n"
    records = ena_service._parse_browser_fasta(text)
    assert len(records) == 2
    assert records[0]["header"] == ">A description one"
    assert records[0]["sequence"] == "ACGTACGT"
    assert records[0]["length"] == 8
    assert records[1]["sequence"] == "TTTT"


def test_browser_fasta_batch_chunks_at_10k(monkeypatch) -> None:
    calls: list[str] = []

    def fake_get(url, params=None):
        calls.append(url)
        return FakeResponse(text=">x\nACGT\n")

    monkeypatch.setattr(ena_service, "_ena_get", fake_get)
    monkeypatch.setattr(ena_service, "ENA_BROWSER_BATCH_SIZE", 2)

    out = ena_service.browser_fasta_batch(["a", "b", "c", "d", "e"])
    # 5 accessions in chunks of 2 -> 3 requests.
    assert out["requests_made"] == 3
    assert len(calls) == 3


def test_search_ena_preview_uses_count_for_total(monkeypatch) -> None:
    monkeypatch.setattr(ena_service, "portal_count", lambda result, query: 5000)
    monkeypatch.setattr(
        ena_service,
        "portal_search",
        lambda result, query, fields=None, limit=0: [{"accession": f"A{i}"} for i in range(limit)],
    )
    out = ena_service.search_ena_preview("sequence", "tax_eq(1)", preview_limit=25)
    assert out["total_available"] == 5000
    assert out["returned"] == 25
    assert out["pagination_complete"] is False
    assert out["api_sequence"] == ["portal_count", "portal_search"]


def test_retrieve_ena_sequences_runs_portal_then_browser(monkeypatch) -> None:
    monkeypatch.setattr(ena_service, "portal_count", lambda result, query: 2)
    monkeypatch.setattr(
        ena_service,
        "portal_search",
        lambda result, query, fields=None, limit=0: [
            {"accession": "AB000001"},
            {"accession": "AB000002"},
        ],
    )
    monkeypatch.setattr(
        ena_service,
        "browser_fasta_batch",
        lambda accessions: {
            "records": [{"header": f">{a}", "sequence": "ACGT", "length": 4} for a in accessions],
            "requests_made": 1,
        },
    )
    out = ena_service.retrieve_ena_sequences("tax_eq(1)", fmt="fasta")
    assert out["total_available"] == 2
    assert out["accession_count"] == 2
    assert out["downloaded"] == 2
    assert out["pagination_complete"] is True
    assert out["api_sequence"] == ["portal_count", "portal_search", "browser_fasta"]


def test_retrieve_ena_read_runs_portal_only(monkeypatch) -> None:
    monkeypatch.setattr(ena_service, "portal_count", lambda result, query: 1)
    monkeypatch.setattr(
        ena_service,
        "portal_search",
        lambda result, query, fields=None, limit=0: [
            {"run_accession": "ERR000001", "fastq_ftp": "ftp://x"}
        ],
    )
    out = ena_service.retrieve_ena_read_runs("tax_eq(1)")
    assert out["total_available"] == 1
    assert out["returned"] == 1
    assert out["api_sequence"] == ["portal_count", "portal_search"]

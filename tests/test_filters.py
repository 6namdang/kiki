import pytest

from kiki.errors import ErrorCode, KikiError
from kiki.services.command_summary import parse_command_summary
from kiki.services.filters import metadata_kwargs, validate_query_scope, virus_kwargs


def test_metadata_kwargs_maps_complete_only() -> None:
    kwargs = metadata_kwargs({"host": "Homo sapiens", "complete_only": True, "isolate": "x"})
    assert kwargs == {"host": "Homo sapiens", "complete_only": True}


def test_virus_kwargs_drops_none() -> None:
    kwargs = virus_kwargs({"host": "Homo sapiens", "lineage": None, "min_seq_length": 1000})
    assert kwargs == {"host": "Homo sapiens", "min_seq_length": 1000}


def test_virus_kwargs_maps_complete_only_to_nuc_completeness() -> None:
    kwargs = virus_kwargs({"complete_only": True})
    assert kwargs == {"nuc_completeness": "complete"}


def test_virus_kwargs_maps_refseq_only_to_source_database() -> None:
    kwargs = virus_kwargs({"refseq_only": True})
    assert kwargs == {"source_database": "refseq"}


def test_virus_kwargs_includes_gget_flags() -> None:
    kwargs = virus_kwargs(
        {
            "is_sars_cov2": True,
            "is_alphainfluenza": True,
            "download_all_accessions": True,
            "genbank_batch_size": 100,
            "keep_temp": True,
            "verbose": False,
            "has_proteins": ["spike", "ORF1ab"],
            "segment": "HA",
            "lineage": ["B.1.1.7", "P.1"],
        }
    )
    assert kwargs["is_sars_cov2"] is True
    assert kwargs["download_all_accessions"] is True
    assert kwargs["genbank_batch_size"] == 100
    assert kwargs["has_proteins"] == ["spike", "ORF1ab"]
    assert kwargs["lineage"] == ["B.1.1.7", "P.1"]


def test_download_all_accessions_requires_filters() -> None:
    with pytest.raises(KikiError) as exc:
        validate_query_scope(
            query="",
            is_accession=False,
            filters={"download_all_accessions": True},
            operation="download a dataset",
        )
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD


def test_parse_command_summary_detects_failures(tmp_path) -> None:
    summary = tmp_path / "command_summary.txt"
    summary.write_text(
        "Run complete\n"
        "--------------------------------------------------------------------------------\n"
        "FAILED OPERATIONS - RETRY COMMANDS\n"
        "--------------------------------------------------------------------------------\n"
        "Retry URL: https://example.com/retry\n",
        encoding="utf-8",
    )
    parsed = parse_command_summary(summary)
    assert parsed["detected"] is True
    assert parsed["retry_urls"] == ["https://example.com/retry"]

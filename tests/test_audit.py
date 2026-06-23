import pytest

from kiki.audit.deferred_filters import explain_filter_application
from kiki.audit.history import get_manifest_by_query_id, query_history, record_manifest
from kiki.services.command_summary import parse_command_summary, summarize_command_summary


def test_explain_deferred_host_filter() -> None:
    audit = explain_filter_application(
        requested_filters={"host": "Homo sapiens", "complete_only": True},
        deferred_filters={"host": "Homo sapiens"},
        operation="metadata_paginated",
    )
    assert audit["deferred_raw"]["host"] == "Homo sapiens"
    assert len(audit["deferred_to_local"]) == 1
    assert "locally" in audit["deferred_to_local"][0]["explanation"].lower()
    assert any(item["filter"] == "complete_only" for item in audit["api_applied"])


def test_explain_dataset_local_filters() -> None:
    audit = explain_filter_application(
        requested_filters={
            "min_collection_date": "2014-01-01",
            "max_ambiguous_chars": 1900,
        },
        deferred_filters=None,
        operation="dataset_download",
    )
    assert len(audit["local_only"]) == 2
    assert "locally" in audit["summary"].lower()


def test_summarize_command_summary_without_failures(tmp_path) -> None:
    summary = tmp_path / "command_summary.txt"
    summary.write_text(
        "gget virus run complete\nRecords fetched: 12\nOutput: ebola.fasta\n",
        encoding="utf-8",
    )
    parsed = summarize_command_summary(summary)
    assert parsed["available"] is True
    assert parsed["has_failures"] is False
    assert "Records fetched" in parsed["excerpt"]


def test_parse_command_summary_detects_failures(tmp_path) -> None:
    summary = tmp_path / "command_summary.txt"
    summary.write_text(
        "Run complete\n"
        "--------------------------------------------------------------------------------\n"
        "FAILED OPERATIONS - RETRY COMMANDS\n"
        "Retry URL: https://example.com/retry\n",
        encoding="utf-8",
    )
    parsed = parse_command_summary(summary)
    assert parsed["detected"] is True
    assert parsed["retry_urls"] == ["https://example.com/retry"]


def test_manifest_history_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path))
    manifest = {
        "query_id": "abc123",
        "tool": "count_virus_sequences",
        "success": True,
        "result": {"count": 5},
    }
    record = record_manifest(manifest)
    assert record["recorded"] is True

    entries = query_history(tool="count_virus_sequences", limit=5)
    assert len(entries) == 1
    assert entries[0]["query_id"] == "abc123"

    found = get_manifest_by_query_id("abc123")
    assert found is not None
    assert found["manifest"]["result"]["count"] == 5

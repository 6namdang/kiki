"""Tests for pagination helpers and NCBI E-utilities epost parsing."""

from kiki.services.ncbi_eutils import _parse_epost_response
from kiki.services.pagination import pagination_meta


def test_pagination_meta_complete_when_retrieved_equals_total() -> None:
    meta = pagination_meta(total_available=10, retrieved=10, pages_fetched=1)
    assert meta["pagination_complete"] is True


def test_pagination_meta_incomplete_when_truncated() -> None:
    meta = pagination_meta(total_available=100, retrieved=10, pages_fetched=1)
    assert meta["pagination_complete"] is False


def test_parse_epost_response_xml() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8" ?>
<ePostResult><QueryKey>1</QueryKey><WebEnv>MC0_123</WebEnv></ePostResult>"""
    webenv, query_key = _parse_epost_response(xml)
    assert webenv == "MC0_123"
    assert query_key == "1"


def test_parse_epost_response_regex_fallback() -> None:
    text = "Some wrapper\n<WebEnv>ABC</WebEnv>\n<QueryKey>2</QueryKey>"
    webenv, query_key = _parse_epost_response(text)
    assert webenv == "ABC"
    assert query_key == "2"

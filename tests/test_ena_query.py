import pytest

from kiki.errors import ErrorCode, KikiError
from kiki.query.ena import (
    validate_ena_accession,
    validate_ena_format,
    validate_ena_full_retrieval,
    validate_ena_query,
    validate_ena_result,
    validate_ena_scope,
    validate_preview_limit,
)


def test_validate_ena_result_accepts_v1_types() -> None:
    assert validate_ena_result("sequence") == "sequence"
    assert validate_ena_result("READ_RUN") == "read_run"


def test_validate_ena_result_rejects_unknown() -> None:
    with pytest.raises(KikiError) as exc:
        validate_ena_result("assembly")
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_validate_ena_query_requires_value() -> None:
    with pytest.raises(KikiError) as exc:
        validate_ena_query("   ")
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_validate_ena_accession_accepts_insdc() -> None:
    assert validate_ena_accession("BN000065") == "BN000065"
    assert validate_ena_accession("DQ285577.1") == "DQ285577.1"


def test_validate_ena_accession_rejects_garbage() -> None:
    with pytest.raises(KikiError) as exc:
        validate_ena_accession("not an accession")
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_validate_preview_limit_caps() -> None:
    assert validate_preview_limit(None) == 25
    assert validate_preview_limit(1000) == 100
    with pytest.raises(KikiError) as exc:
        validate_preview_limit(0)
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_validate_ena_format() -> None:
    assert validate_ena_format(None) == "fasta"
    assert validate_ena_format("EMBL") == "embl"
    with pytest.raises(KikiError) as exc:
        validate_ena_format("genbank")
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_validate_ena_scope_allows_taxonomy() -> None:
    validate_ena_scope("sequence", "tax_eq(2697049)", operation="search records")
    validate_ena_scope("read_run", 'tax_tree(11118) AND country="UK"', operation="search records")


def test_validate_ena_scope_rejects_broad_query() -> None:
    with pytest.raises(KikiError) as exc:
        validate_ena_scope("sequence", 'country="United Kingdom"', operation="search records")
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD


def test_validate_ena_full_retrieval_cap() -> None:
    validate_ena_full_retrieval(50, confirm_download=False)
    with pytest.raises(KikiError) as exc:
        validate_ena_full_retrieval(50000, confirm_download=False)
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD
    # Confirmed download bypasses the cap.
    validate_ena_full_retrieval(50000, confirm_download=True)

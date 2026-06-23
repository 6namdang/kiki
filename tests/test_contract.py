import pytest

from kiki.errors import ErrorCode, KikiError
from kiki.query.normalize import compute_query_id, normalize_query_params
from kiki.query.presets import resolve_preset
from kiki.query.validate import validate_filters


def test_query_id_is_stable() -> None:
    params_a = {"query": "186538", "is_accession": False, "host": "Homo sapiens"}
    params_b = {"host": "Homo sapiens", "is_accession": False, "query": "186538"}
    assert compute_query_id(params_a) == compute_query_id(params_b)


def test_normalize_drops_empty_values() -> None:
    normalized = normalize_query_params(
        {"query": "186538", "host": None, "geographic_location": ""}
    )
    assert normalized == {"query": "186538"}


def test_preset_not_found() -> None:
    with pytest.raises(KikiError) as exc:
        resolve_preset("does_not_exist", {})
    assert exc.value.code == ErrorCode.PRESET_NOT_FOUND


def test_preset_merge_explicit_overrides() -> None:
    resolved = resolve_preset(
        "sars_cov2_ref_genome",
        {"query": "NC_045512.2", "host": "Homo sapiens"},
    )
    assert resolved["query"] == "NC_045512.2"
    assert resolved["host"] == "Homo sapiens"


def test_invalid_date_range() -> None:
    with pytest.raises(KikiError) as exc:
        validate_filters(
            {"min_collection_date": "2020-01-01", "max_collection_date": "2019-01-01"}
        )
    assert exc.value.code == ErrorCode.INVALID_DATE_RANGE


def test_invalid_nuc_completeness() -> None:
    with pytest.raises(KikiError) as exc:
        validate_filters({"nuc_completeness": "unknown"})
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_kiki_error_payload() -> None:
    payload = KikiError(
        ErrorCode.QUERY_TOO_BROAD,
        "too broad",
        details={"query": "2697049"},
    ).to_dict()
    assert payload["success"] is False
    assert payload["error"]["code"] == "QUERY_TOO_BROAD"
    assert payload["error"]["details"]["query"] == "2697049"

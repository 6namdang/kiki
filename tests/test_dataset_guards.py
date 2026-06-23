import pytest

from kiki.errors import ErrorCode, KikiError
from kiki.services.filters import validate_query_scope


def test_dataset_requires_confirmation() -> None:
    with pytest.raises(KikiError) as exc:
        from kiki.services.gget_virus import run_virus_dataset

        run_virus_dataset(
            query="123456",
            is_accession=False,
            confirm_download=False,
            filters={"host": "Homo sapiens"},
        )
    assert exc.value.code == ErrorCode.CONFIRM_DOWNLOAD_REQUIRED


def test_large_taxid_requires_filters() -> None:
    with pytest.raises(KikiError) as exc:
        validate_query_scope(
            query="2697049",
            is_accession=False,
            filters={},
            operation="fetch metadata",
        )
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD


def test_large_taxid_allowed_with_filters() -> None:
    validate_query_scope(
        query="2697049",
        is_accession=False,
        filters={"host": "Homo sapiens"},
        operation="download a dataset",
    )


def test_accession_skips_large_taxid_guard() -> None:
    validate_query_scope(
        query="NC_045512.2",
        is_accession=True,
        filters={},
        operation="fetch metadata",
    )

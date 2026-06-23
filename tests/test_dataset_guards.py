import pytest

from kiki.services.gget_virus import validate_dataset_request


def test_dataset_requires_confirmation() -> None:
    with pytest.raises(ValueError, match="confirm_download"):
        validate_dataset_request(
            query="123456",
            is_accession=False,
            confirm_download=False,
            filters={"host": "Homo sapiens"},
        )


def test_large_taxid_requires_filters() -> None:
    with pytest.raises(ValueError, match="filter"):
        validate_dataset_request(
            query="2697049",
            is_accession=False,
            confirm_download=True,
            filters={},
        )


def test_large_taxid_allowed_with_filters() -> None:
    validate_dataset_request(
        query="2697049",
        is_accession=False,
        confirm_download=True,
        filters={"host": "Homo sapiens"},
    )


def test_accession_skips_large_taxid_guard() -> None:
    validate_dataset_request(
        query="NC_045512.2",
        is_accession=True,
        confirm_download=True,
        filters={},
    )

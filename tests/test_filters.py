import pytest

from kiki.services.filters import metadata_kwargs, virus_kwargs


def test_metadata_kwargs_maps_complete_only() -> None:
    kwargs = metadata_kwargs({"host": "Homo sapiens", "complete_only": True, "isolate": "x"})
    assert kwargs == {"host": "Homo sapiens", "complete_only": True}


def test_virus_kwargs_drops_none() -> None:
    kwargs = virus_kwargs({"host": "Homo sapiens", "lineage": None, "min_seq_length": 1000})
    assert kwargs == {"host": "Homo sapiens", "min_seq_length": 1000, "verbose": False}

import pytest

from kiki.errors import ErrorCode, KikiError
from kiki.query.uniprot import build_uniprot_query, validate_uniprot_scope
from kiki.query.uniprot_presets import resolve_uniprot_preset


def test_build_query_adds_reviewed_default() -> None:
    query = build_uniprot_query(gene="INS", organism_id="9606", reviewed_only=True)
    assert "reviewed:true" in query
    assert "gene:INS" in query
    assert "organism_id:9606" in query


def test_build_query_respects_include_unreviewed() -> None:
    query = build_uniprot_query(
        gene="INS",
        organism_id="9606",
        reviewed_only=True,
        include_unreviewed=True,
    )
    assert "reviewed" not in query


def test_preset_merge() -> None:
    resolved = resolve_uniprot_preset("human_insulin", {"gene": "INS"})
    assert resolved["organism_id"] == "9606"
    assert resolved["gene"] == "INS"


def test_human_without_narrowing_blocked() -> None:
    with pytest.raises(KikiError) as exc:
        validate_uniprot_scope(
            query="(organism_id:9606) AND (reviewed:true)",
            filters={"organism_id": "9606", "reviewed_only": True},
            operation="download",
        )
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD


def test_gene_narrowing_allowed() -> None:
    validate_uniprot_scope(
        query="(organism_id:9606) AND (gene:INS) AND (reviewed:true)",
        filters={"organism_id": "9606", "gene": "INS"},
        operation="download",
    )

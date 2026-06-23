import pytest

from kiki.errors import ErrorCode, KikiError
from kiki.query.ensembl import validate_andor, validate_batch_size, validate_id_type, validate_search_limit
from kiki.services.ensembl import parse_fasta_blocks


def test_parse_fasta_blocks() -> None:
    blocks = [
        ">ENSG00000012048 chromosome:GRCh38:17:43044292:43170245:-1",
        "ATCG\nGCTA",
        ">ENST00000357654\nAA\n",
    ]
    records = parse_fasta_blocks(blocks)
    assert len(records) == 2
    assert records[0]["header"].startswith(">ENSG00000012048")
    assert records[0]["sequence"] == "ATCGGCTA"
    assert records[0]["length"] == 8
    assert records[1]["sequence"] == "AA"


def test_resolve_ensembl_release_default() -> None:
    from kiki.config import ENSEMBL_DEFAULT_RELEASE
    from kiki.query.ensembl import resolve_ensembl_release

    assert resolve_ensembl_release(None) == ENSEMBL_DEFAULT_RELEASE
    assert resolve_ensembl_release(115) == 115


def test_validate_batch_size_rejects_large_batches() -> None:
    with pytest.raises(KikiError) as exc:
        validate_batch_size(["ID"] * 51)
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD


def test_validate_search_limit_caps() -> None:
    with pytest.raises(KikiError) as exc:
        validate_search_limit(101)
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_validate_andor() -> None:
    assert validate_andor("OR") == "or"
    with pytest.raises(KikiError):
        validate_andor("xor")


def test_validate_id_type() -> None:
    assert validate_id_type("Gene") == "gene"
    with pytest.raises(KikiError):
        validate_id_type("protein")

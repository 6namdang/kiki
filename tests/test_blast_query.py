import pytest

from kiki.errors import ErrorCode, KikiError
from kiki.query.blast import (
    build_blast_params,
    detect_query_type,
    validate_database,
    validate_hitlist_size,
    validate_program,
    validate_query,
    validate_rid,
)
from kiki.services.ncbi_blast import (
    classify_agent_status,
    parse_blast_hits,
    parse_blast_status,
)


def test_validate_program_accepts_blastn_blastp() -> None:
    assert validate_program("blastn") == "blastn"
    assert validate_program("BLASTP") == "blastp"


def test_validate_program_rejects_unknown() -> None:
    with pytest.raises(KikiError) as exc:
        validate_program("tblastn")
    assert exc.value.code == ErrorCode.INVALID_PARAMETER


def test_validate_database_defaults() -> None:
    assert validate_database("blastn", None) == "core_nt"
    assert validate_database("blastp", None) == "swissprot"


def test_validate_database_rejects_nt_nr() -> None:
    with pytest.raises(KikiError) as exc:
        validate_database("blastn", "nt")
    assert exc.value.code == ErrorCode.INVALID_PARAMETER
    assert "nt" in exc.value.details.get("note", "").lower() or "nt" in str(exc.value.details)


def test_validate_query_accession() -> None:
    text, qtype = validate_query("blastn", "NC_045512.2")
    assert text == "NC_045512.2"
    assert qtype == "accession"


def test_validate_query_fasta_header() -> None:
    fasta = ">seq1\nATCGATCG"
    text, qtype = validate_query("blastn", fasta)
    assert qtype == "fasta"
    assert text == fasta


def test_validate_query_rejects_oversized_fasta() -> None:
    huge = ">s\n" + ("A" * 60_000)
    with pytest.raises(KikiError) as exc:
        validate_query("blastn", huge)
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD


def test_validate_hitlist_size_cap() -> None:
    with pytest.raises(KikiError) as exc:
        validate_hitlist_size(1000)
    assert exc.value.code == ErrorCode.QUERY_TOO_BROAD


def test_validate_rid() -> None:
    assert validate_rid("ABCD1234") == "ABCD1234"


def test_detect_query_type_raw_nucleotide() -> None:
    assert detect_query_type("blastn", "ATCGATCGATCG") == "fasta"


def test_build_blast_params_stable_keys() -> None:
    params = build_blast_params(
        program="blastn",
        query="NC_045512.2",
        query_type="accession",
        database="core_nt",
        expect=None,
        hitlist_size=25,
        word_size=None,
        filter_value=None,
    )
    assert params["program"] == "blastn"
    assert params["hitlist_size"] == 25


def test_parse_blast_status_ready() -> None:
    text = "Status=READY\nThereAreHits=yes\n"
    status, hits = parse_blast_status(text)
    assert status == "READY"
    assert hits is True


def test_classify_agent_status() -> None:
    assert classify_agent_status("WAITING") == "running"
    assert classify_agent_status("READY") == "ready"
    assert classify_agent_status("UNKNOWN") == "failed"


def test_parse_blast_hits_empty() -> None:
    parsed = parse_blast_hits({"BlastOutput2": []})
    assert parsed["num_hits"] == 0
    assert parsed["hits"] == []


def test_parse_blast_hits_sample() -> None:
    payload = {
        "BlastOutput2": [
            {
                "report": {
                    "program": "blastn",
                    "version": "2.16.0+",
                    "search_target": {"db": "core_nt"},
                    "results": {
                        "search": {
                            "stat": {"db_num": 100, "db_len": 200},
                            "hits": [
                                {
                                    "description": [
                                        {
                                            "accession": "NC_045512.2",
                                            "title": "SARS-CoV-2",
                                            "taxid": 2697049,
                                        }
                                    ],
                                    "hsps": [
                                        {
                                            "evalue": 0.0,
                                            "bit_score": 100.0,
                                            "identity": 29903,
                                            "align_len": 29903,
                                            "query_from": 1,
                                            "query_to": 29903,
                                            "hit_from": 1,
                                            "hit_to": 29903,
                                            "query_strand": "Plus",
                                            "hit_strand": "Plus",
                                        }
                                    ],
                                }
                            ],
                        }
                    },
                }
            }
        ]
    }
    parsed = parse_blast_hits(payload)
    assert parsed["num_hits"] == 1
    assert parsed["hits"][0]["accession"] == "NC_045512.2"
    assert parsed["hits"][0]["percent_identity"] == 100.0

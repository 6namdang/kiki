"""Validation for NCBI BLAST URL API tools."""

from __future__ import annotations

import re

from kiki.config import (
    NCBI_BLAST_MAX_FASTA_BYTES,
    NCBI_BLAST_MAX_HITLIST_SIZE,
    NCBI_BLAST_NUCL_DATABASES,
    NCBI_BLAST_PROT_DATABASES,
)
from kiki.errors import ErrorCode, KikiError

BLAST_PROGRAMS = frozenset({"blastn", "blastp"})

# Single-token identifiers NCBI BLAST accepts (accession or GI-style); not inline sequence.
ACCESSION_LIKE_RE = re.compile(r"^[A-Za-z0-9._-]+$")

NUCLEOTIDE_CHARS_RE = re.compile(r"^[ATCGUNatcgun\s\d]+$")
PROTEIN_CHARS_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWYBZXUO*atcdefghiklmnpqrstvwybzxuo*\s\d]+$")

RID_RE = re.compile(r"^[A-Za-z0-9]+$")


def default_database(program: str) -> str:
    if program == "blastn":
        return "core_nt"
    return "swissprot"


def allowed_databases(program: str) -> frozenset[str]:
    if program == "blastn":
        return NCBI_BLAST_NUCL_DATABASES
    return NCBI_BLAST_PROT_DATABASES


def validate_program(program: str) -> str:
    program = program.strip().lower()
    if program not in BLAST_PROGRAMS:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "program must be blastn or blastp.",
            details={"program": program, "allowed": sorted(BLAST_PROGRAMS)},
        )
    return program


def validate_database(program: str, database: str | None) -> str:
    db = (database or default_database(program)).strip().lower()
    allowed = allowed_databases(program)
    if db not in allowed:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            f"database '{db}' is not allowed for {program}.",
            details={
                "database": db,
                "program": program,
                "allowed": sorted(allowed),
                "note": "nt and nr are excluded in v1 to avoid timeouts and partial results.",
            },
        )
    return db


def detect_query_type(program: str, query: str) -> str:
    """Return 'accession' or 'fasta'."""
    stripped = query.strip()
    if not stripped:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "query is required.")

    if stripped.startswith(">"):
        return "fasta"

    if "\n" in stripped:
        return "fasta"

    compact = re.sub(r"\s+", "", stripped)
    if (
        program == "blastn"
        and len(compact) >= 10
        and "_" not in compact
        and "." not in compact
        and NUCLEOTIDE_CHARS_RE.match(compact)
    ):
        return "fasta"
    if (
        program == "blastp"
        and len(compact) >= 10
        and "_" not in compact
        and PROTEIN_CHARS_RE.match(compact)
    ):
        return "fasta"

    if ACCESSION_LIKE_RE.match(stripped) and len(stripped) <= 40:
        return "accession"

    raise KikiError(
        ErrorCode.INVALID_PARAMETER,
        "query must be an NCBI accession or FASTA/sequence text.",
        details={
            "program": program,
            "examples_accession": ["NC_045512.2", "NP_828854.1"],
            "examples_fasta": [">my_seq\nATCG...", "ATCGATCG"],
        },
    )


def validate_query(program: str, query: str) -> tuple[str, str]:
    program = validate_program(program)
    stripped = query.strip()
    query_type = detect_query_type(program, stripped)
    if query_type == "fasta":
        size = len(stripped.encode("utf-8"))
        if size > NCBI_BLAST_MAX_FASTA_BYTES:
            raise KikiError(
                ErrorCode.QUERY_TOO_BROAD,
                f"Inline FASTA exceeds {NCBI_BLAST_MAX_FASTA_BYTES} bytes.",
                details={"bytes": size, "limit": NCBI_BLAST_MAX_FASTA_BYTES},
            )
    return stripped, query_type


def validate_expect(expect: float | None) -> float | None:
    if expect is None:
        return None
    if expect <= 0:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "expect must be greater than zero.",
            details={"expect": expect},
        )
    return expect


def validate_hitlist_size(hitlist_size: int | None) -> int | None:
    if hitlist_size is None:
        return None
    if hitlist_size <= 0:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "hitlist_size must be a positive integer.",
            details={"hitlist_size": hitlist_size},
        )
    if hitlist_size > NCBI_BLAST_MAX_HITLIST_SIZE:
        raise KikiError(
            ErrorCode.QUERY_TOO_BROAD,
            f"hitlist_size {hitlist_size} exceeds limit of {NCBI_BLAST_MAX_HITLIST_SIZE}.",
            details={"hitlist_size": hitlist_size, "limit": NCBI_BLAST_MAX_HITLIST_SIZE},
        )
    return hitlist_size


def validate_rid(rid: str) -> str:
    rid = rid.strip()
    if not rid or not RID_RE.match(rid):
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "rid must be a non-empty alphanumeric Request ID from submit_blast_search.",
            details={"rid": rid},
        )
    return rid


def build_blast_params(
    *,
    program: str,
    query: str,
    query_type: str,
    database: str,
    expect: float | None,
    hitlist_size: int | None,
    word_size: int | None,
    filter_value: str | None,
) -> dict[str, str | float | int]:
    """Normalized parameters stored in QueryManifest / query_id."""
    params: dict[str, str | float | int] = {
        "program": program,
        "query": query,
        "query_type": query_type,
        "database": database,
    }
    if expect is not None:
        params["expect"] = expect
    if hitlist_size is not None:
        params["hitlist_size"] = hitlist_size
    if word_size is not None:
        params["word_size"] = word_size
    if filter_value is not None:
        params["filter"] = filter_value
    return params

"""Validation for NCBI nucleotide and assembly accession tools."""

from __future__ import annotations

import re

from kiki.config import NCBI_MAX_NUCLEOTIDE_BATCH
from kiki.errors import ErrorCode, KikiError

# Common INSDC / RefSeq accession prefixes (nucleotide + assembly).
NUCLEOTIDE_ACCESSION_RE = re.compile(
    r"^(?:NC|NM|NR|NP|NG|NT|NW|NZ|CP|AP|AC|XM|XR|XP|ZP|BK|KF)_\d+(?:\.\d+)?$",
    re.IGNORECASE,
)
ASSEMBLY_ACCESSION_RE = re.compile(r"^GCF_\d+(?:\.\d+)?$|^GCA_\d+(?:\.\d+)?$", re.IGNORECASE)


def normalize_accessions(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        items = [part.strip() for part in value.replace(",", " ").split() if part.strip()]
    else:
        items = [str(item).strip() for item in value if item and str(item).strip()]
    if not items:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "At least one accession is required.")
    return items


def validate_nucleotide_accession(accession: str) -> str:
    accession = accession.strip()
    if not accession:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "accession is required.")
    if not NUCLEOTIDE_ACCESSION_RE.match(accession):
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Invalid nucleotide accession format.",
            details={"accession": accession, "example": "NC_045512.2"},
        )
    return accession


def validate_assembly_accession(accession: str) -> str:
    accession = accession.strip()
    if not accession:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "accession is required.")
    if not ASSEMBLY_ACCESSION_RE.match(accession):
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Invalid assembly accession format (expected GCF_ or GCA_).",
            details={"accession": accession, "example": "GCF_000001405.40"},
        )
    return accession


def validate_nucleotide_batch(accessions: list[str]) -> list[str]:
    validated = [validate_nucleotide_accession(item) for item in accessions]
    if len(validated) > NCBI_MAX_NUCLEOTIDE_BATCH:
        raise KikiError(
            ErrorCode.QUERY_TOO_BROAD,
            f"Batch size {len(validated)} exceeds limit of {NCBI_MAX_NUCLEOTIDE_BATCH}.",
            details={"count": len(validated), "limit": NCBI_MAX_NUCLEOTIDE_BATCH},
        )
    return validated

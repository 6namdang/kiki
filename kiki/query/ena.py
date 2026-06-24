"""Validation for ENA Portal + Browser API tools."""

from __future__ import annotations

import re

from kiki.config import (
    ENA_DEFAULT_PREVIEW_LIMIT,
    ENA_MAX_PREVIEW_LIMIT,
    ENA_MAX_RETRIEVE_COUNT,
    ENA_RESULTS_V1,
)
from kiki.errors import ErrorCode, KikiError

# ENA / INSDC sequence accessions accepted by the Browser API by-accession endpoint.
ENA_ACCESSION_RE = re.compile(r"^[A-Za-z]{1,6}\d{2,}(?:\.\d+)?$")

# Signals that a Portal query is narrowed enough to avoid an unbounded retrieval.
_SCOPE_SIGNALS = (
    re.compile(r"tax_id\s*=", re.IGNORECASE),
    re.compile(r"tax_tree\s*\(", re.IGNORECASE),
    re.compile(r"tax_eq\s*\(", re.IGNORECASE),
    re.compile(r"\b\w*accession\s*=", re.IGNORECASE),
    re.compile(r"\bstudy_accession\b", re.IGNORECASE),
    re.compile(r"\bsample_accession\b", re.IGNORECASE),
    re.compile(r"\brun_accession\b", re.IGNORECASE),
)


def validate_ena_result(result: str) -> str:
    result = result.strip().lower()
    if result not in ENA_RESULTS_V1:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Unsupported ENA result type.",
            details={"result": result, "allowed": sorted(ENA_RESULTS_V1)},
        )
    return result


def validate_ena_query(query: str) -> str:
    query = query.strip()
    if not query:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "query is required.")
    if len(query) > 4000:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "query is too long (max 4000 characters).",
            details={"length": len(query)},
        )
    return query


def validate_ena_accession(accession: str) -> str:
    accession = accession.strip()
    if not accession:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "accession is required.")
    if not ENA_ACCESSION_RE.match(accession):
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Invalid ENA sequence accession format.",
            details={"accession": accession, "example": "BN000065"},
        )
    return accession


def validate_preview_limit(preview_limit: int | None) -> int:
    if preview_limit is None:
        return ENA_DEFAULT_PREVIEW_LIMIT
    if preview_limit <= 0:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "preview_limit must be a positive integer.",
            details={"preview_limit": preview_limit},
        )
    return min(preview_limit, ENA_MAX_PREVIEW_LIMIT)


def validate_ena_format(fmt: str | None) -> str:
    fmt = (fmt or "fasta").strip().lower()
    if fmt not in {"fasta", "embl"}:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "format must be 'fasta' or 'embl'.",
            details={"format": fmt},
        )
    return fmt


def validate_ena_scope(result: str, query: str, *, operation: str) -> None:
    """Reject broad Portal queries that lack any narrowing signal.

    Mirrors the virus/UniProt scope guards: an agent must constrain the query by
    taxonomy or an accession field before a potentially huge retrieval.
    """
    if any(signal.search(query) for signal in _SCOPE_SIGNALS):
        return
    raise KikiError(
        ErrorCode.QUERY_TOO_BROAD,
        f"ENA query is too broad to {operation}. Add a narrowing filter "
        "(e.g. tax_eq(<taxid>), tax_tree(<taxid>), or a study/sample/run accession).",
        details={"result": result, "query": query},
    )


def validate_ena_full_retrieval(count: int, *, confirm_download: bool) -> None:
    """Refuse a limit=0 full retrieval above the cap unless explicitly confirmed."""
    if count > ENA_MAX_RETRIEVE_COUNT and not confirm_download:
        raise KikiError(
            ErrorCode.QUERY_TOO_BROAD,
            f"ENA query matches {count} records (cap {ENA_MAX_RETRIEVE_COUNT}). "
            "Narrow the query or pass confirm_download=true to retrieve the full set.",
            details={"count": count, "limit": ENA_MAX_RETRIEVE_COUNT},
        )

"""Validation helpers for gget Ensembl tools."""

from __future__ import annotations

from kiki.config import ENSEMBL_DEFAULT_RELEASE, ENSEMBL_MAX_BATCH_SIZE, ENSEMBL_MAX_SEARCH_LIMIT
from kiki.errors import ErrorCode, KikiError


def resolve_ensembl_release(release: int | None) -> int:
    """Return pinned Ensembl release (default from config when omitted)."""
    if release is None:
        return ENSEMBL_DEFAULT_RELEASE
    if release < 1:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "release must be a positive Ensembl release number.",
            details={"release": release},
        )
    return release


def validate_batch_size(ensembl_ids: list[str]) -> None:
    if len(ensembl_ids) > ENSEMBL_MAX_BATCH_SIZE:
        raise KikiError(
            ErrorCode.QUERY_TOO_BROAD,
            f"Batch size {len(ensembl_ids)} exceeds limit of {ENSEMBL_MAX_BATCH_SIZE}. "
            "Split into smaller batches.",
            details={"count": len(ensembl_ids), "limit": ENSEMBL_MAX_BATCH_SIZE},
        )


def validate_search_limit(limit: int | None) -> int:
    if limit is None:
        return ENSEMBL_MAX_SEARCH_LIMIT
    if limit < 1:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "limit must be at least 1.")
    if limit > ENSEMBL_MAX_SEARCH_LIMIT:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            f"limit cannot exceed {ENSEMBL_MAX_SEARCH_LIMIT}.",
            details={"limit": limit, "max": ENSEMBL_MAX_SEARCH_LIMIT},
        )
    return limit


def validate_andor(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"or", "and"}:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "andor must be 'or' or 'and'.",
            details={"andor": value},
        )
    return normalized


def validate_id_type(value: str) -> str:
    allowed = {"gene", "transcript", "translation", "cdna"}
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            f"id_type must be one of: {', '.join(sorted(allowed))}.",
            details={"id_type": value},
        )
    return normalized

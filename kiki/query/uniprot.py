"""UniProt query building, validation, and presets."""

from __future__ import annotations

import re
from typing import Any

from kiki.errors import ErrorCode, KikiError

LARGE_ORGANISM_IDS = frozenset({"9606", "10090", "10116", "7227", "6239", "559292"})

NARROWING_KEYS = (
    "gene",
    "protein_name",
    "accession",
    "length_min",
    "length_max",
    "organism_id",
)

NARROWING_QUERY_TOKENS = (
    "gene:",
    "protein_name:",
    "accession:",
    "length:",
    "annotation:",
    "cc_",
    "xref:",
    "organism_name:",
)

REVIEWED_PATTERN = re.compile(r"\(\s*reviewed\s*:\s*(true|false)\s*\)", re.IGNORECASE)


def build_uniprot_query(
    *,
    query: str | None = None,
    reviewed_only: bool = True,
    include_unreviewed: bool = False,
    organism_id: str | None = None,
    gene: str | None = None,
    protein_name: str | None = None,
    accession: str | None = None,
    length_min: int | None = None,
    length_max: int | None = None,
) -> str:
    """Combine structured filters into a UniProt query string."""
    parts: list[str] = []

    if query and query.strip():
        parts.append(f"({query.strip()})")

    if accession:
        parts.append(f"(accession:{accession})")
    if organism_id:
        parts.append(f"(organism_id:{organism_id})")
    if gene:
        parts.append(f"(gene:{gene})")
    if protein_name:
        parts.append(f"(protein_name:{protein_name})")
    if length_min is not None:
        parts.append(f"(length:[{length_min} TO *])")
    if length_max is not None:
        parts.append(f"(length:[* TO {length_max}])")

    if not parts:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Provide query or at least one structured filter (organism_id, gene, protein_name, accession).",
        )

    combined = " AND ".join(parts)
    if include_unreviewed:
        return combined
    if reviewed_only and not REVIEWED_PATTERN.search(combined):
        return f"({combined}) AND (reviewed:true)"
    return combined


def has_narrowing_filter(filters: dict[str, Any], query: str | None = None) -> bool:
    for key in NARROWING_KEYS:
        if key == "organism_id":
            continue
        if filters.get(key) not in (None, "", False):
            return True

    combined = " ".join(
        str(filters.get(key) or "")
        for key in ("query", "gene", "protein_name", "accession")
    )
    if query:
        combined = f"{combined} {query}"
    lowered = combined.lower()
    if any(token in lowered for token in NARROWING_QUERY_TOKENS):
        return True

    # organism_id alone is not narrowing enough for large taxa
    organism = filters.get("organism_id")
    if organism and str(organism) not in LARGE_ORGANISM_IDS:
        return True
    return False


def validate_uniprot_scope(
    *,
    query: str,
    filters: dict[str, Any],
    operation: str,
) -> None:
    if filters.get("accession"):
        return
    if "accession:" in query.lower():
        return

    organism = filters.get("organism_id")
    if organism and str(organism) in LARGE_ORGANISM_IDS and not has_narrowing_filter(filters, query):
        raise KikiError(
            ErrorCode.QUERY_TOO_BROAD,
            f"Cannot {operation} for a large organism without narrowing filters "
            "(gene, protein_name, accession, length, or a specific query).",
            details={
                "organism_id": organism,
                "required_filters": ["gene", "protein_name", "accession", "length_min", "length_max", "query"],
            },
        )

    if query.strip() in {"(reviewed:true)", "reviewed:true"}:
        raise KikiError(
            ErrorCode.QUERY_TOO_BROAD,
            f"Cannot {operation} with only reviewed:true — add organism, gene, or protein filters.",
        )


def validate_length_range(length_min: int | None, length_max: int | None) -> None:
    if length_min is not None and length_max is not None and length_min > length_max:
        raise KikiError(
            ErrorCode.INVALID_SEQ_LENGTH_RANGE,
            "length_min cannot be greater than length_max.",
            details={"length_min": length_min, "length_max": length_max},
        )

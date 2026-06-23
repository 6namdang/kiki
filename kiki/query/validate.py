import re
from typing import Any

from kiki.errors import ErrorCode, KikiError

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(value: str, field: str) -> None:
    if not DATE_PATTERN.match(value):
        raise KikiError(
            ErrorCode.INVALID_DATE_FORMAT,
            f"{field} must use YYYY-MM-DD format.",
            details={"field": field, "value": value},
        )


def _validate_date_order(min_key: str, max_key: str, filters: dict[str, Any]) -> None:
    min_val = filters.get(min_key)
    max_val = filters.get(max_key)
    if min_val is None or max_val is None:
        return
    _validate_date(min_val, min_key)
    _validate_date(max_val, max_key)
    if min_val > max_val:
        raise KikiError(
            ErrorCode.INVALID_DATE_RANGE,
            f"{min_key} cannot be after {max_key}.",
            details={min_key: min_val, max_key: max_val},
        )


def validate_filters(filters: dict[str, Any]) -> None:
    """Reject invalid filter combinations before any network or disk I/O."""
    for field in (
        "min_collection_date",
        "max_collection_date",
        "min_release_date",
        "max_release_date",
    ):
        if field in filters and filters[field] is not None:
            _validate_date(filters[field], field)

    _validate_date_order("min_collection_date", "max_collection_date", filters)
    _validate_date_order("min_release_date", "max_release_date", filters)

    min_len = filters.get("min_seq_length")
    max_len = filters.get("max_seq_length")
    if min_len is not None and max_len is not None and min_len > max_len:
        raise KikiError(
            ErrorCode.INVALID_SEQ_LENGTH_RANGE,
            "min_seq_length cannot be greater than max_seq_length.",
            details={"min_seq_length": min_len, "max_seq_length": max_len},
        )

    min_genes = filters.get("min_gene_count")
    max_genes = filters.get("max_gene_count")
    if min_genes is not None and max_genes is not None and min_genes > max_genes:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "min_gene_count cannot be greater than max_gene_count.",
            details={"min_gene_count": min_genes, "max_gene_count": max_genes},
        )

    min_proteins = filters.get("min_protein_count")
    max_proteins = filters.get("max_protein_count")
    if min_proteins is not None and max_proteins is not None and min_proteins > max_proteins:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "min_protein_count cannot be greater than max_protein_count.",
            details={"min_protein_count": min_proteins, "max_protein_count": max_proteins},
        )

    min_peptides = filters.get("min_mature_peptide_count")
    max_peptides = filters.get("max_mature_peptide_count")
    if (
        min_peptides is not None
        and max_peptides is not None
        and min_peptides > max_peptides
    ):
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "min_mature_peptide_count cannot be greater than max_mature_peptide_count.",
            details={
                "min_mature_peptide_count": min_peptides,
                "max_mature_peptide_count": max_peptides,
            },
        )

    nuc = filters.get("nuc_completeness")
    if nuc is not None and nuc not in {"complete", "partial"}:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "nuc_completeness must be 'complete' or 'partial'.",
            details={"nuc_completeness": nuc},
        )

    source_db = filters.get("source_database")
    if source_db is not None and source_db not in {"genbank", "refseq"}:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "source_database must be 'genbank' or 'refseq'.",
            details={"source_database": source_db},
        )

    batch_size = filters.get("genbank_batch_size")
    if batch_size is not None and batch_size < 1:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "genbank_batch_size must be a positive integer.",
            details={"genbank_batch_size": batch_size},
        )

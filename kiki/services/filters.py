"""Shared filter validation and gget parameter mapping."""

from typing import Any

from kiki.config import LARGE_TAXIDS
from kiki.errors import ErrorCode, KikiError

# Filters that narrow large taxon queries (required for known-huge datasets).
NARROWING_FILTER_KEYS = (
    "host",
    "geographic_location",
    "min_seq_length",
    "max_seq_length",
    "min_collection_date",
    "max_collection_date",
    "min_release_date",
    "max_release_date",
    "nuc_completeness",
    "complete_only",
    "annotated",
    "source_database",
    "refseq_only",
    "lineage",
    "isolate",
    "submitter_country",
    "min_gene_count",
    "max_gene_count",
    "has_proteins",
    "segment",
    "min_protein_count",
    "max_protein_count",
)

LARGE_TAXON_ALIASES = frozenset({"sars-cov-2", "sarscov2", "sars cov-2", "ebola virus"})


def has_narrowing_filter(filters: dict[str, Any]) -> bool:
    return any(filters.get(key) not in (None, "", False) for key in NARROWING_FILTER_KEYS)


def is_large_taxon_query(query: str) -> bool:
    normalized = query.strip().lower()
    return query in LARGE_TAXIDS or normalized in LARGE_TAXON_ALIASES


def validate_query_scope(
    *,
    query: str,
    is_accession: bool,
    filters: dict[str, Any],
    operation: str,
) -> None:
    if filters.get("download_all_accessions"):
        if not has_narrowing_filter(filters):
            raise KikiError(
                ErrorCode.QUERY_TOO_BROAD,
                "download_all_accessions without narrowing filters would fetch the entire "
                "Viruses taxonomy (taxon 10239). Add filters such as host, dates, or lineage.",
                details={"required_filters": list(NARROWING_FILTER_KEYS)},
            )
        return

    if is_accession or not query.strip():
        return

    if is_large_taxon_query(query) and not has_narrowing_filter(filters):
        raise KikiError(
            ErrorCode.QUERY_TOO_BROAD,
            f"Cannot {operation} for a very large virus dataset without narrowing filters.",
            details={
                "query": query,
                "required_filters": list(NARROWING_FILTER_KEYS),
            },
        )


def drop_none(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def _resolve_nuc_completeness(filters: dict[str, Any]) -> str | None:
    if filters.get("nuc_completeness") is not None:
        return filters["nuc_completeness"]
    if filters.get("complete_only") is True:
        return "complete"
    if filters.get("complete_only") is False:
        return "partial"
    return None


def _resolve_source_database(filters: dict[str, Any]) -> str | None:
    if filters.get("source_database") is not None:
        return filters["source_database"]
    if filters.get("refseq_only") is True:
        return "refseq"
    return None


def metadata_kwargs(filters: dict[str, Any]) -> dict[str, Any]:
    """Map MCP filter names to gget fetch_virus_metadata parameters."""
    return drop_none(
        {
            "host": filters.get("host"),
            "geographic_location": filters.get("geographic_location"),
            "annotated": filters.get("annotated"),
            "complete_only": filters.get("complete_only"),
            "min_release_date": filters.get("min_release_date"),
            "refseq_only": filters.get("refseq_only"),
        }
    )


def virus_kwargs(filters: dict[str, Any]) -> dict[str, Any]:
    """Map MCP filter names to gget.virus parameters (full docs coverage)."""
    return drop_none(
        {
            "host": filters.get("host"),
            "min_seq_length": filters.get("min_seq_length"),
            "max_seq_length": filters.get("max_seq_length"),
            "min_gene_count": filters.get("min_gene_count"),
            "max_gene_count": filters.get("max_gene_count"),
            "nuc_completeness": _resolve_nuc_completeness(filters),
            "has_proteins": filters.get("has_proteins"),
            "proteins_complete": filters.get("proteins_complete"),
            "lab_passaged": filters.get("lab_passaged"),
            "geographic_location": filters.get("geographic_location"),
            "submitter_country": filters.get("submitter_country"),
            "min_collection_date": filters.get("min_collection_date"),
            "max_collection_date": filters.get("max_collection_date"),
            "source_database": _resolve_source_database(filters),
            "annotated": filters.get("annotated"),
            "keep_temp": filters.get("keep_temp"),
            "min_release_date": filters.get("min_release_date"),
            "max_release_date": filters.get("max_release_date"),
            "min_mature_peptide_count": filters.get("min_mature_peptide_count"),
            "max_mature_peptide_count": filters.get("max_mature_peptide_count"),
            "min_protein_count": filters.get("min_protein_count"),
            "max_protein_count": filters.get("max_protein_count"),
            "max_ambiguous_chars": filters.get("max_ambiguous_chars"),
            "is_sars_cov2": filters.get("is_sars_cov2"),
            "is_alphainfluenza": filters.get("is_alphainfluenza"),
            "segment": filters.get("segment"),
            "vaccine_strain": filters.get("vaccine_strain"),
            "lineage": filters.get("lineage"),
            "genbank_metadata": filters.get("genbank_metadata"),
            "genbank_batch_size": filters.get("genbank_batch_size"),
            "download_all_accessions": filters.get("download_all_accessions"),
            "provirus": filters.get("provirus"),
            "isolate": filters.get("isolate"),
            "genotype": filters.get("genotype"),
            "isolation_source": filters.get("isolation_source"),
            "env_source": filters.get("env_source"),
            "submitter_name": filters.get("submitter_name"),
            "submitter_institution": filters.get("submitter_institution"),
            "gen_mol_type": filters.get("gen_mol_type"),
            "verbose": filters.get("verbose"),
        }
    )

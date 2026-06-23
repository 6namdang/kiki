"""Shared filter validation and gget parameter mapping."""

from typing import Any

from kiki.config import LARGE_TAXIDS

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
    "lineage",
    "isolate",
    "refseq_only",
    "submitter_country",
    "min_gene_count",
    "max_gene_count",
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
    if is_accession:
        return
    if is_large_taxon_query(query) and not has_narrowing_filter(filters):
        raise ValueError(
            f"Cannot {operation} for a very large virus dataset without narrowing filters. "
            "Add at least one of: host, geographic_location, dates, sequence length, "
            "complete_only, annotated, lineage, or source_database."
        )


def drop_none(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


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
    """Map MCP filter names to gget.virus parameters."""
    return drop_none(
        {
            "host": filters.get("host"),
            "min_seq_length": filters.get("min_seq_length"),
            "max_seq_length": filters.get("max_seq_length"),
            "min_gene_count": filters.get("min_gene_count"),
            "max_gene_count": filters.get("max_gene_count"),
            "nuc_completeness": filters.get("nuc_completeness"),
            "has_proteins": filters.get("has_proteins"),
            "proteins_complete": filters.get("proteins_complete"),
            "lab_passaged": filters.get("lab_passaged"),
            "geographic_location": filters.get("geographic_location"),
            "submitter_country": filters.get("submitter_country"),
            "min_collection_date": filters.get("min_collection_date"),
            "max_collection_date": filters.get("max_collection_date"),
            "source_database": filters.get("source_database"),
            "annotated": filters.get("annotated"),
            "min_release_date": filters.get("min_release_date"),
            "max_release_date": filters.get("max_release_date"),
            "min_mature_peptide_count": filters.get("min_mature_peptide_count"),
            "max_mature_peptide_count": filters.get("max_mature_peptide_count"),
            "min_protein_count": filters.get("min_protein_count"),
            "max_protein_count": filters.get("max_protein_count"),
            "max_ambiguous_chars": filters.get("max_ambiguous_chars"),
            "segment": filters.get("segment"),
            "vaccine_strain": filters.get("vaccine_strain"),
            "lineage": filters.get("lineage"),
            "genbank_metadata": filters.get("genbank_metadata"),
            "provirus": filters.get("provirus"),
            "isolate": filters.get("isolate"),
            "genotype": filters.get("genotype"),
            "isolation_source": filters.get("isolation_source"),
            "env_source": filters.get("env_source"),
            "submitter_name": filters.get("submitter_name"),
            "submitter_institution": filters.get("submitter_institution"),
            "gen_mol_type": filters.get("gen_mol_type"),
            "verbose": filters.get("verbose", False),
        }
    )

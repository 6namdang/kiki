"""Shared MCP tool filter parameters for gget.virus / fetch_virus_metadata."""

from typing import Any


def common_filter_params() -> dict[str, Any]:
    """Return a dict of shared filter parameter defaults for tool signatures."""
    return {
        "host": None,
        "geographic_location": None,
        "annotated": None,
        "complete_only": None,
        "refseq_only": None,
        "min_release_date": None,
        "max_release_date": None,
        "min_collection_date": None,
        "max_collection_date": None,
        "min_seq_length": None,
        "max_seq_length": None,
        "nuc_completeness": None,
        "source_database": None,
        "lineage": None,
        "isolate": None,
    }


def collect_filters(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def dataset_only_filter_params() -> dict[str, Any]:
    return {
        "min_gene_count": None,
        "max_gene_count": None,
        "has_proteins": None,
        "proteins_complete": None,
        "lab_passaged": None,
        "submitter_country": None,
        "min_mature_peptide_count": None,
        "max_mature_peptide_count": None,
        "min_protein_count": None,
        "max_protein_count": None,
        "max_ambiguous_chars": None,
        "segment": None,
        "vaccine_strain": None,
        "genbank_metadata": None,
        "provirus": None,
        "genotype": None,
        "isolation_source": None,
        "env_source": None,
        "submitter_name": None,
        "submitter_institution": None,
        "gen_mol_type": None,
    }

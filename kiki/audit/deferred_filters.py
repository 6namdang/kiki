"""Human-readable explanations for gget filter application stages."""

from __future__ import annotations

from typing import Any

# Filters supported by gget.fetch_virus_metadata API (when not deferred).
METADATA_API_FILTERS = frozenset(
    {
        "host",
        "geographic_location",
        "annotated",
        "complete_only",
        "refseq_only",
        "min_release_date",
    }
)

# Filters applied locally by gget.virus after metadata fetch (never server-side).
DATASET_LOCAL_FILTERS = frozenset(
    {
        "min_collection_date",
        "max_collection_date",
        "max_release_date",
        "min_seq_length",
        "max_seq_length",
        "min_gene_count",
        "max_gene_count",
        "nuc_completeness",
        "has_proteins",
        "proteins_complete",
        "lab_passaged",
        "submitter_country",
        "min_mature_peptide_count",
        "max_mature_peptide_count",
        "min_protein_count",
        "max_protein_count",
        "max_ambiguous_chars",
        "segment",
        "vaccine_strain",
        "source_database",
        "lineage",
        "isolate",
        "genotype",
        "isolation_source",
        "env_source",
        "submitter_name",
        "submitter_institution",
        "gen_mol_type",
        "provirus",
    }
)

DEFERRED_REASONS: dict[str, str] = {
    "host": (
        "Applied locally during metadata filtering because the NCBI Virus API "
        "could not apply the host filter server-side for this query."
    ),
    "geographic_location": (
        "Applied locally during metadata filtering because the NCBI Virus API "
        "could not apply the geographic location filter server-side for this query."
    ),
}

LOCAL_REASONS: dict[str, str] = {
    "min_collection_date": "Applied locally — collection dates are not exposed on the metadata API.",
    "max_collection_date": "Applied locally — collection dates are not exposed on the metadata API.",
    "max_release_date": "Applied locally — max release date filtering runs during gget metadata filtering.",
    "min_seq_length": "Applied locally after metadata retrieval using sequence length fields.",
    "max_seq_length": "Applied locally after metadata retrieval using sequence length fields.",
    "min_gene_count": "Applied locally using GenBank annotation counts.",
    "max_gene_count": "Applied locally using GenBank annotation counts.",
    "nuc_completeness": "Applied locally using completeness metadata (or mapped from complete_only).",
    "has_proteins": "Applied locally — requires GenBank protein annotation lookup.",
    "proteins_complete": "Applied locally — requires GenBank protein completeness check.",
    "lab_passaged": "Applied locally using sample metadata fields.",
    "submitter_country": "Applied locally using submitter metadata.",
    "lineage": "Applied locally using lineage metadata (common for SARS-CoV-2).",
    "segment": "Applied locally — segment names are context-dependent and filtered post-fetch.",
    "genbank_metadata": "Triggers additional GenBank efetch batches after primary metadata filtering.",
}


def explain_filter_application(
    *,
    requested_filters: dict[str, Any],
    deferred_filters: dict[str, Any] | None,
    operation: str,
) -> dict[str, Any]:
    """Describe how each requested filter was applied for audit/provenance."""
    deferred = dict(deferred_filters or {})
    requested = {k: v for k, v in requested_filters.items() if v is not None}

    api_applied: list[dict[str, str]] = []
    locally_applied: list[dict[str, str]] = []
    deferred_applied: list[dict[str, str]] = []

    for name, value in sorted(requested.items()):
        if name in deferred:
            deferred_applied.append(
                {
                    "filter": name,
                    "value": str(value),
                    "stage": "deferred_local",
                    "explanation": DEFERRED_REASONS.get(
                        name,
                        "Applied locally during metadata filtering because gget could not "
                        "apply this filter via the NCBI Virus API for this query.",
                    ),
                }
            )
        elif name in METADATA_API_FILTERS and operation in {
            "metadata_paginated",
            "metadata_count",
        }:
            api_applied.append(
                {
                    "filter": name,
                    "value": str(value),
                    "stage": "ncbi_virus_api",
                    "explanation": "Applied server-side via gget.fetch_virus_metadata / NCBI Virus API.",
                }
            )
        elif name in DATASET_LOCAL_FILTERS or name in {
            "complete_only",
            "refseq_only",
        }:
            locally_applied.append(
                {
                    "filter": name,
                    "value": str(value),
                    "stage": "local_metadata_filter",
                    "explanation": LOCAL_REASONS.get(
                        name,
                        "Applied locally by gget.virus during metadata filtering.",
                    ),
                }
            )
        elif name in METADATA_API_FILTERS:
            locally_applied.append(
                {
                    "filter": name,
                    "value": str(value),
                    "stage": "local_metadata_filter",
                    "explanation": LOCAL_REASONS.get(
                        name,
                        "Applied locally by gget.virus (may be deferred from API depending on query).",
                    ),
                }
            )

    summary_parts: list[str] = []
    if api_applied:
        summary_parts.append(
            f"{len(api_applied)} filter(s) applied via NCBI Virus API."
        )
    if deferred_applied:
        summary_parts.append(
            f"{len(deferred_applied)} filter(s) deferred from API and applied locally: "
            f"{', '.join(item['filter'] for item in deferred_applied)}."
        )
    if locally_applied:
        summary_parts.append(
            f"{len(locally_applied)} filter(s) applied locally by gget after metadata fetch."
        )
    if not summary_parts:
        summary_parts.append("No narrowing filters were requested.")

    return {
        "summary": " ".join(summary_parts),
        "api_applied": api_applied,
        "deferred_to_local": deferred_applied,
        "local_only": locally_applied,
        "deferred_raw": deferred or None,
    }

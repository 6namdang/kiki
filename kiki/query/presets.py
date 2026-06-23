"""Curated, deterministic queries for common agent workflows.

Metadata presets use filters supported by gget.fetch_virus_metadata (count/metadata tools).
Dataset presets include additional gget.virus filters (dates, sequence length, etc.).
"""

from typing import Any

from kiki.errors import ErrorCode, KikiError

PRESETS: dict[str, dict[str, Any]] = {
    # Metadata / count compatible (fetch_virus_metadata filters)
    "ebola_human_complete_africa": {
        "query": "186538",
        "is_accession": False,
        "host": "Homo sapiens",
        "complete_only": True,
        "geographic_location": "Africa",
    },
    "sars_cov2_ref_genome": {
        "query": "NC_045512.2",
        "is_accession": True,
        "is_sars_cov2": True,
    },
    # Full dataset presets (retrieve_virus_dataset — all gget.virus filters)
    "ebola_human_complete_since_2014": {
        "query": "186538",
        "is_accession": False,
        "host": "Homo sapiens",
        "nuc_completeness": "complete",
        "min_collection_date": "2014-01-01",
        "geographic_location": "Africa",
    },
    "sars_cov2_human_complete": {
        "query": "SARS-CoV-2",
        "is_accession": False,
        "is_sars_cov2": True,
        "host": "Homo sapiens",
        "nuc_completeness": "complete",
        "min_seq_length": 29000,
        "genbank_metadata": True,
    },
    "influenza_a_human_complete": {
        "query": "Influenza A virus",
        "is_accession": False,
        "is_alphainfluenza": True,
        "host": "Homo sapiens",
        "nuc_completeness": "complete",
        "max_seq_length": 15000,
        "genbank_metadata": True,
    },
}


def list_presets() -> list[str]:
    return sorted(PRESETS)


def resolve_preset(preset: str | None, overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge a named preset with explicit tool arguments (explicit wins)."""
    if not preset:
        return overrides

    if preset not in PRESETS:
        raise KikiError(
            ErrorCode.PRESET_NOT_FOUND,
            f"Unknown preset '{preset}'.",
            details={"preset": preset, "available_presets": list_presets()},
        )

    merged = {**PRESETS[preset]}
    for key, value in overrides.items():
        if value is not None and value != "" and value is not False:
            merged[key] = value
    return merged

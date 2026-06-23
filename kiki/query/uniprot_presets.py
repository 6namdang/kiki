"""Curated UniProt queries for viral and general protein workflows."""

from typing import Any

from kiki.errors import ErrorCode, KikiError

PRESETS: dict[str, dict[str, Any]] = {
    "sars_cov2_spike": {
        "query": "(organism_id:2697049) AND (protein_name:spike)",
        "reviewed_only": True,
    },
    "sars_cov2_nsp12": {
        "query": "(organism_id:2697049) AND (gene:nsp12)",
        "reviewed_only": True,
    },
    "ebola_vp35": {
        "query": "(organism_id:186538) AND (gene:VP35)",
        "reviewed_only": True,
    },
    "influenza_a_ha": {
        "query": '(organism_name:"Influenza A virus") AND (protein_name:hemagglutinin)',
        "reviewed_only": True,
    },
    "human_insulin": {
        "organism_id": "9606",
        "gene": "INS",
        "reviewed_only": True,
    },
    "human_tp53": {
        "organism_id": "9606",
        "gene": "TP53",
        "reviewed_only": True,
    },
}


def list_uniprot_presets() -> list[str]:
    return sorted(PRESETS)


def resolve_uniprot_preset(preset: str | None, overrides: dict[str, Any]) -> dict[str, Any]:
    if not preset:
        return overrides

    if preset not in PRESETS:
        raise KikiError(
            ErrorCode.PRESET_NOT_FOUND,
            f"Unknown UniProt preset '{preset}'.",
            details={"preset": preset, "available_presets": list_uniprot_presets()},
        )

    merged = {**PRESETS[preset]}
    for key, value in overrides.items():
        if value is not None and value != "" and value is not False:
            merged[key] = value
    return merged

"""Shared helpers for UniProt MCP tools."""

from __future__ import annotations

from typing import Any

from kiki.errors import ErrorCode, KikiError
from kiki.models.manifest import QueryManifest, build_provenance
from kiki.query.uniprot import build_uniprot_query, validate_length_range, validate_uniprot_scope
from kiki.query.uniprot_presets import resolve_uniprot_preset

UNIPROT_MCP_ONLY = frozenset({"preset", "confirm_download", "preview_limit", "format"})


def uniprot_filter_kwargs(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def build_uniprot_params(
    *,
    preset: str | None,
    query: str | None = None,
    reviewed_only: bool = True,
    include_unreviewed: bool = False,
    organism_id: str | None = None,
    gene: str | None = None,
    protein_name: str | None = None,
    accession: str | None = None,
    length_min: int | None = None,
    length_max: int | None = None,
    preview_limit: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    explicit = {
        "query": query,
        "reviewed_only": reviewed_only,
        "include_unreviewed": include_unreviewed,
        "organism_id": organism_id,
        "gene": gene,
        "protein_name": protein_name,
        "accession": accession,
        "length_min": length_min,
        "length_max": length_max,
        **uniprot_filter_kwargs(**extra),
    }
    if preview_limit is not None:
        explicit["preview_limit"] = preview_limit

    if preset:
        resolved = resolve_uniprot_preset(preset, explicit)
        if preset:
            resolved["preset"] = preset
        return resolved

    if accession and not query:
        return explicit

    return explicit


def resolve_uniprot_query(params: dict[str, Any]) -> str:
    validate_length_range(params.get("length_min"), params.get("length_max"))
    return build_uniprot_query(
        query=params.get("query"),
        reviewed_only=params.get("reviewed_only", True),
        include_unreviewed=params.get("include_unreviewed", False),
        organism_id=params.get("organism_id"),
        gene=params.get("gene"),
        protein_name=params.get("protein_name"),
        accession=params.get("accession"),
        length_min=params.get("length_min"),
        length_max=params.get("length_max"),
    )


def extract_uniprot_filters(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in params.items()
        if key not in UNIPROT_MCP_ONLY and key != "uniprot_query"
    }


def uniprot_success_manifest(
    *,
    tool: str,
    params: dict[str, Any],
    uniprot_query: str,
    result: dict[str, Any],
    operation: str,
    message: str,
    provenance_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query_payload = {
        "type": "uniprot",
        "value": uniprot_query,
        **extract_uniprot_filters(params),
    }
    if params.get("accession"):
        query_payload["accession"] = params["accession"]

    filters_applied = sorted(
        key
        for key in params
        if key not in UNIPROT_MCP_ONLY and key not in {"query", "uniprot_query"} and params[key] is not None
    )
    if params.get("preset"):
        filters_applied.append(f"preset:{params['preset']}")

    manifest = QueryManifest(
        tool=tool,
        success=True,
        query=query_payload,
        result=result,
        provenance=build_provenance(
            engine="uniprot.rest",
            operation=operation,
            params={**params, "uniprot_query": uniprot_query},
            filters_applied=filters_applied,
            extra=provenance_extra,
        ),
        message=message,
    )
    return manifest.to_dict()


def guard_uniprot_scope(params: dict[str, Any], uniprot_query: str, operation: str) -> None:
    validate_uniprot_scope(
        query=uniprot_query,
        filters=params,
        operation=operation,
    )

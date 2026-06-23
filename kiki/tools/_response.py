from typing import Any

from kiki.errors import ErrorCode, KikiError
from kiki.models.manifest import QueryManifest, build_provenance
from kiki.query.presets import resolve_preset

MCP_ONLY_KEYS = frozenset({"preset", "confirm_download", "preview_limit"})


def extract_filters(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in params.items()
        if key not in MCP_ONLY_KEYS and key != "query" and value is not None
    }


def build_query_params(
    *,
    preset: str | None,
    query: str | None,
    is_accession: bool,
    download_all_accessions: bool = False,
    **filters: Any,
) -> dict[str, Any]:
    explicit: dict[str, Any] = {
        "query": query,
        "is_accession": is_accession,
        **{key: value for key, value in filters.items() if value is not None},
    }
    if download_all_accessions:
        explicit["download_all_accessions"] = True
        if not explicit.get("query"):
            explicit["query"] = ""

    if preset:
        resolved = resolve_preset(preset, explicit)
        if not resolved.get("query") and not resolved.get("download_all_accessions"):
            raise KikiError(
                ErrorCode.INVALID_PARAMETER,
                "Provide query, download_all_accessions, or a preset that includes query.",
            )
        return resolved

    if download_all_accessions:
        return explicit

    if not query:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Provide query, preset, or download_all_accessions with filters.",
        )
    return explicit


def filters_applied(params: dict[str, Any]) -> list[str]:
    applied = sorted(
        key
        for key in params
        if key not in MCP_ONLY_KEYS and key != "query" and params[key] is not None
    )
    if params.get("preset"):
        applied.append(f"preset:{params['preset']}")
    return applied


def success_manifest(
    *,
    tool: str,
    params: dict[str, Any],
    result: dict[str, Any],
    engine: str,
    operation: str,
    message: str,
    provenance_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query_value = params.get("query", "")
    query_type = "accession" if params.get("is_accession") else "taxon"
    if params.get("download_all_accessions"):
        query_type = "download_all_accessions"

    manifest = QueryManifest(
        tool=tool,
        success=True,
        query={
            "type": query_type,
            "value": query_value,
            **{key: params[key] for key in params if key != "query"},
        },
        result=result,
        provenance=build_provenance(
            engine=engine,
            operation=operation,
            params=params,
            filters_applied=filters_applied(params),
            extra=provenance_extra,
        ),
        message=message,
    )
    return manifest.to_dict()

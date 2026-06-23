"""Shared helpers for gget Ensembl MCP tools."""

from __future__ import annotations

from typing import Any

from kiki.audit.history import record_manifest
from kiki.models.manifest import QueryManifest, build_provenance

GGET_ENSEMBL_MCP_ONLY = frozenset({"confirm_download", "outfolder", "preview_limit"})


def ensembl_success_manifest(
    *,
    tool: str,
    params: dict[str, Any],
    query_type: str,
    query_value: str | list[str] | dict[str, Any],
    result: dict[str, Any],
    engine: str,
    operation: str,
    message: str,
    provenance_extra: dict[str, Any] | None = None,
    record_history: bool = True,
) -> dict[str, Any]:
    query_payload: dict[str, Any] = {
        "type": query_type,
        "value": query_value,
    }
    for key, value in params.items():
        if key in GGET_ENSEMBL_MCP_ONLY or value is None:
            continue
        if key not in query_payload:
            query_payload[key] = value

    filters_applied = sorted(
        key
        for key in params
        if key not in GGET_ENSEMBL_MCP_ONLY and params[key] is not None
    )

    manifest = QueryManifest(
        tool=tool,
        success=True,
        query=query_payload,
        result=result,
        provenance=build_provenance(
            engine=engine,
            operation=operation,
            params=params,
            filters_applied=filters_applied,
            extra=provenance_extra,
        ),
        message=message,
    )
    payload = manifest.to_dict()
    if record_history:
        payload["audit_record"] = record_manifest(payload)
    return payload

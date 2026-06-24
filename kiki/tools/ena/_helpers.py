"""Shared helpers for ENA MCP tools."""

from __future__ import annotations

from typing import Any

from kiki.audit.history import record_manifest
from kiki.models.manifest import QueryManifest, build_provenance

ENA_MCP_ONLY = frozenset({"confirm_download", "outfolder"})

ENA_PAGINATION_NOTE = (
    "ENA Portal defaults to 100000 rows, which can silently look complete. "
    "Kiki uses Portal /count for totals and limit=0 for full retrieval."
)


def ena_success_manifest(
    *,
    tool: str,
    params: dict[str, Any],
    query_type: str,
    query_value: str,
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
        if key in ENA_MCP_ONLY or value is None:
            continue
        if key not in query_payload:
            query_payload[key] = value

    filters_applied = sorted(
        key for key in params if key not in ENA_MCP_ONLY and params[key] is not None
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

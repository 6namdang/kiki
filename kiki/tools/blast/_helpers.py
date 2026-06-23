"""Shared helpers for NCBI BLAST MCP tools."""

from __future__ import annotations

from typing import Any

from kiki.audit.history import record_manifest
from kiki.models.manifest import QueryManifest, build_provenance

BLAST_DATABASE_NOTE = (
    "Hit lists depend on the NCBI BLAST database build at search time; "
    "identical parameters may return different hits after NCBI updates databases."
)
BLAST_RID_NOTE = (
    "RIDs expire in ~24 hours. Kiki does not persist RIDs; use get_blast_results "
    "promptly and rely on the QueryManifest audit entry for provenance."
)


def blast_success_manifest(
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
        if value is None:
            continue
        if key not in query_payload:
            query_payload[key] = value

    filters_applied = sorted(key for key, value in params.items() if value is not None)

    extra = {
        "database_note": BLAST_DATABASE_NOTE,
        **(provenance_extra or {}),
    }

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
            extra=extra,
        ),
        message=message,
    )
    payload = manifest.to_dict()
    if record_history:
        payload["audit_record"] = record_manifest(payload)
    return payload

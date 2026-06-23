"""Build enriched provenance blocks for gget-backed tools."""

from __future__ import annotations

from typing import Any

from kiki.audit.deferred_filters import explain_filter_application
from kiki.services.command_summary import summarize_command_summary


def build_metadata_execution_audit(
    *,
    filters: dict[str, Any],
    deferred_filters: dict[str, Any] | None,
    pagination_complete: bool,
) -> dict[str, Any]:
    return {
        "pagination_complete": pagination_complete,
        "filter_application": explain_filter_application(
            requested_filters=filters,
            deferred_filters=deferred_filters,
            operation="metadata_paginated",
        ),
    }


def build_dataset_execution_audit(
    *,
    filters: dict[str, Any],
    dataset_manifest: dict[str, Any],
) -> dict[str, Any]:
    audit: dict[str, Any] = {
        "filter_application": explain_filter_application(
            requested_filters=filters,
            deferred_filters=None,
            operation="dataset_download",
        ),
    }

    command_summary_path = dataset_manifest.get("artifacts", {}).get("command_summary")
    if command_summary_path:
        audit["command_summary"] = summarize_command_summary(command_summary_path)

    failures = dataset_manifest.get("failures")
    if failures:
        audit["failures"] = failures

    return audit

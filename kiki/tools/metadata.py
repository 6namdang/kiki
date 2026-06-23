from kiki.audit.gget_provenance import build_metadata_execution_audit
from kiki.services.ncbi import fetch_virus_metadata_query
from kiki.tools._errors import tool_safe
from kiki.tools._params import metadata_filter_kwargs
from kiki.tools._response import build_query_params, extract_filters, success_manifest


def register_metadata_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def get_virus_metadata(
        query: str | None = None,
        is_accession: bool = False,
        preset: str | None = None,
        preview_limit: int = 10,
        host: str | None = None,
        geographic_location: str | None = None,
        annotated: bool | None = None,
        complete_only: bool | None = None,
        refseq_only: bool | None = None,
        min_release_date: str | None = None,
    ) -> dict:
        """Query NCBI Virus metadata via gget with full pagination.

        Uses gget fetch_virus_metadata — all API pages are fetched before responding.
        Returns up to preview_limit records inline plus total_available count.
        Does not download sequence files. Large taxa require narrowing filters.
        """
        params = build_query_params(
            preset=preset,
            query=query,
            is_accession=is_accession,
            preview_limit=preview_limit,
            **metadata_filter_kwargs(
                host=host,
                geographic_location=geographic_location,
                annotated=annotated,
                complete_only=complete_only,
                refseq_only=refseq_only,
                min_release_date=min_release_date,
            ),
        )
        if preset:
            params["preset"] = preset

        filters = extract_filters(params)
        result = fetch_virus_metadata_query(
            query=params["query"],
            is_accession=params.get("is_accession", False),
            preview_limit=preview_limit,
            filters=filters,
        )

        return success_manifest(
            tool="get_virus_metadata",
            params=params,
            result={
                "returned": result["returned"],
                "total_available": result["total_fetched"],
                "records": result["records"],
            },
            engine="gget.fetch_virus_metadata",
            operation="metadata_paginated",
            message=(
                f"Fetched {result['total_fetched']} metadata records via gget pagination. "
                f"Returning {result['returned']} inline preview. No sequences downloaded."
            ),
            provenance_extra=build_metadata_execution_audit(
                filters=filters,
                deferred_filters=result.get("deferred_filters"),
                pagination_complete=result["pagination_complete"],
            ),
        )

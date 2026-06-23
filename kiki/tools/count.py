from kiki.audit.gget_provenance import build_metadata_execution_audit
from kiki.services.ncbi import fetch_virus_metadata_query
from kiki.tools._errors import tool_safe
from kiki.tools._params import metadata_filter_kwargs
from kiki.tools._response import build_query_params, extract_filters, success_manifest


def register_count_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def count_virus_sequences(
        query: str | None = None,
        is_accession: bool = False,
        preset: str | None = None,
        host: str | None = None,
        geographic_location: str | None = None,
        annotated: bool | None = None,
        complete_only: bool | None = None,
        refseq_only: bool | None = None,
        min_release_date: str | None = None,
    ) -> dict:
        """Count virus metadata records without downloading sequences.

        Uses the same gget.fetch_virus_metadata pagination path as get_virus_metadata
        with preview_limit=0. Supports metadata API filters and presets such as
        ebola_human_complete_africa. For counts that require dataset-only filters
        (collection dates, sequence length), use retrieve_virus_dataset and read
        manifest accession_count.
        """
        params = build_query_params(
            preset=preset,
            query=query,
            is_accession=is_accession,
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
            preview_limit=0,
            filters=filters,
        )

        return success_manifest(
            tool="count_virus_sequences",
            params=params,
            result={
                "count": result["total_fetched"],
                "pagination_complete": result["pagination_complete"],
            },
            engine="gget.fetch_virus_metadata",
            operation="metadata_count",
            message=(
                f"Counted {result['total_fetched']} metadata records. "
                "No sequences downloaded."
            ),
            provenance_extra=build_metadata_execution_audit(
                filters=filters,
                deferred_filters=result.get("deferred_filters"),
                pagination_complete=result["pagination_complete"],
            ),
        )

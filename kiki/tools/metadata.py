from kiki.audit import build_audit
from kiki.models import ToolResponse
from kiki.services.ncbi import fetch_virus_metadata_query
from kiki.tools._params import collect_filters


def register_metadata_tools(mcp) -> None:
    @mcp.tool()
    def get_virus_metadata(
        query: str,
        is_accession: bool = False,
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
        Returns up to preview_limit records inline plus total_fetched count.
        Does not download sequence files. Large taxa require narrowing filters.
        """
        filters = collect_filters(
            host=host,
            geographic_location=geographic_location,
            annotated=annotated,
            complete_only=complete_only,
            refseq_only=refseq_only,
            min_release_date=min_release_date,
        )
        params = {
            "query": query,
            "is_accession": is_accession,
            "preview_limit": preview_limit,
            **filters,
        }

        result = fetch_virus_metadata_query(
            query=query,
            is_accession=is_accession,
            preview_limit=preview_limit,
            filters=filters,
        )

        response = ToolResponse(
            tool="get_virus_metadata",
            success=True,
            query={"type": "accession" if is_accession else "taxon", "value": query, **params},
            returned=result["returned"],
            total_available=result["total_fetched"],
            records=result["records"],
            audit=build_audit(
                source="gget.fetch_virus_metadata",
                operation="metadata_paginated",
                params=params,
                extra={
                    "pagination_complete": result["pagination_complete"],
                    "deferred_filters": result.get("deferred_filters"),
                    "gget_version_note": "Full pagination handled by gget; preview_limit caps inline records.",
                },
            ),
            message=(
                f"Fetched {result['total_fetched']} metadata records via gget pagination. "
                f"Returning {result['returned']} inline preview. No sequences downloaded."
            ),
        )
        return response.to_dict()

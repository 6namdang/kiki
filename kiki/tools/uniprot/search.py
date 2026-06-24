from kiki.config import UNIPROT_MAX_PREVIEW
from kiki.services.uniprot import search_proteins
from kiki.tools._errors import tool_safe
from kiki.tools.uniprot._helpers import (
    build_uniprot_params,
    guard_uniprot_scope,
    resolve_uniprot_query,
    uniprot_success_manifest,
)


def register_uniprot_search_tools(mcp) -> None:
    @mcp.tool(name="search_proteins")
    @tool_safe
    def search_proteins_tool(
        query: str | None = None,
        preset: str | None = None,
        reviewed_only: bool = True,
        include_unreviewed: bool = False,
        organism_id: str | None = None,
        gene: str | None = None,
        protein_name: str | None = None,
        accession: str | None = None,
        length_min: int | None = None,
        length_max: int | None = None,
        preview_limit: int = 10,
    ) -> dict:
        """Search UniProtKB with full cursor pagination metadata.

        Returns up to preview_limit summarized records inline plus total_available.
        Defaults to reviewed:true (Swiss-Prot) unless include_unreviewed=true.
        Does not download sequences to disk.
        """
        preview_limit = min(max(1, preview_limit), UNIPROT_MAX_PREVIEW)
        params = build_uniprot_params(
            preset=preset,
            query=query,
            reviewed_only=reviewed_only,
            include_unreviewed=include_unreviewed,
            organism_id=organism_id,
            gene=gene,
            protein_name=protein_name,
            accession=accession,
            length_min=length_min,
            length_max=length_max,
            preview_limit=preview_limit,
        )
        uniprot_query = resolve_uniprot_query(params)
        guard_uniprot_scope(params, uniprot_query, "search proteins")

        result = search_proteins(uniprot_query, preview_limit=preview_limit)
        return uniprot_success_manifest(
            tool="search_proteins",
            params=params,
            uniprot_query=uniprot_query,
            result={
                "returned": result["returned"],
                "total_available": result["total_available"],
                "records": result["records"],
            },
            operation="uniprot_search",
            message=(
                f"Found {result['total_available']} UniProt entries. "
                f"Returning {result['returned']} inline preview."
            ),
            provenance_extra={
                "pagination_complete": result.get("pagination_complete"),
                "pages_fetched": result.get("pages_fetched"),
                "api_sequence": result.get("api_sequence"),
            },
        )

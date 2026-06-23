from kiki.services.uniprot import count_proteins
from kiki.tools._errors import tool_safe
from kiki.tools.uniprot._helpers import (
    build_uniprot_params,
    guard_uniprot_scope,
    resolve_uniprot_query,
    uniprot_success_manifest,
)


def register_uniprot_count_tools(mcp) -> None:
    @mcp.tool(name="count_proteins")
    @tool_safe
    def count_proteins_tool(
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
    ) -> dict:
        """Count UniProtKB entries for a query without downloading sequences.

        Uses X-Total-Results from a single UniProt REST request.
        Defaults to reviewed:true unless include_unreviewed=true.
        """
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
        )
        uniprot_query = resolve_uniprot_query(params)
        guard_uniprot_scope(params, uniprot_query, "count proteins")

        result = count_proteins(uniprot_query)
        return uniprot_success_manifest(
            tool="count_proteins",
            params=params,
            uniprot_query=uniprot_query,
            result={
                "count": result["count"],
                "pagination_complete": result["pagination_complete"],
            },
            operation="uniprot_count",
            message=f"Counted {result['count']} UniProt entries.",
        )

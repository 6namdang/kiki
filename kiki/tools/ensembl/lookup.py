from kiki.query.ensembl import (
    resolve_ensembl_release,
    validate_andor,
    validate_id_type,
    validate_search_limit,
)
from kiki.services.ensembl import (
    fetch_gene_info as ensembl_fetch_gene_info,
    normalize_ensembl_ids,
    search_genes as ensembl_search_genes,
)
from kiki.tools._errors import tool_safe
from kiki.tools.ensembl._helpers import ensembl_success_manifest


def register_ensembl_lookup_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def search_genes(
        searchwords: str | list[str],
        species: str,
        id_type: str = "gene",
        seqtype: str | None = None,
        andor: str = "or",
        limit: int = 20,
        release: int | None = None,
    ) -> dict:
        """Search Ensembl genes/transcripts by free-text terms.

        Queries Ensembl public SQL for the pinned release (default KIKI_ENSEMBL_RELEASE).
        species uses genus_species format (e.g. homo_sapiens).
        """
        if seqtype is not None:
            pass  # deprecated gget alias; ignored

        id_type = validate_id_type(id_type)
        andor = validate_andor(andor)
        limit = validate_search_limit(limit)
        ens_release = resolve_ensembl_release(release)

        params = {
            "searchwords": searchwords,
            "species": species.strip(),
            "id_type": id_type,
            "andor": andor,
            "limit": limit,
            "release": ens_release,
        }

        result = ensembl_search_genes(
            searchwords,
            species,
            id_type=id_type,
            andor=andor,
            limit=limit,
            release=ens_release,
        )

        terms = searchwords if isinstance(searchwords, list) else [searchwords]
        return ensembl_success_manifest(
            tool="search_genes",
            params=params,
            query_type="ensembl_search",
            query_value={"searchwords": terms, "species": species.strip()},
            result=result,
            engine="ensembl.sql",
            operation="gene_search",
            message=(
                f"Found {result['returned']} Ensembl match(es) for {species} "
                f"(release {ens_release})."
            ),
            provenance_extra={
                "pagination_complete": result.get("pagination_complete"),
                "truncated": result.get("truncated", False),
                "limit_applied": result.get("limit_applied"),
                "api_sequence": result.get("api_sequence"),
            },
        )

    @mcp.tool()
    @tool_safe
    def get_gene_info(
        ensembl_id: str | list[str],
        release: int | None = None,
        ncbi: bool = True,
        uniprot: bool = True,
        pdb: bool = False,
        ensembl_only: bool = False,
        expand: bool = False,
    ) -> dict:
        """Fetch gene/transcript metadata for Ensembl IDs via Ensembl REST lookup.

        Core metadata is fetched from the pinned Ensembl release. Optional NCBI/UniProt/PDB
        cross-refs are reserved for a future release of this tool.
        """
        ids = normalize_ensembl_ids(ensembl_id)
        ens_release = resolve_ensembl_release(release)
        params = {
            "ensembl_id": ids if len(ids) > 1 else ids[0],
            "release": ens_release,
            "ncbi": ncbi,
            "uniprot": uniprot,
            "pdb": pdb,
            "ensembl_only": ensembl_only,
            "expand": expand,
        }

        result = ensembl_fetch_gene_info(
            ids,
            release=ens_release,
            ncbi=ncbi,
            uniprot=uniprot,
            pdb=pdb,
            ensembl_only=ensembl_only,
            expand=expand,
        )

        return ensembl_success_manifest(
            tool="get_gene_info",
            params=params,
            query_type="ensembl_info",
            query_value=ids if len(ids) > 1 else ids[0],
            result=result,
            engine="ensembl.rest",
            operation="gene_info",
            message=(
                f"Retrieved metadata for {result['returned']} Ensembl ID(s) "
                f"(release {ens_release})."
            ),
        )

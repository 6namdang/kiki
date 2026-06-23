from kiki.services.gget_ensembl import (
    fetch_gene_info,
    normalize_ensembl_ids,
    search_genes as gget_search_genes,
)
from kiki.tools._errors import tool_safe
from kiki.tools.ensembl._helpers import ensembl_success_manifest
from kiki.query.ensembl import validate_andor, validate_id_type, validate_search_limit


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
        """Search Ensembl genes/transcripts by free-text terms via gget.search.

        species uses genus_species format (e.g. homo_sapiens). Returns structured JSON
        records with ensembl_id, gene_name, description, and Ensembl URL.
        """
        id_type = validate_id_type(id_type)
        andor = validate_andor(andor)
        limit = validate_search_limit(limit)

        params = {
            "searchwords": searchwords,
            "species": species.strip(),
            "id_type": id_type,
            "andor": andor,
            "limit": limit,
        }
        if seqtype is not None:
            params["seqtype"] = seqtype
        if release is not None:
            params["release"] = release

        result = gget_search_genes(
            searchwords,
            species,
            id_type=id_type,
            seqtype=seqtype,
            andor=andor,
            limit=limit,
            release=release,
        )

        terms = searchwords if isinstance(searchwords, list) else [searchwords]
        return ensembl_success_manifest(
            tool="search_genes",
            params=params,
            query_type="ensembl_search",
            query_value={"searchwords": terms, "species": species.strip()},
            result=result,
            engine="gget.search",
            operation="gene_search",
            message=f"Found {result['returned']} Ensembl match(es) for {species}.",
        )

    @mcp.tool()
    @tool_safe
    def get_gene_info(
        ensembl_id: str | list[str],
        ncbi: bool = True,
        uniprot: bool = True,
        pdb: bool = False,
        ensembl_only: bool = False,
        expand: bool = False,
    ) -> dict:
        """Fetch gene/transcript metadata for Ensembl IDs via gget.info.

        Returns Ensembl, NCBI, UniProt, and optional PDB cross-references inline.
        Pass a list of IDs to look up multiple genes in one call.
        """
        ids = normalize_ensembl_ids(ensembl_id)
        params = {
            "ensembl_id": ids if len(ids) > 1 else ids[0],
            "ncbi": ncbi,
            "uniprot": uniprot,
            "pdb": pdb,
            "ensembl_only": ensembl_only,
            "expand": expand,
        }

        result = fetch_gene_info(
            ids,
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
            engine="gget.info",
            operation="gene_info",
            message=f"Retrieved metadata for {result['returned']} Ensembl ID(s).",
        )

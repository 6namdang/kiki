from kiki.services.uniprot import list_id_mapping_fields, map_protein_ids
from kiki.tools._errors import tool_safe
from kiki.tools.uniprot._helpers import uniprot_success_manifest


def register_uniprot_mapping_tools(mcp) -> None:
    @mcp.tool(name="map_protein_ids")
    @tool_safe
    def map_protein_ids_tool(
        ids: list[str],
        from_db: str,
        to_db: str = "UniProtKB",
        list_databases: bool = False,
    ) -> dict:
        """Map protein identifiers across databases via UniProt ID mapping.

        Submits an async mapping job, polls until complete, and returns from/to pairs.
        Common from_db values: Gene_Name, UniProtKB_AC-ID, RefSeq_Protein, EMBL-Protein.
        Set list_databases=true to return supported mapping fields instead of mapping.
        """
        if list_databases:
            fields = list_id_mapping_fields()
            return uniprot_success_manifest(
                tool="map_protein_ids",
                params={"list_databases": True},
                uniprot_query="idmapping:fields",
                result={"databases": fields},
                operation="uniprot_idmapping_fields",
                message="Returned UniProt ID mapping supported fields.",
            )

        params = {"ids": ids, "from_db": from_db, "to_db": to_db}
        result = map_protein_ids(ids=ids, from_db=from_db, to_db=to_db)
        return uniprot_success_manifest(
            tool="map_protein_ids",
            params=params,
            uniprot_query=f"idmapping:{from_db}->{to_db}",
            result={
                "job_id": result["job_id"],
                "mapped_count": result["mapped_count"],
                "mappings": result["mappings"],
                "failed": result["failed"],
            },
            operation="uniprot_idmapping",
            message=f"Mapped {result['mapped_count']} of {len(ids)} ids from {from_db} to {to_db}.",
        )

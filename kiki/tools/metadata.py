from kiki.audit import build_audit
from kiki.models import ToolResponse
from kiki.services.ncbi import fetch_accession_metadata, fetch_taxon_metadata_page


def register_metadata_tools(mcp) -> None:
    @mcp.tool()
    def get_virus_metadata(
        taxid: str | None = None,
        accession: str | None = None,
        host: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Query NCBI Virus metadata without downloading sequences.

        Provide exactly one of taxid or accession.
        Returns JSON records plus an audit block. Does not write sequence files.
        """
        if bool(taxid) == bool(accession):
            raise ValueError("Provide exactly one of: taxid or accession")

        params = {
            "taxid": taxid,
            "accession": accession,
            "host": host,
            "limit": limit,
        }

        if accession:
            records = fetch_accession_metadata(accession, host=host, limit=limit)
            response = ToolResponse(
                tool="get_virus_metadata",
                success=True,
                query={"type": "accession", "value": accession, **params},
                returned=len(records),
                records=records,
                audit=build_audit(
                    source="ncbi_virus_api",
                    operation="metadata_by_accession",
                    params=params,
                ),
                message="Metadata query complete. No sequences downloaded.",
            )
            return response.to_dict()

        assert taxid is not None
        page = fetch_taxon_metadata_page(taxid, limit=limit, host=host)
        response = ToolResponse(
            tool="get_virus_metadata",
            success=True,
            query={"type": "taxid", "value": taxid, **params},
            returned=page["returned"],
            total_available=page["total_available"],
            records=page["records"],
            audit=build_audit(
                source="ncbi_virus_api",
                operation="metadata_by_taxid_page",
                params=params,
                extra={"note": "First page only; use retrieve_virus_dataset for full filtered downloads."},
            ),
            message="Metadata query complete. No sequences downloaded.",
        )
        return response.to_dict()

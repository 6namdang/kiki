from kiki.errors import ErrorCode, KikiError
from kiki.services.uniprot import get_protein as fetch_uniprot_entry
from kiki.tools._errors import tool_safe
from kiki.tools.uniprot._helpers import uniprot_success_manifest


def register_uniprot_get_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def get_protein(
        accession: str,
        format: str = "json",
    ) -> dict:
        """Retrieve a single UniProtKB entry by accession.

        format=json returns a summarized record inline.
        format=fasta|txt|xml|gff returns raw content in result.content.
        """
        accession = accession.strip()
        if not accession:
            raise KikiError(ErrorCode.INVALID_PARAMETER, "accession is required.")

        allowed = {"json", "fasta", "txt", "xml", "gff", "rdf"}
        if format not in allowed:
            raise KikiError(
                ErrorCode.INVALID_PARAMETER,
                f"format must be one of: {', '.join(sorted(allowed))}.",
                details={"format": format},
            )

        params = {"accession": accession, "format": format}
        result = fetch_uniprot_entry(accession, format=format)

        if format == "json":
            payload = {
                "accession": result["accession"],
                "record": result["record"],
            }
            message = f"Retrieved UniProt entry {result['accession']}."
        else:
            payload = {
                "accession": result["accession"],
                "format": result["format"],
                "content": result["content"],
            }
            message = f"Retrieved UniProt entry {result['accession']} as {format}."

        return uniprot_success_manifest(
            tool="get_protein",
            params=params,
            uniprot_query=f"accession:{accession}",
            result=payload,
            operation="uniprot_get",
            message=message,
        )

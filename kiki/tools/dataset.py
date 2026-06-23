from kiki.audit import build_audit
from kiki.models import ToolResponse
from kiki.services.gget_virus import retrieve_virus_dataset


def register_dataset_tools(mcp) -> None:
    @mcp.tool(name="retrieve_virus_dataset")
    def retrieve_virus_dataset(
        query: str,
        is_accession: bool = False,
        confirm_download: bool = False,
        host: str | None = None,
        min_seq_length: int | None = None,
        max_seq_length: int | None = None,
        geographic_location: str | None = None,
        min_collection_date: str | None = None,
        max_collection_date: str | None = None,
        min_release_date: str | None = None,
        max_release_date: str | None = None,
        nuc_completeness: str | None = None,
        source_database: str | None = None,
        lineage: str | None = None,
        isolate: str | None = None,
    ) -> dict:
        """Retrieve a filtered virus sequence dataset via gget.virus.

        Writes FASTA/metadata files to disk under kiki_output/.
        Requires confirm_download=true. Large taxon queries require filters.
        Returns JSON with output_dir and files paths — not inline sequences.
        """
        params = {
            "query": query,
            "is_accession": is_accession,
            "confirm_download": confirm_download,
            "host": host,
            "min_seq_length": min_seq_length,
            "max_seq_length": max_seq_length,
            "geographic_location": geographic_location,
            "min_collection_date": min_collection_date,
            "max_collection_date": max_collection_date,
            "min_release_date": min_release_date,
            "max_release_date": max_release_date,
            "nuc_completeness": nuc_completeness,
            "source_database": source_database,
            "lineage": lineage,
            "isolate": isolate,
        }
        filters = {key: value for key, value in params.items() if key not in {"query", "is_accession", "confirm_download"}}

        result = retrieve_virus_dataset(
            query=query,
            is_accession=is_accession,
            confirm_download=confirm_download,
            **filters,
        )

        response = ToolResponse(
            tool="retrieve_virus_dataset",
            success=True,
            query={"type": "accession" if is_accession else "taxon", "value": query, **params},
            returned=result["file_count"],
            output_dir=result["output_dir"],
            files=result["files"],
            audit=build_audit(
                source="gget.virus",
                operation="dataset_download",
                params=params,
            ),
            message="Dataset written to disk. Inspect output_dir and files.",
        )
        return response.to_dict()

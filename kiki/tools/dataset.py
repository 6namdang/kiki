from kiki.audit import build_audit
from kiki.models import ToolResponse
from kiki.services.gget_virus import run_virus_dataset
from kiki.tools._params import collect_filters


def register_dataset_tools(mcp) -> None:
    @mcp.tool(name="retrieve_virus_dataset")
    def retrieve_virus_dataset_tool(
        query: str,
        is_accession: bool = False,
        confirm_download: bool = False,
        host: str | None = None,
        geographic_location: str | None = None,
        annotated: bool | None = None,
        complete_only: bool | None = None,
        refseq_only: bool | None = None,
        min_release_date: str | None = None,
        max_release_date: str | None = None,
        min_collection_date: str | None = None,
        max_collection_date: str | None = None,
        min_seq_length: int | None = None,
        max_seq_length: int | None = None,
        min_gene_count: int | None = None,
        max_gene_count: int | None = None,
        nuc_completeness: str | None = None,
        has_proteins: bool | None = None,
        proteins_complete: bool | None = None,
        lab_passaged: bool | None = None,
        submitter_country: str | None = None,
        min_mature_peptide_count: int | None = None,
        max_mature_peptide_count: int | None = None,
        min_protein_count: int | None = None,
        max_protein_count: int | None = None,
        max_ambiguous_chars: int | None = None,
        segment: str | None = None,
        vaccine_strain: bool | None = None,
        source_database: str | None = None,
        lineage: str | None = None,
        isolate: str | None = None,
        genotype: str | None = None,
        isolation_source: str | None = None,
        env_source: str | None = None,
        submitter_name: str | None = None,
        submitter_institution: str | None = None,
        gen_mol_type: str | None = None,
        genbank_metadata: bool = False,
        provirus: bool | None = None,
    ) -> dict:
        """Retrieve a filtered virus sequence dataset via gget.virus.

        Wraps the full gget.virus pipeline: metadata filtering, pagination,
        sequence download, and local output files. Requires confirm_download=true.
        Large taxa require narrowing filters. Returns file paths and a manifest.
        """
        filters = collect_filters(
            host=host,
            geographic_location=geographic_location,
            annotated=annotated,
            complete_only=complete_only,
            refseq_only=refseq_only,
            min_release_date=min_release_date,
            max_release_date=max_release_date,
            min_collection_date=min_collection_date,
            max_collection_date=max_collection_date,
            min_seq_length=min_seq_length,
            max_seq_length=max_seq_length,
            min_gene_count=min_gene_count,
            max_gene_count=max_gene_count,
            nuc_completeness=nuc_completeness,
            has_proteins=has_proteins,
            proteins_complete=proteins_complete,
            lab_passaged=lab_passaged,
            submitter_country=submitter_country,
            min_mature_peptide_count=min_mature_peptide_count,
            max_mature_peptide_count=max_mature_peptide_count,
            min_protein_count=min_protein_count,
            max_protein_count=max_protein_count,
            max_ambiguous_chars=max_ambiguous_chars,
            segment=segment,
            vaccine_strain=vaccine_strain,
            source_database=source_database,
            lineage=lineage,
            isolate=isolate,
            genotype=genotype,
            isolation_source=isolation_source,
            env_source=env_source,
            submitter_name=submitter_name,
            submitter_institution=submitter_institution,
            gen_mol_type=gen_mol_type,
            genbank_metadata=genbank_metadata,
            provirus=provirus,
        )
        params = {
            "query": query,
            "is_accession": is_accession,
            "confirm_download": confirm_download,
            **filters,
        }

        result = run_virus_dataset(
            query=query,
            is_accession=is_accession,
            confirm_download=confirm_download,
            filters=filters,
        )

        accession_count = result["manifest"].get("accession_count")
        response = ToolResponse(
            tool="retrieve_virus_dataset",
            success=True,
            query={"type": "accession" if is_accession else "taxon", "value": query, **params},
            returned=accession_count if accession_count is not None else result["file_count"],
            output_dir=result["output_dir"],
            files=result["files"],
            manifest=result["manifest"],
            audit=build_audit(
                source="gget.virus",
                operation="dataset_download",
                params=params,
                extra={"file_count": result["file_count"]},
            ),
            message=(
                f"Dataset written to {result['output_dir']}. "
                f"{accession_count or 'Unknown'} accessions in manifest."
            ),
        )
        return response.to_dict()

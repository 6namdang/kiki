from kiki.audit.gget_provenance import build_dataset_execution_audit
from kiki.services.gget_virus import run_virus_dataset
from kiki.tools._errors import tool_safe
from kiki.tools._params import virus_filter_kwargs
from kiki.tools._response import build_query_params, extract_filters, success_manifest


def register_dataset_tools(mcp) -> None:
    @mcp.tool(name="retrieve_virus_dataset")
    @tool_safe
    def retrieve_virus_dataset_tool(
        query: str | None = None,
        is_accession: bool = False,
        preset: str | None = None,
        confirm_download: bool = False,
        download_all_accessions: bool = False,
        is_sars_cov2: bool = False,
        is_alphainfluenza: bool = False,
        outfolder: str | None = None,
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
        has_proteins: str | list[str] | None = None,
        proteins_complete: bool = False,
        lab_passaged: bool | None = None,
        submitter_country: str | None = None,
        min_mature_peptide_count: int | None = None,
        max_mature_peptide_count: int | None = None,
        min_protein_count: int | None = None,
        max_protein_count: int | None = None,
        max_ambiguous_chars: int | None = None,
        segment: str | list[str] | None = None,
        vaccine_strain: bool | None = None,
        source_database: str | None = None,
        lineage: str | list[str] | None = None,
        isolate: str | None = None,
        genotype: str | list[str] | None = None,
        isolation_source: str | None = None,
        env_source: str | list[str] | None = None,
        submitter_name: str | None = None,
        submitter_institution: str | None = None,
        gen_mol_type: str | None = None,
        genbank_metadata: bool = False,
        genbank_batch_size: int | None = None,
        provirus: bool | None = None,
        keep_temp: bool = False,
        verbose: bool = True,
    ) -> dict:
        """Retrieve a filtered virus sequence dataset via gget.virus.

        Wraps the full gget.virus pipeline (see gget_virus_docs.md): metadata filtering,
        pagination, sequence download, and local FASTA/CSV/JSONL output.

        Query may be a taxon name/ID, single accession, space-separated accessions, or a
        path to a text file of accessions (set is_accession=true for accession modes).

        Requires confirm_download=true. Large taxa require narrowing filters.
        download_all_accessions applies filters across all viral accessions (query ignored)
        and also requires narrowing filters.

        Use is_sars_cov2 / is_alphainfluenza for NCBI cached optimized downloads.
        Set verbose=false to suppress gget progress output.

        Always inspect dataset_manifest.failures and command_summary.txt — gget writes
        a FAILED OPERATIONS section when sequence or GenBank metadata batches fail.
        """
        params = build_query_params(
            preset=preset,
            query=query,
            is_accession=is_accession,
            download_all_accessions=download_all_accessions,
            confirm_download=confirm_download,
            **virus_filter_kwargs(
                is_sars_cov2=is_sars_cov2 or None,
                is_alphainfluenza=is_alphainfluenza or None,
                outfolder=outfolder,
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
                proteins_complete=proteins_complete or None,
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
                genbank_metadata=genbank_metadata or None,
                genbank_batch_size=genbank_batch_size,
                provirus=provirus,
                keep_temp=keep_temp or None,
                verbose=verbose,
                download_all_accessions=download_all_accessions or None,
            ),
        )
        if preset:
            params["preset"] = preset

        filters = extract_filters(params)
        result = run_virus_dataset(
            query=params.get("query", ""),
            is_accession=params.get("is_accession", False),
            confirm_download=confirm_download,
            filters=filters,
        )

        accession_count = result["manifest"].get("accession_count")
        failures = result["manifest"].get("failures", {})
        message = (
            f"Dataset written to {result['output_dir']}. "
            f"{accession_count or 'Unknown'} accessions in manifest."
        )
        if failures.get("detected"):
            message = f"{message} {failures['message']}"

        return success_manifest(
            tool="retrieve_virus_dataset",
            params=params,
            result={
                "returned": accession_count if accession_count is not None else result["file_count"],
                "output_dir": result["output_dir"],
                "files": result["files"],
                "dataset_manifest": result["manifest"],
                "failures": failures,
            },
            engine="gget.virus",
            operation="dataset_download",
            message=message,
            provenance_extra=build_dataset_execution_audit(
                filters=filters,
                dataset_manifest=result["manifest"],
            ),
        )

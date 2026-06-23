from datetime import UTC, datetime
from pathlib import Path

from kiki.errors import ErrorCode, KikiError
from kiki.query.genome import (
    normalize_accessions,
    validate_assembly_accession,
    validate_nucleotide_accession,
    validate_nucleotide_batch,
)
from kiki.services.ncbi_eutils import (
    fetch_assembly_summary,
    fetch_nucleotide_fasta,
    fetch_nucleotide_summary,
)
from kiki.services.ensembl import write_fasta
from kiki.services.output_paths import output_root as resolve_output_root
from kiki.tools._errors import tool_safe
from kiki.tools.genome._helpers import genome_success_manifest


def register_genome_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def get_nucleotide_sequence(accession: str) -> dict:
        """Fetch a nucleotide sequence by NCBI accession via E-utilities efetch.

        Deterministic lookup for GenBank/RefSeq accessions (e.g. NC_045512.2).
        Returns parsed FASTA inline (header, sequence, length). For filtered viral
        taxon queries with complex metadata filters, use count_virus_sequences or
        retrieve_virus_dataset instead.
        """
        accession = validate_nucleotide_accession(accession)
        params = {"accession": accession}
        records = fetch_nucleotide_fasta([accession])

        return genome_success_manifest(
            tool="get_nucleotide_sequence",
            params=params,
            query_type="ncbi_nucleotide_accession",
            query_value=accession,
            result={"returned": len(records), "records": records},
            engine="ncbi.eutils.efetch",
            operation="nucleotide_sequence",
            message=f"Retrieved nucleotide sequence for {accession} ({records[0]['length']} bp).",
        )

    @mcp.tool()
    @tool_safe
    def get_nucleotide_metadata(accession: str) -> dict:
        """Fetch nucleotide record metadata by accession via NCBI esummary.

        Returns title, length, organism, taxid, and update date without downloading
        the full sequence.
        """
        accession = validate_nucleotide_accession(accession)
        params = {"accession": accession}
        record = fetch_nucleotide_summary(accession)

        return genome_success_manifest(
            tool="get_nucleotide_metadata",
            params=params,
            query_type="ncbi_nucleotide_accession",
            query_value=accession,
            result={"record": record},
            engine="ncbi.eutils.esummary",
            operation="nucleotide_metadata",
            message=f"Retrieved metadata for nucleotide accession {accession}.",
        )

    @mcp.tool()
    @tool_safe
    def get_assembly_metadata(accession: str) -> dict:
        """Fetch genome assembly metadata by GCF/GCA accession via NCBI assembly esummary.

        Returns assembly name, organism, taxid, level, FTP path, and release date.
        Does not download sequence files.
        """
        accession = validate_assembly_accession(accession)
        params = {"accession": accession}
        record = fetch_assembly_summary(accession)

        return genome_success_manifest(
            tool="get_assembly_metadata",
            params=params,
            query_type="ncbi_assembly_accession",
            query_value=accession,
            result={"record": record},
            engine="ncbi.eutils.assembly",
            operation="assembly_metadata",
            message=f"Retrieved assembly metadata for {accession}.",
        )

    @mcp.tool()
    @tool_safe
    def retrieve_nucleotide_batch(
        accessions: list[str],
        confirm_download: bool = False,
        outfolder: str | None = None,
    ) -> dict:
        """Fetch multiple nucleotide sequences by accession via NCBI efetch (max 50).

        Returns parsed FASTA records inline. Pass confirm_download=true to also write
        a combined FASTA file to disk.
        """
        ids = validate_nucleotide_batch(normalize_accessions(accessions))
        params: dict = {"accessions": ids}
        if outfolder:
            params["outfolder"] = outfolder

        records = fetch_nucleotide_fasta(ids)
        result: dict = {
            "returned": len(records),
            "requested_accessions": len(ids),
            "records": records,
        }
        message = f"Retrieved {len(records)} nucleotide sequence(s) for {len(ids)} accession(s)."

        if confirm_download:
            if outfolder:
                out_dir = Path(outfolder).expanduser()
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                root, _ = resolve_output_root()
                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                out_dir = root / f"ncbi_nucleotide_{timestamp}"
                out_dir.mkdir(parents=True, exist_ok=True)

            fasta_path = out_dir / "sequences.fasta"
            write_fasta(records, fasta_path)
            result["output_dir"] = str(out_dir)
            result["files"] = [str(fasta_path)]
            result["fasta_path"] = str(fasta_path)
            params["confirm_download"] = True
            message += f" Wrote FASTA to {fasta_path}."
        elif outfolder:
            raise KikiError(
                ErrorCode.CONFIRM_DOWNLOAD_REQUIRED,
                "Pass confirm_download=true to write batch sequences to disk.",
            )

        return genome_success_manifest(
            tool="retrieve_nucleotide_batch",
            params=params,
            query_type="ncbi_nucleotide_batch",
            query_value=ids,
            result=result,
            engine="ncbi.eutils.efetch",
            operation="nucleotide_batch",
            message=message,
            provenance_extra={"requested_accessions": len(ids)},
        )

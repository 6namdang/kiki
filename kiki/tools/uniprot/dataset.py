import os
from datetime import UTC, datetime
from pathlib import Path

from kiki.config import DEFAULT_OUTPUT_ROOT
from kiki.services.uniprot import count_proteins, download_fasta_dataset
from kiki.tools._errors import tool_safe
from kiki.tools.uniprot._helpers import (
    build_uniprot_params,
    guard_uniprot_scope,
    resolve_uniprot_query,
    uniprot_success_manifest,
)
from kiki.errors import ErrorCode, KikiError


def _build_output_path(query_label: str, outfolder: str | None) -> Path:
    if outfolder:
        path = Path(outfolder).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path / "proteins.fasta"

    root = Path(os.environ.get("KIKI_OUTPUT_DIR", DEFAULT_OUTPUT_ROOT))
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe = "".join(char if char.isalnum() else "_" for char in query_label)[:40]
    out_dir = root / f"uniprot_{safe}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "proteins.fasta"


def register_uniprot_dataset_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def retrieve_protein_dataset(
        query: str | None = None,
        preset: str | None = None,
        confirm_download: bool = False,
        reviewed_only: bool = True,
        include_unreviewed: bool = False,
        organism_id: str | None = None,
        gene: str | None = None,
        protein_name: str | None = None,
        accession: str | None = None,
        length_min: int | None = None,
        length_max: int | None = None,
        outfolder: str | None = None,
    ) -> dict:
        """Download matching UniProtKB protein sequences as FASTA to disk.

        Paginates through all result pages via the UniProt REST API.
        Requires confirm_download=true. Defaults to reviewed:true.
        Returns file paths and sequence count.
        """
        if not confirm_download:
            raise KikiError(
                ErrorCode.CONFIRM_DOWNLOAD_REQUIRED,
                "Protein dataset retrieval writes FASTA to disk. Pass confirm_download=true.",
            )

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
            outfolder=outfolder,
            confirm_download=confirm_download,
        )
        uniprot_query = resolve_uniprot_query(params)
        guard_uniprot_scope(params, uniprot_query, "download a protein dataset")

        expected = count_proteins(uniprot_query)["count"]
        fasta_path = _build_output_path(uniprot_query, outfolder)
        download = download_fasta_dataset(uniprot_query, str(fasta_path))

        return uniprot_success_manifest(
            tool="retrieve_protein_dataset",
            params=params,
            uniprot_query=uniprot_query,
            result={
                "returned": download["sequence_count"],
                "expected_count": expected,
                "output_dir": str(fasta_path.parent),
                "files": [str(fasta_path)],
                "fasta_path": str(fasta_path),
            },
            operation="uniprot_dataset_download",
            message=(
                f"Wrote {download['sequence_count']} sequences to {fasta_path}. "
                f"Expected {expected} from UniProt count."
            ),
            provenance_extra={
                "pagination_complete": download["sequence_count"] >= expected or expected == 0,
            },
        )

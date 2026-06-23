from datetime import UTC, datetime
from pathlib import Path

from kiki.errors import ErrorCode, KikiError
from kiki.services.gget_ensembl import fetch_sequences, normalize_ensembl_ids, write_fasta
from kiki.services.output_paths import output_root as resolve_output_root
from kiki.tools._errors import tool_safe
from kiki.tools.ensembl._helpers import ensembl_success_manifest


def register_ensembl_sequence_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def get_sequence(
        ensembl_id: str,
        translate: bool = False,
        isoforms: bool = False,
        transcribe: bool | None = None,
        seqtype: str | None = None,
    ) -> dict:
        """Fetch nucleotide or amino acid sequence for one Ensembl gene/transcript ID.

        Wraps gget.seq with save=False — returns parsed FASTA inline (header, sequence, length).
        Supports Ensembl, WormBase, and FlyBase IDs. Set translate=true for amino acid sequences.
        Set isoforms=true to return all transcript isoforms for a gene ID.
        """
        ensembl_id = ensembl_id.strip()
        if not ensembl_id:
            raise KikiError(ErrorCode.INVALID_PARAMETER, "ensembl_id is required.")

        params = {
            "ensembl_id": ensembl_id,
            "translate": translate,
            "isoforms": isoforms,
        }
        if transcribe is not None:
            params["transcribe"] = transcribe
        if seqtype is not None:
            params["seqtype"] = seqtype

        records = fetch_sequences(
            ensembl_id,
            translate=translate,
            isoforms=isoforms,
            transcribe=transcribe,
            seqtype=seqtype,
        )

        return ensembl_success_manifest(
            tool="get_sequence",
            params=params,
            query_type="ensembl_id",
            query_value=ensembl_id,
            result={
                "returned": len(records),
                "records": records,
            },
            engine="gget.seq",
            operation="sequence_fetch",
            message=f"Retrieved {len(records)} sequence(s) for {ensembl_id}.",
        )

    @mcp.tool()
    @tool_safe
    def retrieve_sequence_batch(
        ensembl_ids: list[str],
        translate: bool = False,
        isoforms: bool = False,
        transcribe: bool | None = None,
        seqtype: str | None = None,
        confirm_download: bool = False,
        outfolder: str | None = None,
    ) -> dict:
        """Fetch sequences for multiple Ensembl IDs via gget.seq.

        Returns parsed FASTA records inline. When confirm_download=true, also writes a
        combined FASTA file to disk (KIKI_OUTPUT_DIR or outfolder).
        """
        from kiki.query.ensembl import validate_batch_size

        ids = normalize_ensembl_ids(ensembl_ids)
        validate_batch_size(ids)

        params: dict = {
            "ensembl_ids": ids,
            "translate": translate,
            "isoforms": isoforms,
        }
        if transcribe is not None:
            params["transcribe"] = transcribe
        if seqtype is not None:
            params["seqtype"] = seqtype
        if outfolder:
            params["outfolder"] = outfolder

        records = fetch_sequences(
            ids,
            translate=translate,
            isoforms=isoforms,
            transcribe=transcribe,
            seqtype=seqtype,
        )

        result: dict = {
            "returned": len(records),
            "requested_ids": len(ids),
            "records": records,
        }
        message = f"Retrieved {len(records)} sequence(s) for {len(ids)} Ensembl ID(s)."

        if confirm_download:
            if outfolder:
                out_dir = Path(outfolder).expanduser()
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                root, _ = resolve_output_root()
                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                out_dir = root / f"ensembl_batch_{timestamp}"
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

        return ensembl_success_manifest(
            tool="retrieve_sequence_batch",
            params=params,
            query_type="ensembl_batch",
            query_value=ids,
            result=result,
            engine="gget.seq",
            operation="sequence_batch",
            message=message,
            provenance_extra={"requested_ids": len(ids)},
        )

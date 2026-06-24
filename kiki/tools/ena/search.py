import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from kiki.errors import ErrorCode, KikiError
from kiki.query.ena import (
    validate_ena_accession,
    validate_ena_format,
    validate_ena_full_retrieval,
    validate_ena_query,
    validate_ena_result,
    validate_ena_scope,
    validate_preview_limit,
)
from kiki.services import ena as ena_service
from kiki.services.output_paths import output_root as resolve_output_root
from kiki.tools._errors import tool_safe
from kiki.tools.ena._helpers import ENA_PAGINATION_NOTE, ena_success_manifest


def _resolve_out_dir(label: str, outfolder: str | None) -> Path:
    if outfolder:
        path = Path(outfolder).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    root, _ = resolve_output_root()
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe = "".join(char if char.isalnum() else "_" for char in label)[:40]
    out_dir = root / f"ena_{safe}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def register_ena_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def count_ena_records(result: str, query: str) -> dict:
        """Count ENA records matching a Portal search, without downloading them.

        Uses the ENA Portal /count endpoint for a verifiable total. This is the
        deterministic way to size a query: the Portal /search default caps at 100000
        rows, which can look complete even when it is not.

        result: one of "sequence" (assembled/annotated nucleotide sequences, the
        direct parallel to NCBI Virus) or "read_run" (raw sequencing reads + FASTQ
        FTP links).

        query: an ENA Portal query string, e.g. `tax_eq(2697049)` or
        `tax_tree(11118) AND country="United Kingdom"`.
        """
        result = validate_ena_result(result)
        query = validate_ena_query(query)
        params = {"result": result, "query": query}

        count = ena_service.portal_count(result, query)
        return ena_success_manifest(
            tool="count_ena_records",
            params=params,
            query_type="ena_count",
            query_value=query,
            result={"result": result, "count": count, "pagination_complete": True},
            engine="ena.portal",
            operation="ena_count",
            message=f"Counted {count} ENA {result} record(s).",
            provenance_extra={"api_sequence": ["portal_count"]},
        )

    @mcp.tool()
    @tool_safe
    def search_ena_records(
        result: str,
        query: str,
        preview_limit: int | None = None,
    ) -> dict:
        """Preview ENA Portal search results (metadata only, no sequence download).

        Returns the verifiable total from Portal /count plus up to preview_limit
        inline metadata rows from Portal /search. pagination_complete is true only
        when the preview captured every matching row.

        Use this to inspect a query before a full retrieval. For sequences, the
        full FASTA/EMBL records come from retrieve_ena_dataset (which runs Portal
        first, then the Browser API). Do not call the ENA Browser search directly;
        Kiki coordinates the two APIs for you.

        result: "sequence" or "read_run".
        query: an ENA Portal query string (must include a narrowing filter such as
        tax_eq(<taxid>), tax_tree(<taxid>), or an accession field).
        """
        result = validate_ena_result(result)
        query = validate_ena_query(query)
        preview_limit = validate_preview_limit(preview_limit)
        validate_ena_scope(result, query, operation="search records")
        params = {"result": result, "query": query, "preview_limit": preview_limit}

        outcome = ena_service.search_ena_preview(result, query, preview_limit=preview_limit)
        return ena_success_manifest(
            tool="search_ena_records",
            params=params,
            query_type="ena_search",
            query_value=query,
            result={
                "result": result,
                "total_available": outcome["total_available"],
                "returned": outcome["returned"],
                "records": outcome["records"],
                "pagination_complete": outcome["pagination_complete"],
            },
            engine="ena.portal",
            operation="ena_search",
            message=(
                f"Found {outcome['total_available']} ENA {result} record(s); "
                f"returning {outcome['returned']} inline preview."
            ),
            provenance_extra={
                "api_sequence": outcome["api_sequence"],
                "pagination_complete": outcome["pagination_complete"],
                "pages_fetched": outcome["pages_fetched"],
                "pagination_note": ENA_PAGINATION_NOTE,
            },
        )

    @mcp.tool()
    @tool_safe
    def get_ena_sequence(accession: str, format: str = "fasta") -> dict:
        """Fetch one assembled/annotated ENA sequence by accession via the Browser API.

        This is the documented exception to the Portal-first workflow: when you
        already have a specific sequence accession (e.g. BN000065), the Browser API
        returns it directly with no Portal search needed.

        format: "fasta" (parsed records inline) or "embl" (EMBL flat file text).
        For discovery by taxon/country/etc., use search_ena_records first.
        """
        accession = validate_ena_accession(accession)
        fmt = validate_ena_format(format)
        params = {"accession": accession, "format": fmt}

        record = ena_service.browser_sequence_by_accession(accession, fmt=fmt)
        if fmt == "fasta":
            records = record["records"]
            result = {"format": "fasta", "returned": len(records), "records": records}
            message = f"Retrieved ENA FASTA for {accession} ({records[0]['length']} bp)."
        else:
            result = {"format": "embl", "content": record["content"]}
            message = f"Retrieved ENA EMBL flat file for {accession}."

        return ena_success_manifest(
            tool="get_ena_sequence",
            params=params,
            query_type="ena_accession",
            query_value=accession,
            result=result,
            engine="ena.browser",
            operation="ena_get_sequence",
            message=message,
            provenance_extra={"api_sequence": [f"browser_{fmt}"]},
        )

    @mcp.tool()
    @tool_safe
    def retrieve_ena_dataset(
        result: str,
        query: str,
        format: str = "fasta",
        confirm_download: bool = False,
        outfolder: str | None = None,
    ) -> dict:
        """Retrieve a full ENA dataset, coordinating Portal then Browser APIs.

        Hardcoded, deterministic workflow so agents never combine the APIs wrongly:
        - result="sequence": Portal /count -> Portal /search (limit=0, full set) ->
          Browser API download in 10000-accession chunks (FASTA or EMBL).
        - result="read_run": Portal /count -> Portal /search (limit=0) returning run
          metadata and FASTQ/submitted FTP links. No Browser step; FTP file transfer
          is out of scope (URLs are returned for downstream tooling).

        The Portal default 100000-row cap is never trusted: totals come from /count
        and the full set is fetched with limit=0.

        Pass confirm_download=true to (a) allow retrievals larger than the safety cap
        and (b) write the dataset to disk. Without it, large queries are refused and
        nothing is written.

        format: "fasta" or "embl" (sequence only; ignored for read_run).
        """
        result = validate_ena_result(result)
        query = validate_ena_query(query)
        fmt = validate_ena_format(format)
        validate_ena_scope(result, query, operation="retrieve a dataset")
        params = {"result": result, "query": query}
        if result == "sequence":
            params["format"] = fmt
        if outfolder:
            params["outfolder"] = outfolder

        count = ena_service.portal_count(result, query)
        validate_ena_full_retrieval(count, confirm_download=confirm_download)

        if result == "sequence":
            outcome = ena_service.retrieve_ena_sequences(query, fmt=fmt)
        else:
            outcome = ena_service.retrieve_ena_read_runs(query)

        message = (
            f"Retrieved {outcome['total_available']} ENA {result} record(s) "
            f"via {' -> '.join(outcome['api_sequence'])}."
        )

        if confirm_download:
            out_dir = _resolve_out_dir(query, outfolder)
            files = _write_dataset(out_dir, result, fmt, outcome)
            outcome["output_dir"] = str(out_dir)
            outcome["files"] = files
            params["confirm_download"] = True
            message += f" Wrote {len(files)} file(s) to {out_dir}."
        elif outfolder:
            raise KikiError(
                ErrorCode.CONFIRM_DOWNLOAD_REQUIRED,
                "Pass confirm_download=true to write the ENA dataset to disk.",
            )

        return ena_success_manifest(
            tool="retrieve_ena_dataset",
            params=params,
            query_type="ena_dataset",
            query_value=query,
            result=outcome,
            engine="ena.portal_browser",
            operation="ena_retrieve_dataset",
            message=message,
            provenance_extra={
                "api_sequence": outcome["api_sequence"],
                "pagination_complete": outcome["pagination_complete"],
                "pagination_note": ENA_PAGINATION_NOTE,
            },
        )


def _write_dataset(out_dir: Path, result: str, fmt: str, outcome: dict) -> list[str]:
    files: list[str] = []
    if result == "sequence" and fmt == "fasta":
        fasta_path = out_dir / "sequences.fasta"
        with open(fasta_path, "w", encoding="utf-8") as handle:
            for record in outcome.get("records", []):
                header = record["header"]
                handle.write(header if header.endswith("\n") else header + "\n")
                sequence = record["sequence"]
                for index in range(0, len(sequence), 80):
                    handle.write(sequence[index : index + 80] + "\n")
        files.append(str(fasta_path))
    elif result == "sequence" and fmt == "embl":
        embl_path = out_dir / "sequences.embl"
        embl_path.write_text(outcome.get("content", ""), encoding="utf-8")
        files.append(str(embl_path))
    else:
        records = outcome.get("records", [])
        json_path = out_dir / "read_runs.json"
        json_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        files.append(str(json_path))
        if records:
            tsv_path = out_dir / "read_runs.tsv"
            fieldnames = sorted({key for row in records for key in row})
            with open(tsv_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(records)
            files.append(str(tsv_path))
    return files

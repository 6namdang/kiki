import csv
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gget

from kiki.config import DEFAULT_OUTPUT_ROOT
from kiki.errors import ErrorCode, KikiError
from kiki.query.validate import validate_filters
from kiki.services.command_summary import parse_command_summary
from kiki.services.filters import validate_query_scope, virus_kwargs
from kiki.services.output_paths import output_root as resolve_output_root


def build_output_dir(root: Path, query: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    label = query.strip() or "all_accessions"
    safe_query = "".join(char if char.isalnum() else "_" for char in label)[:40]
    out_dir = root / f"{safe_query}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def resolve_outfolder(
    *,
    query: str,
    outfolder: str | None,
    output_root_override: Path | None,
) -> Path:
    if outfolder:
        path = Path(outfolder).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    root, _ = resolve_output_root()
    chosen = output_root_override if output_root_override is not None else root
    return build_output_dir(chosen, query)


def list_files(directory: Path) -> list[str]:
    return sorted(str(path) for path in directory.rglob("*") if path.is_file())


def _count_csv_rows(path: Path) -> int:
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def build_dataset_manifest(output_dir: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "accession_count": None,
        "artifacts": {},
        "failures": {"detected": False},
    }

    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue

        name = path.name.lower()

        if name.endswith("_metadata.csv") and "genbank" not in name and "merged" not in name:
            manifest["artifacts"]["metadata_csv"] = str(path)
            manifest["accession_count"] = _count_csv_rows(path)
        elif name.endswith("_metadata.jsonl"):
            manifest["artifacts"]["metadata_jsonl"] = str(path)
        elif name.endswith(".fasta") or name.endswith(".fa"):
            manifest["artifacts"]["fasta"] = str(path)
        elif name == "command_summary.txt":
            manifest["artifacts"]["command_summary"] = str(path)
            manifest["failures"] = parse_command_summary(path)
        elif name.endswith("_merged.csv"):
            manifest["artifacts"]["merged_metadata_csv"] = str(path)
        elif name.endswith("_genbank_metadata.csv"):
            manifest["artifacts"]["genbank_metadata_csv"] = str(path)
        elif name == "genbank_failed_batches.log":
            manifest["artifacts"]["genbank_failed_batches_log"] = str(path)

    return manifest


def run_virus_dataset(
    *,
    query: str,
    is_accession: bool = False,
    confirm_download: bool = False,
    output_root: Path | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run gget.virus with full filter support and return paths + manifest."""
    filters = filters or {}

    if not confirm_download:
        raise KikiError(
            ErrorCode.CONFIRM_DOWNLOAD_REQUIRED,
            "Dataset retrieval writes files to disk. Pass confirm_download=true.",
        )

    validate_filters(filters)
    validate_query_scope(
        query=query,
        is_accession=is_accession,
        filters=filters,
        operation="download a dataset",
    )

    outfolder = resolve_outfolder(
        query=query,
        outfolder=filters.get("outfolder"),
        output_root_override=output_root,
    )

    gget_args = virus_kwargs(filters)
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        gget_args["api_key"] = api_key

    gget.virus(
        query,
        is_accession=is_accession,
        outfolder=str(outfolder),
        **gget_args,
    )

    files = list_files(outfolder)
    manifest = build_dataset_manifest(outfolder)
    return {
        "output_dir": str(outfolder),
        "files": files,
        "file_count": len(files),
        "manifest": manifest,
    }

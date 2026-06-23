import csv
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gget

from kiki.config import DEFAULT_OUTPUT_ROOT
from kiki.services.filters import validate_query_scope, virus_kwargs


def build_output_dir(root: Path, query: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(char if char.isalnum() else "_" for char in query)[:40]
    out_dir = root / f"{safe_query}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


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
    }

    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue

        name = path.name.lower()
        rel = str(path.relative_to(output_dir))

        if name.endswith("_metadata.csv") and "genbank" not in name and "merged" not in name:
            manifest["artifacts"]["metadata_csv"] = str(path)
            manifest["accession_count"] = _count_csv_rows(path)
        elif name.endswith(".fasta") or name.endswith(".fa"):
            manifest["artifacts"]["fasta"] = str(path)
        elif name == "command_summary.txt":
            manifest["artifacts"]["command_summary"] = str(path)
        elif name.endswith("_merged.csv"):
            manifest["artifacts"]["merged_metadata_csv"] = str(path)
        elif name.endswith("_genbank_metadata.csv"):
            manifest["artifacts"]["genbank_metadata_csv"] = str(path)

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
        raise ValueError(
            "Dataset retrieval writes files to disk. "
            "Pass confirm_download=true only when you intend to download a dataset."
        )

    validate_query_scope(
        query=query,
        is_accession=is_accession,
        filters=filters,
        operation="download a dataset",
    )

    root = output_root or Path(os.environ.get("KIKI_OUTPUT_DIR", DEFAULT_OUTPUT_ROOT))
    outfolder = build_output_dir(root, query)

    gget.virus(
        query,
        is_accession=is_accession,
        outfolder=str(outfolder),
        **virus_kwargs(filters),
    )

    files = list_files(outfolder)
    manifest = build_dataset_manifest(outfolder)
    return {
        "output_dir": str(outfolder),
        "files": files,
        "file_count": len(files),
        "manifest": manifest,
    }

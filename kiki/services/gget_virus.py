import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gget

from kiki.config import DEFAULT_OUTPUT_ROOT, LARGE_TAXIDS

FILTER_KEYS = (
    "host",
    "min_seq_length",
    "max_seq_length",
    "geographic_location",
    "min_collection_date",
    "max_collection_date",
    "min_release_date",
    "max_release_date",
    "nuc_completeness",
    "source_database",
    "lineage",
    "isolate",
)


def _has_filter(filters: dict[str, Any]) -> bool:
    return any(filters.get(key) not in (None, "", False) for key in FILTER_KEYS)


def validate_dataset_request(
    *,
    query: str,
    is_accession: bool,
    confirm_download: bool,
    filters: dict[str, Any],
) -> None:
    if not confirm_download:
        raise ValueError(
            "Dataset retrieval writes files to disk. "
            "Pass confirm_download=true only when you intend to download a dataset."
        )

    if is_accession:
        return

    normalized = query.strip().lower()
    is_large = query in LARGE_TAXIDS or normalized in {"sars-cov-2", "sarscov2", "sars cov-2"}
    if is_large and not _has_filter(filters):
        raise ValueError(
            "This query targets a very large virus dataset. "
            "Add at least one filter (host, dates, location, sequence length, etc.) "
            "before downloading."
        )


def build_output_dir(root: Path, query: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(char if char.isalnum() else "_" for char in query)[:40]
    out_dir = root / f"{safe_query}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def list_files(directory: Path) -> list[str]:
    return sorted(str(path) for path in directory.rglob("*") if path.is_file())


def retrieve_virus_dataset(
    *,
    query: str,
    is_accession: bool = False,
    confirm_download: bool = False,
    output_root: Path | None = None,
    **filters: Any,
) -> dict[str, Any]:
    validate_dataset_request(
        query=query,
        is_accession=is_accession,
        confirm_download=confirm_download,
        filters=filters,
    )

    root = output_root or Path(os.environ.get("KIKI_OUTPUT_DIR", DEFAULT_OUTPUT_ROOT))
    outfolder = build_output_dir(root, query)

    kwargs = {key: value for key, value in filters.items() if value is not None}
    gget.virus(
        query,
        is_accession=is_accession,
        outfolder=str(outfolder),
        **kwargs,
    )

    files = list_files(outfolder)
    return {
        "output_dir": str(outfolder),
        "files": files,
        "file_count": len(files),
    }

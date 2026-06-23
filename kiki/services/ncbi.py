import json
import shutil
import tempfile
from pathlib import Path

from gget.gget_virus import fetch_virus_metadata

from kiki.config import MAX_METADATA_LIMIT
from kiki.query.validate import validate_filters
from kiki.services.filters import metadata_kwargs, validate_query_scope


def read_jsonl_records(path: str | Path, limit: int | None = None) -> list[dict]:
    records: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if limit is not None and len(records) >= limit:
                break
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def count_jsonl_records(path: str | Path) -> int:
    count = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def fetch_virus_metadata_query(
    *,
    query: str,
    is_accession: bool = False,
    preview_limit: int = MAX_METADATA_LIMIT,
    filters: dict | None = None,
) -> dict:
    """Fetch virus metadata via gget with full API pagination.

    Uses gget.gget_virus.fetch_virus_metadata so all pages are retrieved
    before returning. Only ``preview_limit`` records are included inline;
    total_fetched reports the complete paginated count.
    """
    filters = filters or {}
    validate_filters(filters)
    validate_query_scope(
        query=query,
        is_accession=is_accession,
        filters=filters,
        operation="fetch metadata",
    )

    preview_limit = min(max(0, preview_limit), MAX_METADATA_LIMIT)
    temp_dir = tempfile.mkdtemp(prefix="kiki_metadata_")
    try:
        temp_file, deferred_filters = fetch_virus_metadata(
            query,
            accession=is_accession,
            temp_output_dir=temp_dir,
            **metadata_kwargs(filters),
        )
        if not temp_file:
            return {
                "total_fetched": 0,
                "returned": 0,
                "records": [],
                "pagination_complete": True,
                "deferred_filters": deferred_filters,
            }

        total_fetched = count_jsonl_records(temp_file)
        records = read_jsonl_records(temp_file, preview_limit) if preview_limit > 0 else []
        return {
            "total_fetched": total_fetched,
            "returned": len(records),
            "records": records,
            "pagination_complete": True,
            "deferred_filters": deferred_filters,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

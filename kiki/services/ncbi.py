import json
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests
from gget.constants import NCBI_API_BASE
from gget.gget_virus import fetch_virus_metadata

from kiki.config import MAX_METADATA_LIMIT


def read_jsonl_records(path: str | Path, limit: int) -> list[dict]:
    records: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if len(records) >= limit:
                break
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def fetch_taxon_metadata_page(
    taxid: str,
    limit: int,
    host: str | None = None,
) -> dict:
    url = f"{NCBI_API_BASE}/virus/taxon/{quote(taxid, safe='')}/dataset_report"
    params = {"page_size": min(limit, MAX_METADATA_LIMIT)}
    if host:
        host_param = host.strip("\"'-_<|>`'").replace("-", "+").replace("_", "+").replace(" ", "+")
        params["filter.host"] = host_param

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    reports = data.get("reports", [])[:limit]
    return {
        "returned": len(reports),
        "total_available": data.get("total_count"),
        "records": reports,
    }


def fetch_accession_metadata(
    accession: str,
    host: str | None = None,
    limit: int = MAX_METADATA_LIMIT,
) -> list[dict]:
    temp_dir = tempfile.mkdtemp(prefix="kiki_mcp_")
    try:
        temp_file, _ = fetch_virus_metadata(
            accession,
            accession=True,
            host=host,
            temp_output_dir=temp_dir,
        )
        if not temp_file:
            return []
        return read_jsonl_records(temp_file, limit)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

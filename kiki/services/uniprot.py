"""UniProt REST API client (https://rest.uniprot.org)."""

from __future__ import annotations

import time
from typing import Any, Iterator
from urllib.parse import parse_qs, urlparse

import requests

from kiki.config import (
    UNIPROT_BASE_URL,
    UNIPROT_ID_MAPPING_POLL_INTERVAL,
    UNIPROT_ID_MAPPING_TIMEOUT,
    UNIPROT_MAX_PAGE_SIZE,
    UNIPROT_REQUEST_TIMEOUT,
)
from kiki.errors import ErrorCode, KikiError

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "kiki-mcp/0.1 (https://github.com/kiki)"})


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    accept_json: bool = True,
) -> requests.Response:
    url = f"{UNIPROT_BASE_URL}{path}"
    headers = {"Accept": "application/json"} if accept_json else {}
    try:
        response = SESSION.request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=UNIPROT_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "UniProt request failed.",
            details={"url": url, "error": str(exc)},
        ) from exc

    if response.status_code == 404:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            "UniProt entry not found.",
            details={"url": url, "status": 404},
        )
    if response.status_code >= 400:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"UniProt returned HTTP {response.status_code}.",
            details={"url": url, "body": response.text[:500]},
        )
    return response


def _parse_link_header(link: str | None) -> str | None:
    if not link:
        return None
    for part in link.split(","):
        section = part.strip()
        if 'rel="next"' in section:
            start = section.find("<") + 1
            end = section.find(">")
            return section[start:end]
    return None


def _cursor_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    values = parse_qs(parsed.query).get("cursor")
    return values[0] if values else None


def search_proteins(
    query: str,
    *,
    preview_limit: int = 10,
    fields: list[str] | None = None,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """Search UniProtKB with cursor pagination."""
    size = min(max(1, UNIPROT_MAX_PAGE_SIZE if fetch_all else preview_limit), UNIPROT_MAX_PAGE_SIZE)
    params: dict[str, Any] = {
        "query": query,
        "format": "json",
        "size": size,
    }
    if fields:
        params["fields"] = ",".join(fields)

    response = _request("GET", "/uniprotkb/search", params=params)
    total = int(response.headers.get("X-Total-Results", "0"))
    payload = response.json()
    records = payload.get("results", [])

    if fetch_all and total > len(records):
        cursor = _cursor_from_url(_parse_link_header(response.headers.get("Link")))
        while cursor and len(records) < total:
            page_params = {**params, "cursor": cursor}
            page = _request("GET", "/uniprotkb/search", params=page_params)
            page_payload = page.json()
            records.extend(page_payload.get("results", []))
            cursor = _cursor_from_url(_parse_link_header(page.headers.get("Link")))

    returned = min(len(records), preview_limit) if not fetch_all else len(records)
    preview = records[:preview_limit] if not fetch_all else records
    return {
        "total_available": total,
        "returned": returned,
        "records": _summarize_records(preview),
        "pagination_complete": len(records) >= total or total == 0,
    }


def count_proteins(query: str) -> dict[str, Any]:
    """Count matching entries using X-Total-Results (single request)."""
    response = _request(
        "GET",
        "/uniprotkb/search",
        params={"query": query, "format": "json", "size": 1},
    )
    total = int(response.headers.get("X-Total-Results", "0"))
    return {
        "count": total,
        "pagination_complete": True,
    }


def get_protein(accession: str, *, format: str = "json") -> dict[str, Any]:
    """Retrieve one UniProtKB entry by accession."""
    if format == "json":
        response = _request("GET", f"/uniprotkb/{accession}", params={"format": "json"})
        record = response.json()
        return {
            "accession": record.get("primaryAccession", accession),
            "record": _summarize_record(record),
            "raw_available": True,
        }

    response = _request(
        "GET",
        f"/uniprotkb/{accession}.{format}",
        accept_json=False,
    )
    return {
        "accession": accession,
        "format": format,
        "content": response.text,
    }


def iter_fasta_pages(query: str) -> Iterator[str]:
    """Yield FASTA text pages for a query."""
    params: dict[str, Any] = {
        "query": query,
        "format": "fasta",
        "size": UNIPROT_MAX_PAGE_SIZE,
    }
    response = _request("GET", "/uniprotkb/search", params=params, accept_json=False)
    if response.text.strip():
        yield response.text

    cursor = _cursor_from_url(_parse_link_header(response.headers.get("Link")))
    while cursor:
        page = _request(
            "GET",
            "/uniprotkb/search",
            params={**params, "cursor": cursor},
            accept_json=False,
        )
        if page.text.strip():
            yield page.text
        cursor = _cursor_from_url(_parse_link_header(page.headers.get("Link")))


def download_fasta_dataset(query: str, output_path: str) -> dict[str, Any]:
    """Download all FASTA records for a query to a file."""
    sequence_count = 0
    with open(output_path, "w", encoding="utf-8") as handle:
        for page in iter_fasta_pages(query):
            if not page.endswith("\n"):
                page += "\n"
            handle.write(page)
            sequence_count += page.count("\n>")

    return {
        "fasta_path": output_path,
        "sequence_count": sequence_count,
    }


def map_protein_ids(
    *,
    ids: list[str],
    from_db: str,
    to_db: str,
) -> dict[str, Any]:
    """Run UniProt ID mapping job and return mapped pairs."""
    if not ids:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Provide at least one id to map.",
        )
    if len(ids) > 5000:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Maximum 5000 ids per mapping job.",
            details={"provided": len(ids)},
        )

    response = _request(
        "POST",
        "/idmapping/run",
        data={"from": from_db, "to": to_db, "ids": ",".join(ids)},
        accept_json=True,
    )
    job_id = response.json()["jobId"]

    deadline = time.monotonic() + UNIPROT_ID_MAPPING_TIMEOUT
    status_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        status_response = _request("GET", f"/idmapping/status/{job_id}")
        status_payload = status_response.json()
        status = status_payload.get("jobStatus")
        if status == "FINISHED" or "results" in status_payload:
            break
        if status in {"FAILED", "ERROR"}:
            raise KikiError(
                ErrorCode.UPSTREAM_ERROR,
                "UniProt ID mapping job failed.",
                details={"job_id": job_id, "status": status},
            )
        time.sleep(UNIPROT_ID_MAPPING_POLL_INTERVAL)
    else:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "UniProt ID mapping job timed out.",
            details={"job_id": job_id},
        )

    if "results" in status_payload:
        mappings = status_payload["results"]
        return {
            "job_id": job_id,
            "from_db": from_db,
            "to_db": to_db,
            "mapped_count": len(mappings),
            "mappings": mappings,
            "failed": status_payload.get("failed", []),
        }

    results_response = _request(
        "GET",
        f"/idmapping/results/{job_id}",
        params={"format": "json"},
    )
    payload = results_response.json()
    mappings = payload.get("results", payload.get("mapped", []))
    return {
        "job_id": job_id,
        "from_db": from_db,
        "to_db": to_db,
        "mapped_count": len(mappings),
        "mappings": mappings,
        "failed": payload.get("failed", []),
    }


def list_id_mapping_fields() -> dict[str, Any]:
    """Return supported ID mapping database fields."""
    response = _request("GET", "/configure/idmapping/fields")
    return response.json()


def _gene_names(record: dict[str, Any]) -> list[str]:
    genes = record.get("genes") or []
    names: list[str] = []
    for gene in genes:
        if gene.get("geneName", {}).get("value"):
            names.append(gene["geneName"]["value"])
        for synonym in gene.get("synonyms") or []:
            if synonym.get("value"):
                names.append(synonym["value"])
    return names


def _protein_name(record: dict[str, Any]) -> str | None:
    description = record.get("proteinDescription") or {}
    recommended = description.get("recommendedName") or {}
    full_name = recommended.get("fullName") or {}
    if full_name.get("value"):
        return full_name["value"]
    submission = description.get("submissionNames") or []
    if submission:
        return submission[0].get("fullName", {}).get("value")
    return None


def _organism_name(record: dict[str, Any]) -> str | None:
    organism = record.get("organism") or {}
    return organism.get("scientificName") or organism.get("commonName")


def _summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    sequence = record.get("sequence") or {}
    return {
        "accession": record.get("primaryAccession"),
        "uniProtkbId": record.get("uniProtkbId"),
        "protein_name": _protein_name(record),
        "gene_names": _gene_names(record),
        "organism": _organism_name(record),
        "organism_id": (record.get("organism") or {}).get("taxonId"),
        "length": sequence.get("length"),
        "reviewed": (record.get("entryType") or "").endswith("Swiss-Prot"),
    }


def _summarize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_summarize_record(record) for record in records]

"""ENA Portal + Browser API client.

Two coordinated APIs (https://ena-docs.readthedocs.io/en/latest/retrieval/programmatic-access.html):

- Portal API (``/ena/portal/api``): search/discovery — returns accessions + metadata rows.
- Browser API (``/ena/browser/api``): record download — FASTA / EMBL flat file by accession.

The hardcoded order for sequence retrieval is Portal search (``limit=0`` for the full set)
then Browser download in 10000-accession chunks, so agents never combine the APIs wrongly
or trust the silent 100000-row Portal default cap as if it were the complete result.
"""

from __future__ import annotations

import io
import threading
import time
from typing import Any

import requests

from kiki.config import (
    ENA_BROWSER_BASE,
    ENA_BROWSER_BATCH_SIZE,
    ENA_MIN_INTERVAL,
    ENA_PORTAL_BASE,
    ENA_REQUEST_TIMEOUT,
)
from kiki.errors import ErrorCode, KikiError
from kiki.services.pagination import pagination_meta

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "kiki-mcp/0.1 (https://github.com/kiki)"})

_ENA_LOCK = threading.Lock()
_LAST_ENA_REQUEST_AT = 0.0

# Default Portal return fields per result type (accession is always included by ENA).
DEFAULT_FIELDS = {
    "sequence": ["accession", "description", "scientific_name", "tax_id", "base_count"],
    "read_run": [
        "run_accession",
        "sample_accession",
        "study_accession",
        "scientific_name",
        "tax_id",
        "instrument_platform",
        "library_strategy",
        "fastq_ftp",
        "submitted_ftp",
    ],
}


def _ena_get(url: str, *, params: dict[str, Any] | None = None) -> requests.Response:
    global _LAST_ENA_REQUEST_AT
    with _ENA_LOCK:
        elapsed = time.monotonic() - _LAST_ENA_REQUEST_AT
        if elapsed < ENA_MIN_INTERVAL:
            time.sleep(ENA_MIN_INTERVAL - elapsed)
        try:
            response = SESSION.get(url, params=params, timeout=ENA_REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise KikiError(
                ErrorCode.UPSTREAM_ERROR,
                "ENA request failed.",
                details={"url": url, "error": str(exc)},
            ) from exc
        _LAST_ENA_REQUEST_AT = time.monotonic()

    if response.status_code == 404:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            "ENA record not found.",
            details={"url": url, "status": 404},
        )
    if response.status_code == 429:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "ENA rate limit exceeded (HTTP 429). Reduce request frequency and retry.",
            details={"url": url},
        )
    if response.status_code >= 400:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"ENA returned HTTP {response.status_code}.",
            details={"url": url, "body": response.text[:500]},
        )
    return response


# --- Portal API ---------------------------------------------------------------


def portal_count(result: str, query: str) -> int:
    """Count rows matching a Portal search via the dedicated /count endpoint.

    ENA returns the count as JSON when ``format=json`` is requested; older/plain
    responses are a TSV with a ``count`` header line followed by the number.
    """
    response = _ena_get(
        f"{ENA_PORTAL_BASE}/count",
        params={"result": result, "query": query, "format": "json"},
    )
    text = response.text.strip()
    try:
        payload = response.json()
        count = payload.get("count") if isinstance(payload, dict) else None
        if count is not None:
            return int(count)
    except ValueError:
        pass
    # Fallback: plain text — last non-empty token that is an integer.
    for token in reversed(text.splitlines()):
        token = token.strip()
        if token.isdigit():
            return int(token)
    raise KikiError(
        ErrorCode.UPSTREAM_ERROR,
        "Failed to parse ENA Portal /count response.",
        details={"result": result, "query": query, "body": text[:200]},
    )


def portal_search(
    result: str,
    query: str,
    *,
    fields: list[str] | None = None,
    limit: int,
) -> list[dict[str, Any]]:
    """Search the Portal API and return JSON rows.

    ``limit=0`` retrieves the full set (ENA streams large result sets). Any other
    positive value caps the rows returned (used for previews).
    """
    field_list = fields if fields is not None else DEFAULT_FIELDS.get(result)
    params: dict[str, Any] = {
        "result": result,
        "query": query,
        "format": "json",
        "limit": limit,
    }
    if field_list:
        params["fields"] = ",".join(field_list)

    response = _ena_get(f"{ENA_PORTAL_BASE}/search", params=params)
    text = response.text.strip()
    if not text:
        return []
    try:
        payload = response.json()
    except ValueError as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "Failed to parse ENA Portal /search JSON response.",
            details={"result": result, "query": query, "body": text[:200]},
        ) from exc
    if not isinstance(payload, list):
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "Unexpected ENA Portal /search payload (expected a JSON array).",
            details={"result": result, "query": query, "body": text[:200]},
        )
    return payload


# --- Browser API --------------------------------------------------------------


def _parse_browser_fasta(text: str) -> list[dict[str, Any]]:
    """Parse a multi-record FASTA blob into header/sequence/length records."""
    records: list[dict[str, Any]] = []
    header: str | None = None
    sequence_parts: list[str] = []
    for line in io.StringIO(text):
        line = line.rstrip("\n")
        if line.startswith(">"):
            if header is not None:
                seq = "".join(sequence_parts)
                records.append({"header": header, "sequence": seq, "length": len(seq)})
            header = line
            sequence_parts = []
        elif line.strip():
            sequence_parts.append(line.strip())
    if header is not None:
        seq = "".join(sequence_parts)
        records.append({"header": header, "sequence": seq, "length": len(seq)})
    return records


def browser_sequence_by_accession(accession: str, *, fmt: str = "fasta") -> dict[str, Any]:
    """Fetch one assembled/annotated sequence record by accession (Browser API)."""
    response = _ena_get(f"{ENA_BROWSER_BASE}/{fmt}/{accession}")
    text = response.text.strip()
    if not text:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"ENA returned no {fmt} record for accession {accession}.",
            details={"accession": accession, "format": fmt},
        )
    if fmt == "fasta":
        records = _parse_browser_fasta(text)
        if not records:
            raise KikiError(
                ErrorCode.NOT_FOUND,
                f"Failed to parse ENA FASTA for accession {accession}.",
                details={"accession": accession},
            )
        return {"format": "fasta", "records": records}
    return {"format": fmt, "content": text}


def browser_fasta_batch(accessions: list[str]) -> dict[str, Any]:
    """Download FASTA for many accessions in 10000-accession chunks (Browser cap)."""
    records: list[dict[str, Any]] = []
    requests_made = 0
    for start in range(0, len(accessions), ENA_BROWSER_BATCH_SIZE):
        chunk = accessions[start : start + ENA_BROWSER_BATCH_SIZE]
        response = _ena_get(f"{ENA_BROWSER_BASE}/fasta/{','.join(chunk)}")
        requests_made += 1
        records.extend(_parse_browser_fasta(response.text))
    return {"records": records, "requests_made": requests_made}


def browser_embl_batch(accessions: list[str]) -> dict[str, Any]:
    """Download EMBL flat files for many accessions in 10000-accession chunks."""
    chunks: list[str] = []
    requests_made = 0
    for start in range(0, len(accessions), ENA_BROWSER_BATCH_SIZE):
        chunk = accessions[start : start + ENA_BROWSER_BATCH_SIZE]
        response = _ena_get(f"{ENA_BROWSER_BASE}/embl/{','.join(chunk)}")
        requests_made += 1
        if response.text.strip():
            chunks.append(response.text)
    return {"content": "\n".join(chunks), "requests_made": requests_made}


# --- Orchestrated flows -------------------------------------------------------


def search_ena_preview(
    result: str,
    query: str,
    *,
    fields: list[str] | None = None,
    preview_limit: int,
) -> dict[str, Any]:
    """Portal /count then a capped Portal /search preview.

    Never relies on the silent 100000-row default: total_available comes from /count,
    and pagination_complete reflects whether the preview captured every row.
    """
    total = portal_count(result, query)
    rows = portal_search(result, query, fields=fields, limit=preview_limit)
    meta = pagination_meta(
        total_available=total,
        retrieved=len(rows),
        pages_fetched=1,
        complete=total <= preview_limit,
    )
    return {
        "result": result,
        "total_available": total,
        "returned": len(rows),
        "records": rows,
        **meta,
        "api_sequence": ["portal_count", "portal_search"],
    }


def _accession_key(result: str) -> str:
    return "run_accession" if result == "read_run" else "accession"


def _extract_accessions(rows: list[dict[str, Any]], result: str) -> list[str]:
    key = _accession_key(result)
    accessions: list[str] = []
    for row in rows:
        value = row.get(key) or row.get("accession")
        if value:
            accessions.append(str(value))
    return accessions


def retrieve_ena_sequences(
    query: str,
    *,
    fields: list[str] | None = None,
    fmt: str = "fasta",
) -> dict[str, Any]:
    """Full sequence retrieval: Portal search (limit=0) -> Browser download in 10k chunks."""
    total = portal_count("sequence", query)
    rows = portal_search("sequence", query, fields=fields, limit=0)
    accessions = _extract_accessions(rows, "sequence")

    if fmt == "embl":
        download = browser_embl_batch(accessions)
        payload_records: list[dict[str, Any]] | None = None
        content: str | None = download["content"]
        retrieved = content.count("\nID ") + (1 if content.startswith("ID ") else 0)
    else:
        download = browser_fasta_batch(accessions)
        payload_records = download["records"]
        content = None
        retrieved = len(payload_records)

    meta = pagination_meta(
        total_available=total,
        retrieved=len(accessions),
        pages_fetched=1,
        complete=len(accessions) >= total,
    )
    result: dict[str, Any] = {
        "result": "sequence",
        "format": fmt,
        "total_available": total,
        "accession_count": len(accessions),
        "accessions": accessions,
        "downloaded": retrieved,
        **meta,
        "browser_requests": download["requests_made"],
        "api_sequence": ["portal_count", "portal_search", f"browser_{fmt}"],
    }
    if payload_records is not None:
        result["records"] = payload_records
    if content is not None:
        result["content"] = content
    return result


def retrieve_ena_read_runs(
    query: str,
    *,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Full read_run metadata retrieval via Portal search (limit=0). No Browser step.

    Returns run metadata including FASTQ/submitted FTP links; actual file transfer
    over FTP is out of scope (URLs are returned for downstream tooling).
    """
    total = portal_count("read_run", query)
    rows = portal_search("read_run", query, fields=fields, limit=0)
    meta = pagination_meta(
        total_available=total,
        retrieved=len(rows),
        pages_fetched=1,
        complete=len(rows) >= total,
    )
    return {
        "result": "read_run",
        "total_available": total,
        "returned": len(rows),
        "records": rows,
        **meta,
        "api_sequence": ["portal_count", "portal_search"],
    }

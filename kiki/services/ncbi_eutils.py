"""NCBI E-utilities client for deterministic nucleotide and assembly lookups."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

import requests

from kiki.config import (
    NCBI_EUTILS_BASE,
    NCBI_EUTILS_MIN_INTERVAL,
    NCBI_EUTILS_MIN_INTERVAL_WITH_KEY,
    NCBI_EUTILS_TIMEOUT,
)
from kiki.errors import ErrorCode, KikiError
from kiki.services.ensembl import parse_fasta_blocks

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "kiki-mcp/0.1 (https://github.com/kiki)"})

_EUTILS_LOCK = threading.Lock()
_LAST_EUTILS_REQUEST_AT = 0.0


def _eutils_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = dict(extra or {})
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def _eutils_get(endpoint: str, *, params: dict[str, Any]) -> requests.Response:
    global _LAST_EUTILS_REQUEST_AT
    url = f"{NCBI_EUTILS_BASE}/{endpoint}"
    min_interval = (
        NCBI_EUTILS_MIN_INTERVAL_WITH_KEY
        if os.environ.get("NCBI_API_KEY")
        else NCBI_EUTILS_MIN_INTERVAL
    )
    with _EUTILS_LOCK:
        elapsed = time.monotonic() - _LAST_EUTILS_REQUEST_AT
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        try:
            response = SESSION.get(
                url,
                params=_eutils_params(params),
                timeout=NCBI_EUTILS_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise KikiError(
                ErrorCode.UPSTREAM_ERROR,
                "NCBI E-utilities request failed.",
                details={"url": url, "error": str(exc)},
            ) from exc
        _LAST_EUTILS_REQUEST_AT = time.monotonic()

    if response.status_code >= 400:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"NCBI E-utilities returned HTTP {response.status_code}.",
            details={"url": url, "body": response.text[:500]},
        )
    return response


def _parse_fasta_text(text: str) -> list[dict[str, Any]]:
    blocks = [block for block in text.strip().split("\n") if block.strip()]
    if not blocks:
        raise KikiError(ErrorCode.NOT_FOUND, "No sequence returned from NCBI.")
    # parse_fasta_blocks expects header and sequence as separate list items when split by line
    lines = text.strip().splitlines()
    blocks_for_parser: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.startswith(">") and current:
            blocks_for_parser.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks_for_parser.append("\n".join(current))
    return parse_fasta_blocks(blocks_for_parser)


def fetch_nucleotide_fasta(accessions: list[str]) -> list[dict[str, Any]]:
    """Fetch nucleotide FASTA for one or more accessions via efetch."""
    response = _eutils_get(
        "efetch.fcgi",
        params={
            "db": "nucleotide",
            "id": ",".join(accessions),
            "rettype": "fasta",
            "retmode": "text",
        },
    )
    text = response.text.strip()
    if not text or text.startswith("Error"):
        raise KikiError(
            ErrorCode.NOT_FOUND,
            "NCBI returned no nucleotide sequence for the requested accession(s).",
            details={"accessions": accessions},
        )
    records = _parse_fasta_text(text)
    if not records:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            "Failed to parse nucleotide FASTA from NCBI.",
            details={"accessions": accessions},
        )
    return records


def fetch_nucleotide_summary(accession: str) -> dict[str, Any]:
    """Fetch nucleotide record summary via esummary."""
    response = _eutils_get(
        "esummary.fcgi",
        params={"db": "nucleotide", "id": accession, "retmode": "json"},
    )
    payload = response.json()
    uids = payload.get("result", {}).get("uids", [])
    if not uids:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"Nucleotide accession not found: {accession}.",
            details={"accession": accession},
        )
    uid = uids[0]
    record = payload.get("result", {}).get(uid)
    if not record or record.get("error"):
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"Nucleotide accession not found: {accession}.",
            details={"accession": accession},
        )
    return {
        "accession": record.get("accessionversion") or accession,
        "title": record.get("title"),
        "length": record.get("slen"),
        "moltype": record.get("moltype"),
        "organism": record.get("organism"),
        "taxid": record.get("taxid"),
        "genbank_division": record.get("genbankdivision"),
        "update_date": record.get("updatedate"),
    }


def _assembly_uid(accession: str) -> str:
    response = _eutils_get(
        "esearch.fcgi",
        params={"db": "assembly", "term": accession, "retmode": "json"},
    )
    payload = response.json()
    idlist = payload.get("esearchresult", {}).get("idlist", [])
    if not idlist:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"Assembly accession not found: {accession}.",
            details={"accession": accession},
        )
    return idlist[0]


def fetch_assembly_summary(accession: str) -> dict[str, Any]:
    """Fetch assembly metadata via esearch + esummary."""
    uid = _assembly_uid(accession)
    response = _eutils_get(
        "esummary.fcgi",
        params={"db": "assembly", "id": uid, "retmode": "json"},
    )
    payload = response.json()
    record = payload.get("result", {}).get(uid)
    if not record:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"Assembly accession not found: {accession}.",
            details={"accession": accession},
        )
    return {
        "accession": record.get("assemblyaccession") or accession,
        "assembly_name": record.get("assemblyname"),
        "organism": record.get("organism"),
        "taxid": record.get("taxid"),
        "species_taxid": record.get("speciestaxid"),
        "assembly_level": record.get("assemblytype"),
        "submitter": record.get("submitter"),
        "release_date": record.get("releasedate"),
        "refseq_category": record.get("refseq_category"),
        "paired_assembly": record.get("pairasmblyacc"),
        "ftp_path": record.get("ftppath_refseq") or record.get("ftppath_genbank"),
    }

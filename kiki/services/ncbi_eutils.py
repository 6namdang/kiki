"""NCBI E-utilities client for deterministic nucleotide and assembly lookups."""

from __future__ import annotations

import os
import re
import threading
import time
import xml.etree.ElementTree as ET
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
from kiki.services.pagination import pagination_meta

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "kiki-mcp/0.1 (https://github.com/kiki)"})

_EUTILS_LOCK = threading.Lock()
_LAST_EUTILS_REQUEST_AT = 0.0

WEBENV_RE = re.compile(r"<WebEnv>([^<]+)</WebEnv>")
QUERYKEY_RE = re.compile(r"<QueryKey>([^<]+)</QueryKey>")


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


def _parse_epost_response(text: str) -> tuple[str, str]:
    webenv_match = WEBENV_RE.search(text)
    query_key_match = QUERYKEY_RE.search(text)
    if webenv_match and query_key_match:
        return webenv_match.group(1), query_key_match.group(1)
    try:
        root = ET.fromstring(text)
        webenv = root.findtext("WebEnv")
        query_key = root.findtext("QueryKey")
        if webenv and query_key:
            return webenv, query_key
    except ET.ParseError:
        pass
    raise KikiError(
        ErrorCode.UPSTREAM_ERROR,
        "Failed to parse NCBI epost response (WebEnv / QueryKey).",
        details={"response_preview": text[:500]},
    )


def _epost_ids(db: str, ids: list[str]) -> tuple[str, str]:
    """Upload record IDs to the NCBI history server (epost)."""
    response = _eutils_get(
        "epost.fcgi",
        params={"db": db, "id": ",".join(ids)},
    )
    return _parse_epost_response(response.text)


def _efetch_from_history(
    *,
    db: str,
    webenv: str,
    query_key: str,
    rettype: str,
    retmode: str,
) -> str:
    response = _eutils_get(
        "efetch.fcgi",
        params={
            "db": db,
            "query_key": query_key,
            "WebEnv": webenv,
            "rettype": rettype,
            "retmode": retmode,
        },
    )
    return response.text


def _parse_fasta_text(text: str) -> list[dict[str, Any]]:
    if not text.strip():
        raise KikiError(ErrorCode.NOT_FOUND, "No sequence returned from NCBI.")
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


def fetch_nucleotide_fasta(accessions: list[str]) -> dict[str, Any]:
    """Fetch nucleotide FASTA via epost → efetch (NCBI-recommended batch order)."""
    webenv, query_key = _epost_ids("nucleotide", accessions)
    text = _efetch_from_history(
        db="nucleotide",
        webenv=webenv,
        query_key=query_key,
        rettype="fasta",
        retmode="text",
    ).strip()
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
    meta = pagination_meta(
        total_available=len(accessions),
        retrieved=len(records),
        pages_fetched=1,
        complete=len(records) >= len(accessions),
    )
    return {
        "records": records,
        "api_sequence": ["epost", "efetch"],
        **meta,
    }


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
        "api_sequence": ["esummary"],
        "pagination_complete": True,
        "pages_fetched": 1,
    }


def _assembly_uid(accession: str) -> str:
    response = _eutils_get(
        "esearch.fcgi",
        params={
            "db": "assembly",
            "term": f"{accession}[Assembly Accession]",
            "retmax": 1,
            "retmode": "json",
        },
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
    """Fetch assembly metadata via esearch → esummary."""
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
        "api_sequence": ["esearch", "esummary"],
        "pagination_complete": True,
        "pages_fetched": 2,
    }

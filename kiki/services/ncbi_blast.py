"""NCBI BLAST Common URL API client."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any

import requests

from kiki.config import (
    NCBI_BLAST_BASE,
    NCBI_BLAST_MIN_INTERVAL,
    NCBI_BLAST_TIMEOUT,
    NCBI_BLAST_TOOL_ID,
)
from kiki.errors import ErrorCode, KikiError

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "kiki-mcp/0.1 (https://github.com/kiki)"})

_BLAST_LOCK = threading.Lock()
_LAST_BLAST_REQUEST_AT = 0.0

RID_RE = re.compile(r"RID\s*=\s*(\S+)", re.IGNORECASE)
RTOE_RE = re.compile(r"RTOE\s*=\s*(\d+)", re.IGNORECASE)
STATUS_RE = re.compile(r"Status\s*=\s*(\w+)", re.IGNORECASE)
HITS_RE = re.compile(r"ThereAreHits\s*=\s*(\w+)", re.IGNORECASE)

BLAST_STATUS_RUNNING = frozenset({"WAITING", "SEARCHING", "QUEUED"})
BLAST_STATUS_READY = frozenset({"READY"})
BLAST_STATUS_FAILED = frozenset({"FAILED", "UNKNOWN"})


def _blast_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "tool": NCBI_BLAST_TOOL_ID,
        **(extra or {}),
    }
    email = os.environ.get("NCBI_BLAST_EMAIL")
    if email:
        params["email"] = email
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def _blast_get(params: dict[str, Any]) -> requests.Response:
    global _LAST_BLAST_REQUEST_AT
    with _BLAST_LOCK:
        elapsed = time.monotonic() - _LAST_BLAST_REQUEST_AT
        if elapsed < NCBI_BLAST_MIN_INTERVAL:
            time.sleep(NCBI_BLAST_MIN_INTERVAL - elapsed)
        try:
            response = SESSION.get(
                NCBI_BLAST_BASE,
                params=_blast_params(params),
                timeout=NCBI_BLAST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise KikiError(
                ErrorCode.UPSTREAM_ERROR,
                "NCBI BLAST request failed.",
                details={"url": NCBI_BLAST_BASE, "error": str(exc)},
            ) from exc
        _LAST_BLAST_REQUEST_AT = time.monotonic()

    if response.status_code >= 400:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"NCBI BLAST returned HTTP {response.status_code}.",
            details={"url": NCBI_BLAST_BASE, "body": response.text[:500]},
        )
    return response


def _parse_rid_response(text: str) -> tuple[str, int | None]:
    rid_match = RID_RE.search(text)
    if not rid_match:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "NCBI BLAST did not return a Request ID (RID). The service may be unavailable or the query was rejected.",
            details={"response_preview": text[:500]},
        )
    rid = rid_match.group(1).strip()
    rtoe_match = RTOE_RE.search(text)
    rtoe = int(rtoe_match.group(1)) if rtoe_match else None
    return rid, rtoe


def parse_blast_status(text: str) -> tuple[str, bool | None]:
    """Return (ncbi_status, there_are_hits) where hits may be None if not reported."""
    status_match = STATUS_RE.search(text)
    if not status_match:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "Could not parse BLAST job status from NCBI response.",
            details={"response_preview": text[:500]},
        )
    status = status_match.group(1).upper()
    hits_match = HITS_RE.search(text)
    there_are_hits: bool | None = None
    if hits_match:
        there_are_hits = hits_match.group(1).lower() == "yes"
    return status, there_are_hits


def submit_blast_search(
    *,
    program: str,
    query: str,
    database: str,
    expect: float | None = None,
    hitlist_size: int | None = None,
    word_size: int | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    """Submit a BLAST search (CMD=Put) and return RID + estimated wait."""
    params: dict[str, Any] = {
        "CMD": "Put",
        "PROGRAM": program,
        "QUERY": query,
        "DATABASE": database,
        "FORMAT_TYPE": "JSON2",
    }
    if expect is not None:
        params["EXPECT"] = expect
    if hitlist_size is not None:
        params["HITLIST_SIZE"] = hitlist_size
    if word_size is not None:
        params["WORD_SIZE"] = word_size
    if filter_value is not None:
        params["FILTER"] = filter_value

    response = _blast_get(params)
    rid, rtoe = _parse_rid_response(response.text)
    return {
        "rid": rid,
        "rtoe_seconds": rtoe,
        "program": program,
        "database": database,
    }


def get_blast_job_status(rid: str) -> dict[str, Any]:
    """Poll BLAST job status once (CMD=Get, FORMAT_OBJECT=SearchInfo)."""
    response = _blast_get(
        {
            "CMD": "Get",
            "FORMAT_OBJECT": "SearchInfo",
            "RID": rid,
        }
    )
    ncbi_status, there_are_hits = parse_blast_status(response.text)
    return {
        "ncbi_status": ncbi_status,
        "there_are_hits": there_are_hits,
    }


def fetch_blast_results_json(rid: str) -> dict[str, Any]:
    """Fetch JSON2 BLAST report for a completed job."""
    response = _blast_get(
        {
            "CMD": "Get",
            "RID": rid,
            "FORMAT_TYPE": "JSON2",
        }
    )
    text = response.text.strip()
    if not text:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "NCBI BLAST returned an empty result payload.",
            details={"rid": rid},
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "Failed to parse NCBI BLAST JSON2 response.",
            details={"rid": rid, "preview": text[:500]},
        ) from exc


def _best_hsp(hsps: list[dict[str, Any]]) -> dict[str, Any]:
    return min(hsps, key=lambda hsp: hsp.get("evalue", float("inf")))


def parse_blast_hits(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse JSON2 into agent-friendly hit records."""
    reports = payload.get("BlastOutput2") or []
    if not reports:
        return {"num_hits": 0, "hits": [], "search_stats": {}}

    report = reports[0].get("report") or {}
    search = ((report.get("results") or {}).get("search")) or {}
    raw_hits = search.get("hits") or []
    stats = search.get("stat") or {}

    hits: list[dict[str, Any]] = []
    for index, hit in enumerate(raw_hits, start=1):
        descriptions = hit.get("description") or []
        desc = descriptions[0] if descriptions else {}
        hsps = hit.get("hsps") or []
        if not hsps:
            continue
        hsp = _best_hsp(hsps)
        identity = hsp.get("identity")
        align_len = hsp.get("align_len") or 0
        percent_identity = None
        if identity is not None and align_len:
            percent_identity = round(100.0 * identity / align_len, 2)

        hits.append(
            {
                "rank": index,
                "accession": desc.get("accession") or desc.get("id"),
                "title": desc.get("title"),
                "taxid": desc.get("taxid"),
                "evalue": hsp.get("evalue"),
                "bit_score": hsp.get("bit_score"),
                "identity": identity,
                "align_len": align_len,
                "percent_identity": percent_identity,
                "query_from": hsp.get("query_from"),
                "query_to": hsp.get("query_to"),
                "hit_from": hsp.get("hit_from"),
                "hit_to": hsp.get("hit_to"),
                "query_strand": hsp.get("query_strand"),
                "hit_strand": hsp.get("hit_strand"),
            }
        )

    search_stats = {
        "db_num": stats.get("db_num"),
        "db_len": stats.get("db_len"),
        "hsp_len": stats.get("hsp_len"),
        "eff_space": stats.get("eff_space"),
        "kappa": stats.get("kappa"),
        "lambda": stats.get("lambda"),
        "entropy": stats.get("entropy"),
    }
    return {
        "num_hits": len(hits),
        "hits": hits,
        "search_stats": {k: v for k, v in search_stats.items() if v is not None},
        "program": report.get("program"),
        "version": report.get("version"),
        "database": ((report.get("search_target") or {}).get("db")),
    }


def classify_agent_status(ncbi_status: str) -> str:
    status = ncbi_status.upper()
    if status in BLAST_STATUS_READY:
        return "ready"
    if status in BLAST_STATUS_FAILED:
        return "failed"
    return "running"


def get_blast_results_once(rid: str) -> dict[str, Any]:
    """Check status once and return structured agent payload."""
    status_info = get_blast_job_status(rid)
    ncbi_status = status_info["ncbi_status"]
    agent_status = classify_agent_status(ncbi_status)

    base: dict[str, Any] = {
        "status": agent_status,
        "rid": rid,
        "ncbi_status": ncbi_status,
    }

    if agent_status == "running":
        base["retry_after_seconds"] = 60
        base["message"] = (
            "BLAST job still running. Wait at least 60 seconds, then call "
            "get_blast_results again with the same rid."
        )
        return base

    if agent_status == "failed":
        base["message"] = (
            "BLAST job failed or expired (RIDs expire in ~24 hours). "
            "Submit a new search with submit_blast_search."
        )
        return base

    there_are_hits = status_info.get("there_are_hits")
    if there_are_hits is False:
        base["num_hits"] = 0
        base["hits"] = []
        base["search_stats"] = {}
        base["message"] = "BLAST search completed with no hits."
        return base

    payload = fetch_blast_results_json(rid)
    parsed = parse_blast_hits(payload)
    base.update(parsed)
    base["message"] = f"BLAST search completed with {parsed['num_hits']} hit(s)."
    return base

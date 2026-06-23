"""Execute VirBench-style queries against Kiki MCP tools."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastmcp import Client

from kiki.benchmark.load import iter_queries, load_query_set
from kiki.server import create_server


def _extract_count(data: dict[str, Any], count_field: str | None) -> int | None:
    if not data.get("success"):
        return None
    result = data.get("result", {})
    if count_field:
        cursor: Any = result
        for part in count_field.split("."):
            if isinstance(cursor, dict):
                cursor = cursor.get(part)
            else:
                cursor = None
                break
        if cursor is not None:
            return int(cursor)
    if "count" in result:
        return int(result["count"])
    if "returned" in result and result["returned"] is not None:
        return int(result["returned"])
    manifest = result.get("dataset_manifest", {})
    if manifest.get("accession_count") is not None:
        return int(manifest["accession_count"])
    return None


@dataclass
class QueryResult:
    query_id: str
    name: str
    tool: str
    expected_count: int | None
    actual_count: int | None
    tolerance: int
    passed: bool
    reproducible: bool | None
    query_ids_seen: list[str] = field(default_factory=list)
    counts_seen: list[int | None] = field(default_factory=list)
    error: str | None = None
    manifest_query_id: str | None = None
    tags: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class BenchmarkReport:
    total: int
    passed: int
    failed: int
    skipped: int
    accuracy_pct: float | None
    reproducibility_pct: float | None
    results: list[QueryResult]
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "accuracy_pct": self.accuracy_pct,
            "reproducibility_pct": self.reproducibility_pct,
            "description": self.description,
            "results": [
                {
                    "query_id": item.query_id,
                    "name": item.name,
                    "tool": item.tool,
                    "expected_count": item.expected_count,
                    "actual_count": item.actual_count,
                    "tolerance": item.tolerance,
                    "passed": item.passed,
                    "reproducible": item.reproducible,
                    "query_ids_seen": item.query_ids_seen,
                    "counts_seen": item.counts_seen,
                    "manifest_query_id": item.manifest_query_id,
                    "error": item.error,
                    "skipped": item.skipped,
                    "skip_reason": item.skip_reason,
                    "tags": item.tags,
                }
                for item in self.results
            ],
        }


async def _call_tool_once(
    client: Client,
    tool: str,
    params: dict[str, Any],
    count_field: str | None,
) -> tuple[dict[str, Any], int | None]:
    response = await client.call_tool(tool, params)
    data = response.data
    count = _extract_count(data, count_field)
    return data, count


async def _run_single_query(
    client: Client,
    entry: dict[str, Any],
    *,
    repeats: int,
) -> QueryResult:
    query_id = entry["id"]
    expected = entry.get("expected_count")
    tolerance = int(entry.get("tolerance", 0))
    tool = entry["tool"]
    params = dict(entry.get("params", {}))
    count_field = entry.get("count_field")

    if expected is None:
        return await _run_reproducibility_only(
            client,
            entry,
            repeats=repeats,
        )

    query_ids_seen: list[str] = []
    counts_seen: list[int | None] = []
    last_error: str | None = None
    manifest_query_id: str | None = None

    for run_index in range(repeats):
        if run_index > 0:
            await asyncio.sleep(1.0)
        data, count = await _call_tool_once(client, tool, params, count_field)
        if not data.get("success"):
            last_error = data.get("error", {}).get("message", str(data))
            query_ids_seen.append("")
            counts_seen.append(None)
            continue
        manifest_query_id = data.get("query_id")
        query_ids_seen.append(manifest_query_id or "")
        counts_seen.append(count)

    valid_counts = [value for value in counts_seen if value is not None]
    actual = valid_counts[0] if valid_counts else None
    passed = (
        actual is not None
        and expected is not None
        and abs(actual - expected) <= tolerance
        and last_error is None
    )

    unique_qids = {qid for qid in query_ids_seen if qid}
    unique_counts = {c for c in counts_seen if c is not None}
    reproducible = (
        len(valid_counts) == repeats
        and len(unique_qids) == 1
        and len(unique_counts) == 1
        and last_error is None
    )

    return QueryResult(
        query_id=query_id,
        name=entry.get("name", query_id),
        tool=tool,
        expected_count=expected,
        actual_count=actual,
        tolerance=tolerance,
        passed=passed,
        reproducible=reproducible,
        query_ids_seen=query_ids_seen,
        counts_seen=counts_seen,
        error=last_error,
        manifest_query_id=manifest_query_id,
        tags=list(entry.get("tags", [])),
    )


async def _run_reproducibility_only(
    client: Client,
    entry: dict[str, Any],
    *,
    repeats: int,
) -> QueryResult:
    tool = entry["tool"]
    params = dict(entry.get("params", {}))
    count_field = entry.get("count_field")

    query_ids_seen: list[str] = []
    counts_seen: list[int | None] = []
    last_error: str | None = None
    manifest_query_id: str | None = None

    for run_index in range(repeats):
        if run_index > 0:
            await asyncio.sleep(1.0)
        data, count = await _call_tool_once(client, tool, params, count_field)
        if not data.get("success"):
            last_error = data.get("error", {}).get("message", str(data))
            query_ids_seen.append("")
            counts_seen.append(None)
            continue
        manifest_query_id = data.get("query_id")
        query_ids_seen.append(manifest_query_id or "")
        counts_seen.append(count)

    valid_counts = [value for value in counts_seen if value is not None]
    unique_qids = {qid for qid in query_ids_seen if qid}
    unique_counts = {c for c in counts_seen if c is not None}
    reproducible = (
        len(valid_counts) == repeats
        and len(unique_qids) == 1
        and len(unique_counts) == 1
        and last_error is None
    )

    return QueryResult(
        query_id=entry["id"],
        name=entry.get("name", entry["id"]),
        tool=tool,
        expected_count=None,
        actual_count=valid_counts[0] if valid_counts else None,
        tolerance=0,
        passed=reproducible,
        reproducible=reproducible,
        query_ids_seen=query_ids_seen,
        counts_seen=counts_seen,
        error=last_error,
        manifest_query_id=manifest_query_id,
        tags=list(entry.get("tags", [])),
        skipped=False,
        skip_reason=entry.get("note"),
    )


async def run_benchmark_async(
    *,
    query_path: Path | None = None,
    tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
    repeats: int = 3,
    output_dir: Path | None = None,
) -> BenchmarkReport:
    query_set = load_query_set(query_path)
    queries = iter_queries(query_set, tags=tags, exclude_tags=exclude_tags)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    mcp = create_server()
    results: list[QueryResult] = []

    async with Client(mcp) as client:
        for entry in queries:
            params = dict(entry.get("params", {}))
            if (
                entry["tool"] == "retrieve_virus_dataset"
                and output_dir is not None
                and "outfolder" not in params
            ):
                params["outfolder"] = str(output_dir / entry["id"])
                entry = {**entry, "params": params}

            result = await _run_single_query(client, entry, repeats=repeats)
            results.append(result)

    scored = [r for r in results if r.expected_count is not None and not r.skipped]
    passed = sum(1 for r in scored if r.passed)
    failed = sum(1 for r in scored if not r.passed)
    skipped = sum(1 for r in results if r.skipped)

    repro_candidates = [r for r in results if r.reproducible is not None and not r.skipped]
    repro_passed = sum(1 for r in repro_candidates if r.reproducible)

    accuracy_pct = (100.0 * passed / len(scored)) if scored else None
    reproducibility_pct = (
        (100.0 * repro_passed / len(repro_candidates)) if repro_candidates else None
    )

    return BenchmarkReport(
        total=len(results),
        passed=passed,
        failed=failed,
        skipped=skipped,
        accuracy_pct=accuracy_pct,
        reproducibility_pct=reproducibility_pct,
        results=results,
        description=query_set.get("description", ""),
    )


def run_benchmark(
    *,
    query_path: Path | None = None,
    tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
    repeats: int = 3,
    output_dir: Path | None = None,
) -> BenchmarkReport:
    return asyncio.run(
        run_benchmark_async(
            query_path=query_path,
            tags=tags,
            exclude_tags=exclude_tags,
            repeats=repeats,
            output_dir=output_dir,
        )
    )

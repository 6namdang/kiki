"""Load benchmark query definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kiki.errors import ErrorCode, KikiError

QUERIES_PATH = Path(__file__).parent / "queries" / "public_subset.json"


def load_query_set(path: Path | None = None) -> dict[str, Any]:
    query_path = path or QUERIES_PATH
    if not query_path.is_file():
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            f"Benchmark query file not found: {query_path}",
        )
    with open(query_path, encoding="utf-8") as handle:
        return json.load(handle)


def iter_queries(
    query_set: dict[str, Any],
    *,
    tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    for entry in query_set.get("queries", []):
        entry_tags = set(entry.get("tags", []))
        if tags and not entry_tags.intersection(tags):
            continue
        if exclude_tags and entry_tags.intersection(exclude_tags):
            continue
        queries.append(entry)
    return queries

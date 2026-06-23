"""Persist and query QueryManifest history for downstream agent inspection."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kiki.config import DEFAULT_AUDIT_DIR

HISTORY_FILENAME = "manifest_history.jsonl"


def audit_dir() -> Path:
    return Path(os.environ.get("KIKI_AUDIT_DIR", DEFAULT_AUDIT_DIR))


def history_path() -> Path:
    return audit_dir() / HISTORY_FILENAME


def record_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Append a manifest snapshot to the local audit log. Returns storage metadata."""
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "query_id": manifest.get("query_id"),
        "tool": manifest.get("tool"),
        "success": manifest.get("success"),
        "message": manifest.get("message"),
        "manifest": manifest,
    }
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, separators=(",", ":"), default=str))
        handle.write("\n")

    return {
        "recorded": True,
        "history_path": str(path),
        "query_id": manifest.get("query_id"),
    }


def query_history(
    *,
    query_id: str | None = None,
    tool: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return recent manifest history entries, newest first."""
    path = history_path()
    if not path.is_file():
        return []

    limit = min(max(1, limit), 500)
    entries: list[dict[str, Any]] = []

    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if query_id and entry.get("query_id") != query_id:
                continue
            if tool and entry.get("tool") != tool:
                continue
            entries.append(entry)

    entries.reverse()
    return entries[:limit]


def get_manifest_by_query_id(query_id: str) -> dict[str, Any] | None:
    """Return the most recent manifest entry for a query_id."""
    matches = query_history(query_id=query_id, limit=1)
    return matches[0] if matches else None

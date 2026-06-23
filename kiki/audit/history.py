"""Persist and query QueryManifest history for downstream agent inspection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kiki.audit.paths import FALLBACK_AUDIT_DIR, history_enabled, resolve_writable_dir
from kiki.config import DEFAULT_AUDIT_DIR

HISTORY_FILENAME = "manifest_history.jsonl"


def audit_dir() -> tuple[Path, str | None]:
    return resolve_writable_dir(
        DEFAULT_AUDIT_DIR,
        fallback=FALLBACK_AUDIT_DIR,
        env_var="KIKI_AUDIT_DIR",
    )


def history_paths() -> list[Path]:
    primary, _ = audit_dir()
    paths = [primary / HISTORY_FILENAME]
    fallback = FALLBACK_AUDIT_DIR / HISTORY_FILENAME
    if fallback not in paths:
        paths.append(fallback)
    return paths


def _append_entry(path: Path, manifest: dict[str, Any]) -> None:
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


def record_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Append a manifest snapshot to the audit log. Never raises on write failure."""
    if not history_enabled():
        return {
            "recorded": False,
            "query_id": manifest.get("query_id"),
            "reason": "Audit history disabled (KIKI_RECORD_HISTORY=false).",
        }

    primary_dir, dir_note = audit_dir()
    primary_path = primary_dir / HISTORY_FILENAME
    fallback_path = FALLBACK_AUDIT_DIR / HISTORY_FILENAME

    last_error: OSError | None = None
    for path in (primary_path, fallback_path):
        try:
            _append_entry(path, manifest)
            payload: dict[str, Any] = {
                "recorded": True,
                "history_path": str(path),
                "query_id": manifest.get("query_id"),
            }
            if path != primary_path:
                payload["note"] = f"Primary audit dir not writable; wrote to {path}"
            elif dir_note:
                payload["note"] = dir_note
            return payload
        except OSError as exc:
            last_error = exc
            continue

    return {
        "recorded": False,
        "query_id": manifest.get("query_id"),
        "reason": f"Could not write audit log: {last_error or 'unknown error'}",
    }


def query_history(
    *,
    query_id: str | None = None,
    tool: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return recent manifest history entries, newest first."""
    limit = min(max(1, limit), 500)
    entries: list[dict[str, Any]] = []

    for path in history_paths():
        if not path.is_file():
            continue
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

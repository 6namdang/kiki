"""Shared helpers for reporting pagination completeness."""

from __future__ import annotations

from typing import Any


def pagination_meta(
    *,
    total_available: int | None,
    retrieved: int,
    pages_fetched: int,
    complete: bool | None = None,
) -> dict[str, Any]:
    """Build a consistent pagination block for service responses."""
    if complete is None and total_available is not None:
        complete = retrieved >= total_available
    return {
        "total_available": total_available,
        "retrieved": retrieved,
        "pages_fetched": pages_fetched,
        "pagination_complete": complete if complete is not None else True,
    }

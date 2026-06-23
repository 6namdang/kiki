from datetime import UTC, datetime
from typing import Any


def build_audit(
    *,
    source: str,
    operation: str,
    params: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a reproducibility log block attached to every tool response."""
    audit: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "source": source,
        "operation": operation,
        "params": params,
    }
    if extra:
        audit.update(extra)
    return audit

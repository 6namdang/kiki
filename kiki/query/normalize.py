import hashlib
import json
from typing import Any


def normalize_query_params(params: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize query params for stable hashing and reproducibility."""
    normalized: dict[str, Any] = {}
    for key in sorted(params):
        value = params[key]
        if value is None or value == "":
            continue
        if isinstance(value, str):
            normalized[key] = value.strip()
        elif isinstance(value, bool):
            normalized[key] = value
        else:
            normalized[key] = value
    return normalized


def compute_query_id(params: dict[str, Any]) -> str:
    """Deterministic query identifier from normalized parameters."""
    canonical = json.dumps(normalize_query_params(params), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

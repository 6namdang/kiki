import importlib.metadata
from dataclasses import asdict, dataclass, field
from typing import Any

from kiki import __version__ as kiki_version
from kiki.config import ENSEMBL_DEFAULT_RELEASE
from kiki.query.normalize import compute_query_id, normalize_query_params


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


@dataclass
class QueryManifest:
    """Standard deterministic response envelope for all Kiki tools."""

    tool: str
    success: bool
    query: dict[str, Any]
    result: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)
    query_id: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if self.query_id is None:
            self.query_id = compute_query_id(self.query)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


def build_provenance(
    *,
    engine: str,
    operation: str,
    params: dict[str, Any],
    filters_applied: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if "gget" in engine:
        engine_version = _package_version("gget")
    elif engine.startswith("ensembl"):
        release = params.get("release")
        engine_version = f"release-{release}" if release is not None else f"release-{ENSEMBL_DEFAULT_RELEASE}"
    elif engine.startswith("ncbi.blast"):
        engine_version = "blast.ncbi.nlm.nih.gov/urlapi"
    elif engine.startswith("ncbi.eutils"):
        engine_version = "eutils.ncbi.nlm.nih.gov"
    elif engine.startswith("uniprot"):
        engine_version = "rest.uniprot.org"
    elif engine.startswith("ena"):
        engine_version = "ebi.ac.uk/ena"
    else:
        engine_version = _package_version(engine)
    provenance: dict[str, Any] = {
        "engine": engine,
        "engine_version": engine_version,
        "kiki_version": kiki_version,
        "operation": operation,
        "normalized_query": normalize_query_params(params),
        "filters_applied": filters_applied,
    }
    if extra:
        provenance.update(extra)
    return provenance

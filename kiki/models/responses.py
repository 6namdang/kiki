from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ToolResponse:
    """Standardized MCP tool output for agents and audit trails."""

    tool: str
    success: bool
    query: dict[str, Any]
    audit: dict[str, Any] = field(default_factory=dict)
    returned: int | None = None
    total_available: int | None = None
    records: list[dict[str, Any]] | None = None
    output_dir: str | None = None
    files: list[str] | None = None
    manifest: dict[str, Any] | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}

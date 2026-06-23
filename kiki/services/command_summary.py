"""Parse gget.virus command_summary.txt for failed operations."""

from pathlib import Path
from typing import Any

FAILURE_HEADER = "FAILED OPERATIONS - RETRY COMMANDS"


def parse_command_summary(path: str | Path) -> dict[str, Any]:
    """Extract failure information from gget command_summary.txt."""
    summary_path = Path(path)
    if not summary_path.is_file():
        return {"detected": False, "path": str(summary_path)}

    text = summary_path.read_text(encoding="utf-8", errors="replace")
    if FAILURE_HEADER not in text:
        return {
            "detected": False,
            "path": str(summary_path),
            "has_command_summary": True,
        }

    start = text.index(FAILURE_HEADER)
    excerpt = text[start:].strip()
    if len(excerpt) > 4000:
        excerpt = excerpt[:4000] + "\n... (truncated)"

    retry_urls = [
        line.removeprefix("Retry URL: ").strip()
        for line in excerpt.splitlines()
        if line.startswith("Retry URL:")
    ]

    return {
        "detected": True,
        "path": str(summary_path),
        "excerpt": excerpt,
        "retry_urls": retry_urls,
        "message": (
            "Some gget.virus operations failed. Inspect command_summary.txt "
            "FAILED OPERATIONS section before treating the dataset as complete."
        ),
    }

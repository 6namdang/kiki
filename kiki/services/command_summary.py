"""Parse gget.virus command_summary.txt for audit and failure reporting."""

from pathlib import Path
from typing import Any

FAILURE_HEADER = "FAILED OPERATIONS - RETRY COMMANDS"
MAX_EXCERPT_CHARS = 6000
MAX_SUMMARY_CHARS = 3000


def _read_summary_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def summarize_command_summary(path: str | Path) -> dict[str, Any]:
    """Extract key excerpts from command_summary.txt for provenance."""
    summary_path = Path(path)
    if not summary_path.is_file():
        return {"path": str(summary_path), "available": False}

    text = _read_summary_text(summary_path)
    lines = text.splitlines()
    head = "\n".join(lines[:40]).strip()
    if len(head) > MAX_SUMMARY_CHARS:
        head = head[:MAX_SUMMARY_CHARS] + "\n... (truncated)"

    payload: dict[str, Any] = {
        "path": str(summary_path),
        "available": True,
        "line_count": len(lines),
        "excerpt": head,
        "has_failures": FAILURE_HEADER in text,
    }

    if FAILURE_HEADER in text:
        payload["failure_section"] = _extract_failure_section(text)

    return payload


def _extract_failure_section(text: str) -> dict[str, Any]:
    start = text.index(FAILURE_HEADER)
    excerpt = text[start:].strip()
    if len(excerpt) > MAX_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_EXCERPT_CHARS] + "\n... (truncated)"

    retry_urls = [
        line.removeprefix("Retry URL: ").strip()
        for line in excerpt.splitlines()
        if line.startswith("Retry URL:")
    ]

    return {
        "excerpt": excerpt,
        "retry_urls": retry_urls,
        "message": (
            "Some gget.virus operations failed. Inspect command_summary.txt "
            "FAILED OPERATIONS section before treating the dataset as complete."
        ),
    }


def parse_command_summary(path: str | Path) -> dict[str, Any]:
    """Extract failure information from gget command_summary.txt."""
    summary = summarize_command_summary(path)
    if not summary.get("available"):
        return {"detected": False, "path": summary["path"]}

    if not summary.get("has_failures"):
        return {
            "detected": False,
            "path": summary["path"],
            "has_command_summary": True,
            "excerpt": summary.get("excerpt"),
        }

    failure = summary["failure_section"]
    return {
        "detected": True,
        "path": summary["path"],
        "excerpt": failure["excerpt"],
        "retry_urls": failure["retry_urls"],
        "message": failure["message"],
    }

"""Format benchmark results for terminal and markdown."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kiki.benchmark.runner import BenchmarkReport


def format_markdown(report: BenchmarkReport) -> str:
    lines = [
        "# Kiki VirBench public subset report",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
    ]
    if report.description:
        lines.extend([report.description, ""])

    if report.accuracy_pct is not None:
        lines.append(
            f"**Accuracy:** {report.passed}/{report.passed + report.failed} "
            f"({report.accuracy_pct:.1f}%)"
        )
    if report.reproducibility_pct is not None:
        lines.append(
            f"**Reproducibility (3× same params):** "
            f"{report.reproducibility_pct:.1f}%"
        )
    lines.append("")

    lines.append("| ID | Tool | Expected | Actual | Pass | Reproducible |")
    lines.append("|----|------|----------|--------|------|--------------|")
    for item in report.results:
        expected = "—" if item.expected_count is None else str(item.expected_count)
        actual = "—" if item.actual_count is None else str(item.actual_count)
        passed = "✅" if item.passed else "❌"
        repro = (
            "✅"
            if item.reproducible
            else "❌"
            if item.reproducible is False
            else "—"
        )
        lines.append(
            f"| `{item.query_id}` | {item.tool} | {expected} | {actual} | {passed} | {repro} |"
        )
        if item.error:
            lines.append(f"| | _{item.error}_ | | | | |")
    lines.append("")
    return "\n".join(lines)


def format_terminal(report: BenchmarkReport) -> str:
    lines = ["Kiki VirBench public subset", "=" * 40]
    if report.accuracy_pct is not None:
        lines.append(
            f"Accuracy:   {report.passed}/{report.passed + report.failed} "
            f"({report.accuracy_pct:.1f}%)"
        )
    if report.reproducibility_pct is not None:
        lines.append(f"Reproducible: {report.reproducibility_pct:.1f}%")
    lines.append("")
    for item in report.results:
        status = "PASS" if item.passed else "FAIL"
        lines.append(f"[{status}] {item.query_id}")
        lines.append(f"  tool={item.tool} expected={item.expected_count} actual={item.actual_count}")
        if item.manifest_query_id:
            lines.append(f"  query_id={item.manifest_query_id}")
        if item.reproducible is not None:
            lines.append(f"  reproducible={item.reproducible} runs={item.counts_seen}")
        if item.error:
            lines.append(f"  error={item.error}")
    return "\n".join(lines)


def write_report(
    report: BenchmarkReport,
    output_dir: Path,
    *,
    prefix: str = "virbench",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{prefix}_{timestamp}.json"
    md_path = output_dir / f"{prefix}_{timestamp}.md"

    payload: dict[str, Any] = report.to_dict()
    payload["generated_at"] = datetime.now(UTC).isoformat()

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(format_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}

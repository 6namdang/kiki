"""CLI: python -m kiki.benchmark"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kiki.benchmark.report import format_terminal, write_report
from kiki.benchmark.runner import run_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Kiki VirBench public subset (accuracy + reproducibility).",
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=None,
        help="Path to query JSON (default: kiki/benchmark/queries/public_subset.json)",
    )
    parser.add_argument(
        "--safe-only",
        action="store_true",
        help="Run only queries tagged 'safe' (default for quick smoke).",
    )
    parser.add_argument(
        "--include-integration",
        action="store_true",
        help="Include integration/dataset queries (slow; may download sequences).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of identical runs per query for reproducibility check.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("kiki_output/virbench"),
        help="Directory for reports and optional dataset downloads.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print summary only; do not write JSON/markdown report files.",
    )
    args = parser.parse_args(argv)

    tags: set[str] | None = {"safe"} if args.safe_only else None
    exclude_tags: set[str] | None = None
    if not args.include_integration:
        exclude_tags = {"integration", "dataset"}

    dataset_dir = args.output_dir / "datasets" if args.include_integration else None

    report = run_benchmark(
        query_path=args.queries,
        tags=tags,
        exclude_tags=exclude_tags,
        repeats=args.repeats,
        output_dir=dataset_dir,
    )

    print(format_terminal(report))

    if not args.no_write:
        paths = write_report(report, args.output_dir)
        print(f"\nWrote {paths['json']}")
        print(f"Wrote {paths['markdown']}")

    if report.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

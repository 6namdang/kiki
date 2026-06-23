"""Resolve writable output directories for dataset downloads."""

from __future__ import annotations

from pathlib import Path

from kiki.audit.paths import FALLBACK_OUTPUT_DIR, resolve_writable_dir
from kiki.config import DEFAULT_OUTPUT_ROOT


def output_root() -> tuple[Path, str | None]:
    return resolve_writable_dir(
        DEFAULT_OUTPUT_ROOT,
        fallback=FALLBACK_OUTPUT_DIR,
        env_var="KIKI_OUTPUT_DIR",
    )

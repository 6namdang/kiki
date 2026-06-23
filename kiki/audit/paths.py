"""Resolve writable directories on local dev vs read-only hosted runtimes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

FALLBACK_AUDIT_DIR = Path(tempfile.gettempdir()) / "kiki_audit"
FALLBACK_OUTPUT_DIR = Path(tempfile.gettempdir()) / "kiki_output"


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".kiki_write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def resolve_writable_dir(
    preferred: Path,
    *,
    fallback: Path,
    env_var: str,
) -> tuple[Path, str | None]:
    """Pick the first writable directory; return path and optional fallback note."""
    if os.environ.get(env_var):
        chosen = Path(os.environ[env_var]).expanduser()
        if _is_writable_dir(chosen):
            return chosen, None
        if _is_writable_dir(fallback):
            return fallback, f"{env_var} not writable; using {fallback}"
        return chosen, f"{env_var} set but not writable; writes may fail"

    if _is_writable_dir(preferred):
        return preferred, None
    if _is_writable_dir(fallback):
        return fallback, f"{preferred} not writable; using {fallback}"
    return preferred, f"{preferred} not writable; writes may fail"


def history_enabled() -> bool:
    value = os.environ.get("KIKI_RECORD_HISTORY", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}

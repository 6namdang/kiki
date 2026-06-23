from pathlib import Path

import pytest

from kiki.audit.paths import resolve_writable_dir


def test_resolve_writable_dir_uses_fallback_when_primary_read_only(tmp_path, monkeypatch) -> None:
    read_only = tmp_path / "readonly"
    read_only.mkdir()
    read_only.chmod(0o555)

    fallback = tmp_path / "fallback"
    chosen, note = resolve_writable_dir(
        read_only,
        fallback=fallback,
        env_var="KIKI_TEST_DIR",
    )
    assert chosen == fallback
    assert note is not None

    read_only.chmod(0o755)


def test_resolve_writable_dir_respects_env_var(tmp_path, monkeypatch) -> None:
    explicit = tmp_path / "custom"
    monkeypatch.setenv("KIKI_TEST_DIR", str(explicit))
    chosen, _ = resolve_writable_dir(
        tmp_path / "ignored",
        fallback=tmp_path / "fallback",
        env_var="KIKI_TEST_DIR",
    )
    assert chosen == explicit

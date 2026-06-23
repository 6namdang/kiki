import os

import pytest

from kiki.benchmark.load import iter_queries, load_query_set
from kiki.benchmark.runner import run_benchmark_async


@pytest.mark.asyncio
async def test_virbench_safe_queries_pass(tmp_path, monkeypatch) -> None:
    """Safe subset must hit ground-truth counts and be reproducible across 3 runs."""
    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))

    report = await run_benchmark_async(
        tags={"safe"},
        repeats=3,
        output_dir=tmp_path / "datasets",
    )

    assert report.total >= 4
    assert report.failed == 0, report.to_dict()
    assert report.accuracy_pct == 100.0
    assert report.reproducibility_pct == 100.0

    for item in report.results:
        assert item.passed, f"{item.query_id}: {item.error}"
        assert item.reproducible is True
        assert len(set(item.query_ids_seen)) == 1
        assert len(set(item.counts_seen)) == 1


def test_public_subset_loads() -> None:
    query_set = load_query_set()
    assert query_set["version"] == "1"
    safe = iter_queries(query_set, tags={"safe"})
    assert len(safe) >= 4
    blog = iter_queries(query_set, tags={"blog"})
    assert any(q["id"] == "blog_ebola_zebov_2014_window" for q in blog)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_blog_ebola_dataset_count(tmp_path, monkeypatch) -> None:
    """Optional live run of blog VirBench example (expected 266)."""
    if not os.environ.get("KIKI_RUN_INTEGRATION_BENCHMARK"):
        pytest.skip("Set KIKI_RUN_INTEGRATION_BENCHMARK=1 to run dataset benchmark.")

    monkeypatch.setenv("KIKI_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("KIKI_OUTPUT_DIR", str(tmp_path / "output"))

    report = await run_benchmark_async(
        tags={"blog"},
        repeats=1,
        output_dir=tmp_path / "datasets",
    )

    assert report.total == 1
    item = report.results[0]
    assert item.passed, f"expected 266 got {item.actual_count}: {item.error}"
    assert item.actual_count == 266

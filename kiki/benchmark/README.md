# VirBench public subset

Kiki accuracy and reproducibility checks inspired by the [Anthropic biology agents blog](../blog.md) and VirBench (Nasri et al., 2026). The full 120-query VirBench benchmark is not public; this subset uses **blog-documented ground-truth counts** plus **stable smoke queries**.

## Quick run (safe only, ~30s)

```bash
python -m kiki.benchmark --safe-only
```

Runs 4 queries tagged `safe` (virus + UniProt), each **3 times**, and reports:

- **Accuracy** — actual count vs expected (tolerance 0)
- **Reproducibility** — identical `query_id` and count across repeats

Reports are written to `kiki_output/virbench/` as JSON + Markdown.

## Full public subset (excludes slow dataset downloads)

```bash
python -m kiki.benchmark
```

## Blog Ebola example (downloads sequences — slow)

```bash
python -m kiki.benchmark --include-integration
```

Includes the blog VirBench example (TaxID `3052462`, expected **266** sequences). Writes dataset output under `kiki_output/virbench/datasets/`.

## Query file

`queries/public_subset.json` — add queries with:

| Field | Description |
|-------|-------------|
| `id` | Stable identifier |
| `tool` | Kiki MCP tool name |
| `params` | Tool arguments (JSON) |
| `expected_count` | Ground truth (`null` = reproducibility-only) |
| `tolerance` | Allowed absolute error |
| `tags` | `safe`, `smoke`, `integration`, `dataset`, `blog` |

## pytest

```bash
pytest tests/test_virbench_subset.py -q
```

Integration tests (blog dataset) are skipped unless `KIKI_RUN_INTEGRATION_BENCHMARK=1`.

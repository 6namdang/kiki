# Contributing to Kiki

Kiki is an MCP server for **deterministic biological data retrieval** (NCBI Virus via gget, UniProt via REST). These rules keep the codebase agent-ready, reproducible, and safe to run in hosted environments.

## Before you start

1. Read `README.md` (tools reference) and `notebook.md` (product vision).
2. Python **3.12+** required.
3. Install dev dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

4. Run tests before opening a PR:

```bash
pytest
```

5. Verify the MCP server locally:

```bash
fastmcp inspect server.py:mcp
kiki serve --transport http --port 8000
```

---

## Architecture (must follow)

```
Agent → MCP tool (kiki/tools/) → service (kiki/services/) → gget / UniProt REST
                                      ↓
                              QueryManifest + provenance + audit
```

| Layer | Responsibility |
|-------|----------------|
| `kiki/tools/` | MCP tool signatures, `@tool_safe`, param collection, `success_manifest` |
| `kiki/services/` | Network I/O, pagination, file writes — **no MCP imports** |
| `kiki/query/` | Presets, validation, query normalization / `query_id` |
| `kiki/models/` | `QueryManifest`, response shapes |
| `kiki/audit/` | Provenance enrichment, manifest history, writable-path fallback |
| `kiki/errors.py` | `KikiError` + stable `ErrorCode` enum |
| `server.py` (repo root) | **Horizon entrypoint** — `server.py:mcp` only |

Do **not** put business logic in `kiki/server.py` or `server.py` beyond wiring.

---

## Non-negotiable rules

### 1. Every tool returns QueryManifest

Successful tool calls must use `success_manifest()` (virus/gget) or `uniprot_success_manifest()` (UniProt). Do not return ad-hoc dicts.

Required fields: `tool`, `success`, `query_id`, `query`, `result`, `provenance`, `message`.

### 2. Use KikiError for guardrails

Validate before network or disk I/O. Raise `KikiError` with a stable `ErrorCode` — never bare `ValueError` for user/agent-facing failures.

Register tools with `@tool_safe` so errors become JSON payloads, not MCP stack traces.

### 3. Never crash on audit or optional I/O

Manifest history (`record_manifest`) and writable-path resolution must **never** fail the primary tool result. Use `/tmp` fallback on read-only filesystems (Horizon). See `kiki/audit/paths.py`.

### 4. Dataset downloads require explicit consent

Tools that write sequences to disk must require `confirm_download=true` and raise `CONFIRM_DOWNLOAD_REQUIRED` otherwise.

### 5. Guard broad queries

Large taxa / organisms require narrowing filters. Use `validate_query_scope()` (virus) and `validate_uniprot_scope()` (UniProt). Never run unfiltered SARS-CoV-2 or `download_all_accessions` without filters in tests or docs examples.

### 6. Safe defaults for testing and docs

- Virus smoke tests: accession `NC_045512.2` or presets like `sars_cov2_ref_genome`.
- Do **not** add integration tests that download multi-GB datasets without maintainer approval.
- Do **not** commit secrets (`.env`, API keys, VirBench private CSVs).

### 7. Horizon deploy entrypoint

Production entrypoint is **`server.py:mcp`** at repo root — not `kiki/server.py:mcp`.

---

## Adding a new MCP tool

1. Implement service logic in `kiki/services/`.
2. Add tool in `kiki/tools/` (or `kiki/tools/uniprot/`).
3. Register in the appropriate `register_*_tools()` and `kiki/tools/__init__.py`.
4. Wrap with `@mcp.tool()` + `@tool_safe`.
5. Add tests:
   - Unit tests for validation / param mapping.
   - At most one live API smoke test if needed (mark slow/external clearly).
6. Document in `README.md` tools table + parameters + example JSON.

### Tool naming

- Snake_case, verb-first: `get_virus_metadata`, `count_proteins`, `map_protein_ids`.
- Use explicit `name=` on `@mcp.tool()` when the function name has a `_tool` suffix.

### Parameters

- Prefer explicit typed parameters on the tool function (FastMCP schema).
- Map gget/UniProt kwargs in `kiki/services/filters.py` or `kiki/tools/_params.py` — do not pass through unknown keys.
- Optional filters: `str | None = None`, `bool | None = None` — use `collect_filters()` to drop `None`.

---

## Code style

- **Python 3.12+** syntax (`str | None`, not `Optional[str]` unless matching existing file).
- **Type hints** on all public functions.
- **Minimal scope** — no drive-by refactors in the same PR as a feature.
- **Match existing patterns** in the file you edit.
- Comments only for non-obvious business logic (deferred filters, pagination, hosted FS behavior).
- No new dependencies without discussion — prefer stdlib + existing stack (`fastmcp`, `gget`, `requests`).

---

## Testing

| Requirement | Rule |
|-------------|------|
| All PRs | `pytest` must pass |
| New validation / mapping | Unit test in `tests/` |
| New MCP tool | Registration test or in-process `Client` smoke test |
| Reproducibility | Same params → same `query_id` and count when applicable |
| Async MCP tests | Use `@pytest.mark.asyncio` (configured in `pyproject.toml`) |

Test layout mirrors domains: `test_filters.py`, `test_uniprot_*.py`, `test_audit.py`, etc.

---

## Git & PR workflow

1. Branch from `main`: `feature/short-description` or `fix/short-description`.
2. Keep PRs focused — one concern per PR when possible.
3. PR description must include:
   - **What** changed
   - **Why**
   - **Test plan** (commands run)
4. Do not commit: `venv/`, `__pycache__/`, `kiki_output/`, `kiki_audit/`, `.env`, large generated datasets.
5. Update `README.md` when adding/changing tools or env vars.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `KIKI_OUTPUT_DIR` | Dataset download root (fallback: `/tmp/kiki_output`) |
| `KIKI_AUDIT_DIR` | Manifest audit log (fallback: `/tmp/kiki_audit`) |
| `KIKI_RECORD_HISTORY` | Set `false` to disable audit writes |
| `NCBI_API_KEY` | Optional, forwarded to gget |

Document new env vars in `README.md` and `kiki/config.py`.

---

## Hosted deployment (Horizon)

- Filesystem under `/app` is read-only — code must use writable-path fallback.
- Prefer metadata/count tools for hosted smoke tests; dataset tools write to `/tmp`.
- After deploy, test via Horizon Inspector or ChatMCP with minimal JSON:

```json
{ "preset": "sars_cov2_ref_genome" }
```

---

## Questions?

Open an issue or discuss in the PR. When in doubt: **deterministic, auditable, agent-safe**.

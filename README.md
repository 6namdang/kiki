# Kiki

MCP server for **deterministic biological sequence data retrieval** — Phase 1: NCBI Virus.

Agents call Kiki tools to query virus metadata, count records, or retrieve filtered datasets from NCBI. Every successful response uses a **QueryManifest** envelope with deterministic `query_id`, structured `result`, and `provenance` for reproducibility. Errors return stable machine-readable codes.

## Install

```bash
git clone <your-repo-url>
cd kiki

python3 -m venv venv
source venv/bin/activate

pip install -e ".[dev]"
```

Verify the CLI:

```bash
kiki serve --help
```

---

## Run the server

### Option A: HTTP (default)

Best for testing, scripts, or hosted deployments.

```bash
kiki serve --transport http --host 127.0.0.1 --port 8000
```

Server URL: `http://127.0.0.1:8000/mcp`

Leave this terminal running while you connect clients.

### Option B: stdio

Best for **Cursor** and **Claude Desktop** (agent launches the process directly).

```bash
kiki serve --transport stdio
```

---

## Connect an MCP client

### Cursor

1. Open **Cursor Settings → MCP → Add server**
2. Add one of the configs below
3. Restart Cursor or reload MCP servers

**stdio (recommended for Cursor):**

```json
{
  "mcpServers": {
    "kiki": {
      "command": "/absolute/path/to/kiki/venv/bin/kiki",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

**HTTP (if the server is already running):**

```json
{
  "mcpServers": {
    "kiki": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

Replace `/absolute/path/to/kiki` with your actual project path.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kiki": {
      "command": "/absolute/path/to/kiki/venv/bin/kiki",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

Restart Claude Desktop after saving.

---

## Use the tools

Once connected, ask your agent to call Kiki tools — or call them from Python.

### 1. `get_virus_metadata` — query only (safe)

Returns JSON metadata via **`gget.fetch_virus_metadata`** with **full API pagination**.
**Does not download sequences.** Returns up to `preview_limit` records inline plus `total_available` (full fetched count).

**By accession:**

```json
{
  "query": "NC_045512.2",
  "is_accession": true
}
```

**By taxon** (name or taxid — e.g. Ebola `186538`):

```json
{
  "query": "186538",
  "host": "Homo sapiens",
  "complete_only": true,
  "preview_limit": 5
}
```

Supported metadata filters: `host`, `geographic_location`, `annotated`, `complete_only`, `refseq_only`, `min_release_date`.

Example response shape:

```json
{
  "tool": "get_virus_metadata",
  "success": true,
  "query_id": "a1b2c3d4e5f6g7h8",
  "query": { "type": "accession", "value": "NC_045512.2", "is_accession": true },
  "result": {
    "returned": 5,
    "total_available": 142,
    "records": [{ "accession": "...", "length": 19710 }]
  },
  "provenance": {
    "engine": "gget.fetch_virus_metadata",
    "operation": "metadata_paginated",
    "pagination_complete": true,
    "filters_applied": []
  },
  "message": "Fetched 142 metadata records via gget pagination. Returning 5 inline preview."
}
```

Optional **`preset`** parameter (e.g. `sars_cov2_ref_genome`, `ebola_human_complete_africa`) merges curated defaults; explicit args override preset values.

### 2. `count_virus_sequences` — count only (safe)

Same metadata pagination path as `get_virus_metadata` with `preview_limit=0`. Returns `{ "count": N }` without downloading sequences. Use metadata-compatible filters and presets only; for dataset-only filters (collection dates, sequence length), use `retrieve_virus_dataset` and read `dataset_manifest.accession_count`.

```json
{
  "preset": "sars_cov2_ref_genome"
}
```

### 3. `retrieve_virus_dataset` — full gget.virus pipeline

Wraps **`gget.virus`** end-to-end: metadata filtering, pagination, sequence download, CSV/FASTA output.
Writes files to `kiki_output/`. Returns **file paths + manifest**, not inline sequences.

**Requires `confirm_download: true`.** Large taxa (e.g. SARS-CoV-2) require narrowing filters.

```json
{
  "query": "186538",
  "confirm_download": true,
  "host": "Homo sapiens",
  "nuc_completeness": "complete",
  "min_collection_date": "2014-01-01",
  "geographic_location": "Africa"
}
```

Supports the full **`gget.virus`** surface from `gget_virus_docs.md`:

| Category | Parameters |
|----------|------------|
| Query modes | `query`, `is_accession`, `download_all_accessions` |
| Optimized caches | `is_sars_cov2`, `is_alphainfluenza` |
| Host / location | `host`, `geographic_location`, `submitter_country` |
| Sequence / gene | `nuc_completeness`, `complete_only`, `min_seq_length`, `max_seq_length`, gene/protein/peptide counts, `max_ambiguous_chars`, `has_proteins`, `segment`, `proteins_complete` |
| Dates | `min_collection_date`, `max_collection_date`, `min_release_date`, `max_release_date` |
| Quality flags | `annotated`, `lab_passaged`, `vaccine_strain`, `provirus` |
| Database / lineage | `source_database`, `refseq_only`, `lineage`, `isolate`, `genotype`, … |
| Workflow | `outfolder`, `genbank_metadata`, `genbank_batch_size`, `keep_temp`, `verbose` |

Query may be a taxon, taxid, single accession, space-separated accessions, or a path to an accession list file (`is_accession=true`).

Presets: `sars_cov2_ref_genome`, `sars_cov2_human_complete`, `influenza_a_human_complete`, `ebola_human_complete_since_2014`.

**Failure handling:** gget writes `command_summary.txt` with a `FAILED OPERATIONS - RETRY COMMANDS` section when batches fail. Kiki parses this into `result.failures` — always check before treating a dataset as complete.

Example response shape:

```json
{
  "tool": "retrieve_virus_dataset",
  "success": true,
  "query_id": "...",
  "result": {
    "returned": 12,
    "output_dir": "/path/to/kiki_output/Ebola_20260622_...",
    "files": [".../ebola_metadata.csv", ".../ebola.fasta"],
    "dataset_manifest": {
      "accession_count": 12,
      "artifacts": {
        "metadata_csv": ".../ebola_metadata.csv",
        "fasta": ".../ebola.fasta"
      }
    }
  },
  "provenance": { "engine": "gget.virus", "operation": "dataset_download" }
}
```

Dataset preset example: `ebola_human_complete_since_2014` (includes collection date filters).

---

## UniProt tools

Five tools wrap the [UniProt REST API](https://rest.uniprot.org) (`rest.uniprot.org`). All searches default to **`reviewed:true`** (Swiss-Prot) unless `include_unreviewed=true`.

| Tool | Purpose | Downloads? |
|------|---------|------------|
| `search_proteins` | Paginated search, JSON preview + total | No |
| `count_proteins` | Count via `X-Total-Results` | No |
| `get_protein` | Single accession (JSON summary or FASTA/txt/xml) | No (inline) |
| `retrieve_protein_dataset` | Bulk FASTA to disk | Yes — `confirm_download=true` |
| `map_protein_ids` | Cross-database ID mapping | No |

**Presets:** `sars_cov2_spike`, `sars_cov2_nsp12`, `ebola_vp35`, `influenza_a_ha`, `human_insulin`, `human_tp53`

Example — SARS-CoV-2 spike count:

```json
{ "preset": "sars_cov2_spike" }
```

Example — single protein FASTA:

```json
{ "accession": "P01308", "format": "fasta" }
```

Example — ID mapping:

```json
{
  "ids": ["P01308"],
  "from_db": "UniProtKB_AC-ID",
  "to_db": "Gene_Name"
}
```

Structured filters (`organism_id`, `gene`, `protein_name`, `length_min`, `length_max`) are AND-combined with an optional raw UniProt query string. Large organisms (e.g. human `9606`) require narrowing filters for dataset downloads.

### Typed errors

Failed guardrails return `{ "success": false, "error": { "code": "...", "message": "...", "details": {} } }`:

| Code | Meaning |
|------|---------|
| `QUERY_TOO_BROAD` | Large taxon without narrowing filters |
| `CONFIRM_DOWNLOAD_REQUIRED` | Dataset tool called without `confirm_download=true` |
| `INVALID_DATE_RANGE` / `INVALID_DATE_FORMAT` | Bad date filters |
| `INVALID_SEQ_LENGTH_RANGE` | `min_seq_length` > `max_seq_length` |
| `PRESET_NOT_FOUND` | Unknown preset name |
| `INVALID_PARAMETER` | Missing query/preset or invalid filter combo |
| `UPSTREAM_ERROR` | UniProt/gget API failure |
| `NOT_FOUND` | UniProt accession not found |

Override the download directory with `outfolder` or the `KIKI_OUTPUT_DIR` environment variable. Optional `NCBI_API_KEY` is forwarded to gget when set.

---

## Test from Python (HTTP)

Start the server in one terminal, then run the smoke client in another:

```bash
# Terminal 1
kiki serve --transport http --port 8000

# Terminal 2
source venv/bin/activate
python client.py
```

Or call tools directly:

```python
import asyncio
from fastmcp import Client

client = Client("http://127.0.0.1:8000/mcp")

async def main():
    async with client:
        tools = await client.list_tools()
        print([t.name for t in tools])
        # ['get_virus_metadata', 'count_virus_sequences', 'retrieve_virus_dataset']

        result = await client.call_tool(
            "get_virus_metadata",
            {"query": "NC_045512.2", "is_accession": True},
        )
        print(result.data)

asyncio.run(main())
```

Or run the test suite (no server needed for most tests):

```bash
pytest
```

---

## Tools summary

| Tool | Purpose | Downloads? |
|------|---------|------------|
| `get_virus_metadata` | Query NCBI Virus metadata (JSON preview) | No |
| `count_virus_sequences` | Count metadata records (VirBench-style) | No |
| `retrieve_virus_dataset` | Filtered dataset via `gget.virus` | Yes — requires `confirm_download=true` |
| `search_proteins` | UniProtKB search (JSON preview) | No |
| `count_proteins` | UniProtKB count | No |
| `get_protein` | Single UniProt entry | No |
| `retrieve_protein_dataset` | UniProt FASTA dataset | Yes — requires `confirm_download=true` |
| `map_protein_ids` | UniProt ID mapping | No |

---

## Deploy to Prefect Horizon

[Horizon](https://horizon.prefect.io) is managed MCP hosting from the FastMCP team. Free tier for personal projects.

### Prerequisites

1. Push this repo to **GitHub** (public or private)
2. Entrypoint must expose a `FastMCP` object — use **`server.py:mcp`** (repo root, not `kiki/server.py:mcp`)

Verify locally before deploying:

```bash
fastmcp inspect server.py:mcp
```

### Deploy

1. Go to [horizon.prefect.io](https://horizon.prefect.io) and sign in with GitHub
2. Connect GitHub and **select this repository**
3. Configure the deployment:
   - **Server name:** e.g. `kiki-virus` (becomes part of your URL)
   - **Entrypoint:** `server.py:mcp`
   - **Description:** optional
   - **Authentication:** enable for private/team use; Horizon handles OAuth 2.1
4. Click **Deploy Server** — live in ~60 seconds

Your URL will look like:

```
https://kiki-virus.fastmcp.app/mcp
```

Horizon auto-redeploys on every push to `main`. Pull requests get preview URLs.

### Test on Horizon

In the Horizon dashboard:

- **Inspector** — run each tool with inputs and inspect JSON output
- **ChatMCP** — chat against the server to verify end-to-end behavior

Start with `get_virus_metadata` + accession `NC_045512.2` (no downloads).

### Connect clients to Horizon

**Cursor** (HTTP):

```json
{
  "mcpServers": {
    "kiki": {
      "url": "https://YOUR-SERVER-NAME.fastmcp.app/mcp"
    }
  }
}
```

**Python client:**

```python
from fastmcp import Client

client = Client("https://YOUR-SERVER-NAME.fastmcp.app/mcp")
```

If authentication is enabled, Horizon provides OAuth — follow the connection snippets in the dashboard.

### Note on `retrieve_virus_dataset`

Downloads write to the container filesystem on Horizon. Prefer **`get_virus_metadata`** for hosted testing. Dataset downloads are better suited to local/self-hosted runs unless you add persistent storage later.

---

## Project layout

```
kiki/
  server.py          # FastMCP app
  cli.py             # kiki serve
  tools/             # MCP tool definitions
  services/          # NCBI + gget wrappers
  models/            # QueryManifest + ToolResponse
  query/             # normalize, validate, presets
  errors.py          # KikiError codes
  audit/             # Reproducibility logs
tests/
```

See `notebook.md` for roadmap and strategy.

# Kiki

MCP server for **deterministic biological sequence data retrieval** — Phase 1: NCBI Virus.

Agents call Kiki tools to query virus metadata or retrieve filtered datasets from NCBI. Every response includes an audit block (timestamp, source, params) for reproducibility.

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
  "returned": 5,
  "total_available": 142,
  "records": [{ "accession": "...", "length": 19710, "...": "..." }],
  "audit": {
    "source": "gget.fetch_virus_metadata",
    "operation": "metadata_paginated",
    "pagination_complete": true
  },
  "message": "Fetched 142 metadata records via gget pagination. Returning 5 inline preview."
}
```

### 2. `retrieve_virus_dataset` — full gget.virus pipeline

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

Supports all major `gget.virus` filters: dates, host, location, sequence length, gene/protein counts, lineage, segment, genbank_metadata, and more.

Example response shape:

```json
{
  "tool": "retrieve_virus_dataset",
  "success": true,
  "output_dir": "/path/to/kiki_output/Ebola_20260622_...",
  "files": [".../ebola_metadata.csv", ".../ebola.fasta"],
  "returned": 12,
  "manifest": {
    "accession_count": 12,
    "artifacts": {
      "metadata_csv": ".../ebola_metadata.csv",
      "fasta": ".../ebola.fasta"
    }
  },
  "audit": { "...": "..." }
}
```

Override the download directory with the `KIKI_OUTPUT_DIR` environment variable.

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
        # ['get_virus_metadata', 'retrieve_virus_dataset']

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
| `get_virus_metadata` | Query NCBI Virus metadata (JSON) | No |
| `retrieve_virus_dataset` | Filtered dataset via `gget.virus` | Yes — requires `confirm_download=true` |

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
  models/            # Standardized ToolResponse
  audit/             # Reproducibility logs
tests/
```

See `notebook.md` for roadmap and strategy.

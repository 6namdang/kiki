# Kiki

MCP server for **deterministic biological data retrieval** — NCBI Virus (via gget) and UniProt (via REST API).

Agents call Kiki tools to query metadata, count records, retrieve datasets, or map identifiers. Every successful response uses a **QueryManifest** envelope with a deterministic `query_id`, structured `result`, and `provenance` block. Errors return stable machine-readable codes.

---

## Install

```bash
git clone <your-repo-url>
cd kiki

python3 -m venv venv
source venv/bin/activate

pip install -e ".[dev]"
kiki serve --help
```

**Contributing:** see [CONTRIBUTING.md](CONTRIBUTING.md) for architecture, coding rules, and PR workflow.

---

## Run the server

### HTTP (default)

```bash
kiki serve --transport http --host 127.0.0.1 --port 8000
```

Server URL: `http://127.0.0.1:8000/mcp`

### stdio (Cursor / Claude Desktop)

```bash
kiki serve --transport stdio
```

**Cursor (stdio):**

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

**Cursor / scripts (HTTP):**

```json
{
  "mcpServers": {
    "kiki": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

**Claude Desktop** — same stdio config in `~/Library/Application Support/Claude/claude_desktop_config.json`.

---

## Tools reference

Kiki exposes **8 tools** across two data sources. Use the safe query/count tools for exploration; use dataset tools only when you intend to write files to disk.

| # | Tool | Source | Purpose | Writes files? |
|---|------|--------|---------|---------------|
| 1 | [`get_virus_metadata`](#1-get_virus_metadata) | NCBI Virus / gget | Paginated metadata search + inline preview | No |
| 2 | [`count_virus_sequences`](#2-count_virus_sequences) | NCBI Virus / gget | Count metadata records | No |
| 3 | [`retrieve_virus_dataset`](#3-retrieve_virus_dataset) | NCBI Virus / gget | Full sequence dataset (FASTA/CSV/JSONL) | **Yes** |
| 4 | [`search_proteins`](#4-search_proteins) | UniProt REST | Paginated protein search + inline preview | No |
| 5 | [`count_proteins`](#5-count_proteins) | UniProt REST | Count matching proteins | No |
| 6 | [`get_protein`](#6-get_protein) | UniProt REST | Single accession lookup | No |
| 7 | [`retrieve_protein_dataset`](#7-retrieve_protein_dataset) | UniProt REST | Bulk FASTA download | **Yes** |
| 8 | [`map_protein_ids`](#8-map_protein_ids) | UniProt REST | Cross-database ID mapping | No |
| 9 | [`get_query_history`](#9-get_query_history) | Kiki audit log | Inspect prior QueryManifest runs | No |

### Shared behavior

**Response shape** — all tools return a QueryManifest:

```json
{
  "tool": "get_virus_metadata",
  "success": true,
  "query_id": "a1b2c3d4e5f6g7h8",
  "query": { "type": "accession", "value": "NC_045512.2" },
  "result": { },
  "provenance": { "engine": "...", "operation": "...", "filters_applied": [] },
  "message": "Human-readable summary."
}
```

**Presets** — most search/count/dataset tools accept a `preset` string that merges curated defaults. Explicit arguments always override preset values. See [Virus presets](#virus-presets) and [UniProt presets](#uniprot-presets).

**Dataset downloads** — `retrieve_virus_dataset` and `retrieve_protein_dataset` require `"confirm_download": true`. Output goes to `kiki_output/` by default, or set `outfolder` / `KIKI_OUTPUT_DIR`.

**Environment variables**

| Variable | Effect |
|----------|--------|
| `KIKI_OUTPUT_DIR` | Override default download directory (auto-fallback to `/tmp/kiki_output` if not writable) |
| `KIKI_AUDIT_DIR` | Override manifest audit log directory (default: `./kiki_audit`, auto-fallback to `/tmp/kiki_audit` if not writable) |
| `KIKI_RECORD_HISTORY` | Set to `false` to disable audit log writes (default: `true`) |
| `NCBI_API_KEY` | Forwarded to gget for NCBI Virus tools |

On read-only hosted runtimes (e.g. Horizon), audit logs and dataset downloads automatically fall back to `/tmp/kiki_audit` and `/tmp/kiki_output`. Tool calls never fail solely because audit logging failed.

**Audit & reproducibility** — virus tool responses include enriched `provenance`:

- `filter_application` — per-filter stage (`ncbi_virus_api`, `deferred_local`, `local_metadata_filter`) with human-readable explanations when gget applies filters locally
- `command_summary` — excerpt from gget's `command_summary.txt` (dataset downloads)
- `audit_record` — pointer to the append-only local history file
- `query_id` — deterministic hash of normalized params; same inputs → same `query_id`

Use **`get_query_history`** to inspect prior runs by `query_id` or list recent entries by `tool`.

**Typed errors**

| Code | Meaning |
|------|---------|
| `QUERY_TOO_BROAD` | Large taxon/organism without narrowing filters |
| `CONFIRM_DOWNLOAD_REQUIRED` | Dataset tool called without `confirm_download=true` |
| `INVALID_DATE_RANGE` / `INVALID_DATE_FORMAT` | Bad date filters (virus) |
| `INVALID_SEQ_LENGTH_RANGE` | Min length > max length |
| `PRESET_NOT_FOUND` | Unknown preset name |
| `INVALID_PARAMETER` | Missing required input or invalid filter |
| `UPSTREAM_ERROR` | gget or UniProt API failure |
| `NOT_FOUND` | UniProt accession not found |

---

## NCBI Virus tools

Powered by [gget](https://github.com/pachterlab/gget) against [NCBI Virus](https://www.ncbi.nlm.nih.gov/labs/virus/). Large taxa (e.g. SARS-CoV-2 `2697049`) require narrowing filters unless querying a specific accession.

### 1. `get_virus_metadata`

Query virus metadata with full gget pagination. Returns up to `preview_limit` records inline plus `total_available`. **Does not download sequences.**

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | — | Taxon name/ID or accession |
| `is_accession` | bool | `false` | Treat `query` as accession |
| `preset` | string | — | Named preset (see below) |
| `preview_limit` | int | `10` | Max inline records (max 100) |
| `host` | string | — | Host organism name or taxid |
| `geographic_location` | string | — | e.g. `Africa`, `USA` |
| `annotated` | bool | — | Annotated sequences only |
| `complete_only` | bool | — | Complete genomes only |
| `refseq_only` | bool | — | RefSeq records only |
| `min_release_date` | string | — | `YYYY-MM-DD` |

**Examples**

By accession (safest starting point):

```json
{ "query": "NC_045512.2", "is_accession": true }
```

By taxon with filters:

```json
{
  "query": "186538",
  "host": "Homo sapiens",
  "complete_only": true,
  "preview_limit": 5
}
```

With preset:

```json
{ "preset": "sars_cov2_ref_genome" }
```

**Result fields:** `returned`, `total_available`, `records[]`

---

### 2. `count_virus_sequences`

Count metadata records using the same gget pagination path as `get_virus_metadata`, with no inline records. Supports metadata-compatible filters and presets only.

**Parameters** — same filters as `get_virus_metadata` (no `preview_limit`).

**Examples**

```json
{ "preset": "sars_cov2_ref_genome" }
```

```json
{
  "query": "186538",
  "host": "Homo sapiens",
  "complete_only": true,
  "geographic_location": "Africa"
}
```

**Result fields:** `count`, `pagination_complete`

> For counts requiring dataset-only filters (collection dates, sequence length), use `retrieve_virus_dataset` and read `dataset_manifest.accession_count`.

---

### 3. `retrieve_virus_dataset`

Full `gget.virus` pipeline: metadata filtering, pagination, sequence download, CSV/FASTA/JSONL output. **Requires `confirm_download: true`.**

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | — | Taxon, taxid, accession, space-separated accessions, or accession list file path |
| `is_accession` | bool | `false` | Accession mode |
| `preset` | string | — | Named preset |
| `confirm_download` | bool | `false` | **Must be `true`** to run |
| `download_all_accessions` | bool | `false` | Filter across all viral accessions (requires narrowing filters) |
| `is_sars_cov2` | bool | `false` | NCBI cached SARS-CoV-2 download |
| `is_alphainfluenza` | bool | `false` | NCBI cached Influenza A download |
| `outfolder` | string | — | Output directory |
| `host` | string | — | Host filter |
| `geographic_location` | string | — | Location filter |
| `annotated` | bool | — | Annotated only |
| `complete_only` | bool | — | Complete genomes (maps to `nuc_completeness`) |
| `refseq_only` | bool | — | RefSeq only (maps to `source_database`) |
| `min_release_date` | string | — | `YYYY-MM-DD` |
| `max_release_date` | string | — | `YYYY-MM-DD` |
| `min_collection_date` | string | — | `YYYY-MM-DD` |
| `max_collection_date` | string | — | `YYYY-MM-DD` |
| `min_seq_length` | int | — | Min nucleotide length |
| `max_seq_length` | int | — | Max nucleotide length |
| `min_gene_count` | int | — | Min genes |
| `max_gene_count` | int | — | Max genes |
| `nuc_completeness` | string | — | `complete` or `partial` |
| `has_proteins` | string \| list | — | e.g. `"spike"` or `["spike", "ORF1ab"]` |
| `proteins_complete` | bool | `false` | All annotated proteins complete |
| `lab_passaged` | bool | — | Lab-passaged samples |
| `submitter_country` | string | — | Submitter country |
| `min_mature_peptide_count` | int | — | Min mature peptides |
| `max_mature_peptide_count` | int | — | Max mature peptides |
| `min_protein_count` | int | — | Min proteins |
| `max_protein_count` | int | — | Max proteins |
| `max_ambiguous_chars` | int | — | Max ambiguous bases (N) |
| `segment` | string \| list | — | e.g. `"HA"` or `["HA", "NA"]` |
| `vaccine_strain` | bool | — | Vaccine strain filter |
| `source_database` | string | — | `genbank` or `refseq` |
| `lineage` | string \| list | — | SARS-CoV-2 lineage |
| `isolate` | string | — | Isolate name |
| `genotype` | string \| list | — | Genotype |
| `isolation_source` | string | — | Isolation source |
| `env_source` | string \| list | — | Environmental source |
| `submitter_name` | string | — | Submitter name |
| `submitter_institution` | string | — | Submitter institution |
| `gen_mol_type` | string | — | Genomic molecule type |
| `genbank_metadata` | bool | `false` | Fetch GenBank metadata CSV |
| `genbank_batch_size` | int | — | GenBank batch size (default 200) |
| `provirus` | bool | — | Provirus filter |
| `keep_temp` | bool | `false` | Keep intermediate files |
| `verbose` | bool | `true` | gget progress output |

See `gget_virus_docs.md` for full gget.virus documentation.

**Examples**

Ebola surveillance dataset:

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

SARS-CoV-2 reference genome (cached):

```json
{
  "query": "NC_045512.2",
  "is_accession": true,
  "is_sars_cov2": true,
  "confirm_download": true
}
```

With preset:

```json
{ "preset": "ebola_human_complete_since_2014", "confirm_download": true }
```

**Result fields:** `returned`, `output_dir`, `files[]`, `dataset_manifest`, `failures`

> Always check `result.failures` and `command_summary.txt` — gget writes a `FAILED OPERATIONS - RETRY COMMANDS` section when download batches fail.

---

### Virus presets

| Preset | Compatible tools | Description |
|--------|------------------|-------------|
| `sars_cov2_ref_genome` | metadata, count, dataset | SARS-CoV-2 reference accession `NC_045512.2` |
| `ebola_human_complete_africa` | metadata, count | Ebola human complete genomes in Africa |
| `ebola_human_complete_since_2014` | dataset | Ebola human complete since 2014 in Africa |
| `sars_cov2_human_complete` | dataset | SARS-CoV-2 human complete genomes ≥29kb + GenBank metadata |
| `influenza_a_human_complete` | dataset | Influenza A human complete ≤15kb + GenBank metadata |

---

## UniProt tools

Powered by the [UniProt REST API](https://rest.uniprot.org). All search/count/dataset tools default to **`reviewed:true`** (Swiss-Prot). Pass `"include_unreviewed": true` to include TrEMBL. Large organisms (e.g. human `9606`) require narrowing filters for dataset downloads.

### 4. `search_proteins`

Search UniProtKB with cursor pagination. Returns up to `preview_limit` summarized records inline plus `total_available`. **Does not download sequences.**

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | — | Raw UniProt query string |
| `preset` | string | — | Named preset |
| `reviewed_only` | bool | `true` | Append `(reviewed:true)` |
| `include_unreviewed` | bool | `false` | Skip reviewed filter |
| `organism_id` | string | — | NCBI taxonomy ID |
| `gene` | string | — | Gene name |
| `protein_name` | string | — | Protein name |
| `accession` | string | — | UniProt accession |
| `length_min` | int | — | Min sequence length |
| `length_max` | int | — | Max sequence length |
| `preview_limit` | int | `10` | Max inline records (max 100) |

Structured filters are AND-combined with `query`. You can use `query` alone, structured filters alone, or both.

**Examples**

Raw query:

```json
{ "query": "insulin AND organism_id:9606" }
```

Structured filters:

```json
{ "organism_id": "9606", "gene": "INS" }
```

With preset:

```json
{ "preset": "sars_cov2_spike", "preview_limit": 5 }
```

**Result fields:** `returned`, `total_available`, `records[]` (accession, protein_name, gene_names, organism, length, reviewed)

---

### 5. `count_proteins`

Count UniProtKB entries via `X-Total-Results` (single API request). Same filters as `search_proteins`.

**Examples**

```json
{ "preset": "sars_cov2_spike" }
```

```json
{ "organism_id": "9606", "gene": "TP53" }
```

**Result fields:** `count`, `pagination_complete`

---

### 6. `get_protein`

Retrieve a single UniProtKB entry by accession. No search filters needed.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession` | string | **required** | UniProt accession (e.g. `P01308`) |
| `format` | string | `json` | `json`, `fasta`, `txt`, `xml`, `gff`, or `rdf` |

**Examples**

Summarized JSON:

```json
{ "accession": "P01308" }
```

Raw FASTA:

```json
{ "accession": "P01308", "format": "fasta" }
```

**Result fields (json):** `accession`, `record`  
**Result fields (other formats):** `accession`, `format`, `content`

---

### 7. `retrieve_protein_dataset`

Download all matching protein sequences as FASTA to disk. Paginates through every result page. **Requires `confirm_download: true`.**

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | — | Raw UniProt query |
| `preset` | string | — | Named preset |
| `confirm_download` | bool | `false` | **Must be `true`** to run |
| `reviewed_only` | bool | `true` | Append `(reviewed:true)` |
| `include_unreviewed` | bool | `false` | Skip reviewed filter |
| `organism_id` | string | — | NCBI taxonomy ID |
| `gene` | string | — | Gene name |
| `protein_name` | string | — | Protein name |
| `accession` | string | — | UniProt accession |
| `length_min` | int | — | Min sequence length |
| `length_max` | int | — | Max sequence length |
| `outfolder` | string | — | Output directory |

**Examples**

```json
{ "preset": "ebola_vp35", "confirm_download": true }
```

```json
{
  "organism_id": "9606",
  "gene": "INS",
  "confirm_download": true
}
```

**Result fields:** `returned`, `expected_count`, `output_dir`, `files[]`, `fasta_path`

---

### 8. `map_protein_ids`

Map protein identifiers across databases via the UniProt ID mapping service.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ids` | list[string] | **required** | IDs to map (max 5000) |
| `from_db` | string | **required** | Source database |
| `to_db` | string | `UniProtKB` | Target database |
| `list_databases` | bool | `false` | Return supported fields instead of mapping |

Common `from_db` / `to_db` values: `UniProtKB_AC-ID`, `Gene_Name`, `RefSeq_Protein`, `EMBL-Protein`, `UniProtKB`, `UniProtKB-Swiss-Prot`.

**Examples**

Accession → gene name:

```json
{
  "ids": ["P01308"],
  "from_db": "UniProtKB_AC-ID",
  "to_db": "Gene_Name"
}
```

List supported databases:

```json
{ "ids": [], "from_db": "UniProtKB_AC-ID", "list_databases": true }
```

**Result fields:** `job_id`, `mapped_count`, `mappings[]` (from/to pairs), `failed[]`

---

### 9. `get_query_history`

Inspect prior tool runs stored in the local audit log (`KIKI_AUDIT_DIR/manifest_history.jsonl`). Every successful tool call is recorded with its full QueryManifest so agents can verify *how* a result was produced.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query_id` | string | — | Return the most recent entry for this deterministic query hash |
| `tool` | string | — | Filter by tool name when listing |
| `limit` | int | `20` | Max entries when listing (max 500) |

**Examples**

Look up a prior run:

```json
{ "query_id": "a1b2c3d4e5f6g7h8" }
```

List recent virus counts:

```json
{ "tool": "count_virus_sequences", "limit": 10 }
```

**Result fields:** `count`, `entries[]` (each with `recorded_at`, `query_id`, `tool`, full `manifest`)

---

### UniProt presets

| Preset | Description |
|--------|-------------|
| `sars_cov2_spike` | SARS-CoV-2 spike proteins (reviewed) |
| `sars_cov2_nsp12` | SARS-CoV-2 nsp12 (reviewed) |
| `ebola_vp35` | Ebola VP35 (reviewed) |
| `influenza_a_ha` | Influenza A hemagglutinin (reviewed) |
| `human_insulin` | Human insulin (`INS`, reviewed) |
| `human_tp53` | Human TP53 (reviewed) |

---

## Call tools from Python

```bash
# Terminal 1
kiki serve --transport http --port 8000

# Terminal 2
python client.py   # smoke test: get_virus_metadata
pytest             # full test suite (no server needed for most tests)
```

```python
import asyncio
from fastmcp import Client

client = Client("http://127.0.0.1:8000/mcp")

async def main():
    async with client:
        tools = await client.list_tools()
        print([t.name for t in tools])
        # All 8 tools:
        # get_virus_metadata, count_virus_sequences, retrieve_virus_dataset,
        # search_proteins, count_proteins, get_protein,
        # retrieve_protein_dataset, map_protein_ids, get_query_history

        # Virus metadata
        r = await client.call_tool(
            "get_virus_metadata",
            {"query": "NC_045512.2", "is_accession": True},
        )
        print(r.data)

        # UniProt count
        r = await client.call_tool(
            "count_proteins",
            {"preset": "sars_cov2_spike"},
        )
        print(r.data)

asyncio.run(main())
```

---

## Deploy to Prefect Horizon

[Horizon](https://horizon.prefect.io) is managed MCP hosting from the FastMCP team.

**Entrypoint:** `server.py:mcp` (repo root — not `kiki/server.py:mcp`)

```bash
fastmcp inspect server.py:mcp
```

1. Push repo to GitHub
2. Go to [horizon.prefect.io](https://horizon.prefect.io) → connect repo
3. Set entrypoint `server.py:mcp`, deploy
4. URL: `https://YOUR-SERVER-NAME.fastmcp.app/mcp`

**Safe tools for hosted testing:** `get_virus_metadata`, `count_virus_sequences`, `search_proteins`, `count_proteins`, `get_protein`, `map_protein_ids`

**Dataset tools** (`retrieve_virus_dataset`, `retrieve_protein_dataset`) write to the container filesystem — prefer local/self-hosted runs unless you add persistent storage.

---

## Project layout

```
kiki/
  server.py              # FastMCP app
  cli.py                 # kiki serve
  tools/                 # MCP tool definitions (virus + uniprot)
  services/              # gget + UniProt REST clients
  models/                # QueryManifest
  query/                 # normalize, validate, presets
  errors.py              # KikiError codes
tests/
server.py                # Horizon entrypoint (imports kiki.server.mcp)
```

See `notebook.md` for roadmap and `gget_virus_docs.md` for full gget.virus parameter reference.

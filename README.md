# Kiki

MCP server for **deterministic biological data retrieval** — NCBI Virus (via gget), NCBI nucleotide/assembly (E-utilities), Ensembl (direct REST + pinned SQL), and UniProt (REST API).

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

Kiki exposes **24 tools** across six data domains. Use the safe query/count tools for exploration; use dataset tools only when you intend to write files to disk.

| # | Tool | Source | Purpose | Writes files? |
|---|------|--------|---------|---------------|
| 1 | [`get_virus_metadata`](#1-get_virus_metadata) | NCBI Virus / gget | Paginated metadata search + inline preview | No |
| 2 | [`count_virus_sequences`](#2-count_virus_sequences) | NCBI Virus / gget | Count metadata records | No |
| 3 | [`retrieve_virus_dataset`](#3-retrieve_virus_dataset) | NCBI Virus / gget | Full viral genome dataset (FASTA/CSV/JSONL) | **Yes** |
| 4 | [`get_nucleotide_sequence`](#4-get_nucleotide_sequence) | NCBI E-utilities | Single accession FASTA (GenBank/RefSeq) | No |
| 5 | [`get_nucleotide_metadata`](#5-get_nucleotide_metadata) | NCBI E-utilities | Nucleotide record summary | No |
| 6 | [`get_assembly_metadata`](#6-get_assembly_metadata) | NCBI E-utilities | Genome assembly (GCF/GCA) metadata | No |
| 7 | [`retrieve_nucleotide_batch`](#7-retrieve_nucleotide_batch) | NCBI E-utilities | Multi-accession FASTA (+ optional file) | Optional |
| 8 | [`submit_blast_search`](#8-submit_blast_search) | NCBI BLAST URL API | Submit blastn/blastp search → RID | No |
| 9 | [`get_blast_results`](#9-get_blast_results) | NCBI BLAST URL API | Poll once for structured hits | No |
| 10 | [`get_sequence`](#10-get_sequence) | Ensembl REST | Single gene/transcript FASTA | No |
| 11 | [`retrieve_sequence_batch`](#11-retrieve_sequence_batch) | Ensembl REST | Multi-ID sequence fetch (+ optional FASTA file) | Optional |
| 12 | [`search_genes`](#12-search_genes) | Ensembl SQL | Gene search by text terms | No |
| 13 | [`get_gene_info`](#13-get_gene_info) | Ensembl REST | Gene/transcript metadata | No |
| 14 | [`get_reference`](#14-get_reference) | Ensembl FTP | Reference genome FTP metadata | No |
| 15 | [`search_proteins`](#15-search_proteins) | UniProt REST | Paginated protein search + inline preview | No |
| 16 | [`count_proteins`](#16-count_proteins) | UniProt REST | Count matching proteins | No |
| 17 | [`get_protein`](#17-get_protein) | UniProt REST | Single accession lookup | No |
| 18 | [`retrieve_protein_dataset`](#18-retrieve_protein_dataset) | UniProt REST | Bulk FASTA download | **Yes** |
| 19 | [`map_protein_ids`](#19-map_protein_ids) | UniProt REST | Cross-database ID mapping | No |
| 20 | [`count_ena_records`](#20-count_ena_records) | ENA Portal API | Verifiable count via `/count` | No |
| 21 | [`search_ena_records`](#21-search_ena_records) | ENA Portal API | Preview metadata (sequence / read_run) | No |
| 22 | [`get_ena_sequence`](#22-get_ena_sequence) | ENA Browser API | Single sequence by accession (FASTA/EMBL) | No |
| 23 | [`retrieve_ena_dataset`](#23-retrieve_ena_dataset) | ENA Portal + Browser | Full dataset (Portal→Browser for sequences) | **Yes** |
| 24 | [`get_query_history`](#24-get_query_history) | Kiki audit log | Inspect prior QueryManifest runs | No |

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
| `KIKI_ENSEMBL_RELEASE` | Pinned Ensembl release for all Ensembl tools (default `114`) |
| `NCBI_API_KEY` | Optional — forwarded to gget (virus) and NCBI BLAST URL API |
| `NCBI_BLAST_EMAIL` | Optional contact email for NCBI BLAST (`tool=kiki-mcp` is always sent) |

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

## NCBI genome / nucleotide tools (E-utilities)

Inspired by the [Anthropic biology agents blog](blog.md): agents need a **deterministic layer** instead of gluing together E-utilities by hand. These tools wrap NCBI E-utilities for **direct accession lookups** — the safest starting point for genome sequencing records.

Use **virus tools** above when you need NCBI Virus portal filters (taxon, host, geography, collection dates). Use **nucleotide tools** here for known accessions or reference assemblies.

### 4. `get_nucleotide_sequence`

Fetch one GenBank/RefSeq nucleotide record as parsed FASTA via `efetch`.

**Example**

```json
{ "accession": "NC_045512.2" }
```

**Result fields:** `returned`, `records[]` (`header`, `sequence`, `length`)

---

### 5. `get_nucleotide_metadata`

Record summary (title, length, organism, taxid) without downloading sequence.

**Example**

```json
{ "accession": "NC_045512.2" }
```

---

### 6. `get_assembly_metadata`

Genome assembly metadata for GCF/GCA accessions (name, taxid, FTP path).

**Example**

```json
{ "accession": "GCF_000001405.40" }
```

---

### 7. `retrieve_nucleotide_batch`

Fetch up to 50 accessions inline. Pass `confirm_download=true` to write `sequences.fasta` to disk.

**Example**

```json
{ "accessions": ["NC_045512.2"] }
```

---

## NCBI BLAST tools (URL API)

Two-step sequence similarity search via the [NCBI BLAST Common URL API](https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html). Agents submit a search, wait, then poll for structured JSON2 hits — no browser or hand-rolled E-utilities glue.

**v1 databases (curated allowlist):** `core_nt`, `refseq_rna` (blastn); `swissprot`, `refseq_protein` (blastp). `nt` and `nr` are excluded to avoid timeouts and partial results on large DBs.

**Agent workflow**

1. `submit_blast_search` → save `rid`
2. Wait `retry_after_seconds` (≥60s per NCBI policy)
3. `get_blast_results` → if `status: "running"`, wait and retry
4. When `status: "ready"`, use `hits[]` (accession, e-value, identity, alignment coords)

RIDs expire in ~24 hours. Kiki records each call in the audit manifest but does not persist RIDs. Hit lists may drift when NCBI updates database builds.

### 8. `submit_blast_search`

**Example (blastn vs core_nt)**

```json
{
  "program": "blastn",
  "query": "NC_045512.2",
  "database": "core_nt",
  "hitlist_size": 25
}
```

**Result fields:** `rid`, `rtoe_seconds`, `retry_after_seconds`, `program`, `database`, `query_type`

---

### 9. `get_blast_results`

**Example**

```json
{ "rid": "ABCDEF12" }
```

**Result fields:** `status` (`running` \| `ready` \| `failed`), `hits[]`, `num_hits`, `search_stats`, `retry_after_seconds` (when running)

---

## Ensembl tools (pinned release)

Gene and reference genome retrieval via **direct Ensembl APIs** — REST (`e{release}.rest.ensembl.org`), public SQL search, and deterministic FTP URLs. All tools default to **`KIKI_ENSEMBL_RELEASE`** (default `114`) so the same inputs return the same results against that release snapshot.

Pass `release` explicitly to override. Sequences are returned inline as parsed FASTA records (`header`, `sequence`, `length`).

### 10. `get_sequence`

Fetch one Ensembl gene or transcript ID. Set `translate=true` for amino acid sequences; `isoforms=true` for all transcript isoforms of a gene.

**Example**

```json
{ "ensembl_id": "ENSG00000012048" }
```

Transcript with protein sequence:

```json
{ "ensembl_id": "ENST00000357654", "translate": true }
```

---

### 11. `retrieve_sequence_batch`

Fetch multiple Ensembl IDs in one call (max 50). Returns inline FASTA records. Pass `confirm_download=true` to also write `sequences.fasta` to disk.

**Example**

```json
{
  "ensembl_ids": ["ENSG00000012048", "ENSG00000139618"],
  "isoforms": false
}
```

---

### 12. `search_genes`

Search Ensembl by free-text terms. `species` uses `genus_species` format (e.g. `homo_sapiens`).

**Example**

```json
{ "searchwords": "BRCA1", "species": "homo_sapiens", "limit": 5 }
```

Multi-term OR search:

```json
{ "searchwords": ["TP53", "p53"], "species": "homo_sapiens", "andor": "or" }
```

---

### 13. `get_gene_info`

Metadata for one or more Ensembl IDs from Ensembl REST lookup (pinned release).

**Example**

```json
{ "ensembl_id": "ENSG00000012048", "pdb": false }
```

---

### 14. `get_reference`

Reference genome annotation FTP links (GTF, cDNA, DNA, etc.) — metadata only, no download.

**Example**

```json
{ "species": "homo_sapiens", "which": "gtf" }
```

List available species:

```json
{ "list_species": true }
```

---

## UniProt tools

Powered by the [UniProt REST API](https://rest.uniprot.org). All search/count/dataset tools default to **`reviewed:true`** (Swiss-Prot). Pass `"include_unreviewed": true` to include TrEMBL. Large organisms (e.g. human `9606`) require narrowing filters for dataset downloads.

### 15. `search_proteins`

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

### 16. `count_proteins`

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

### 17. `get_protein`

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

### 18. `retrieve_protein_dataset`

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

### 19. `map_protein_ids`

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

## ENA tools (Portal + Browser APIs)

The European Nucleotide Archive exposes two coordinated APIs: the **Portal API** for search and discovery (returns accessions and metadata) and the **Browser API** for record download (FASTA / EMBL by accession). Kiki hardcodes the correct order — Portal first, then Browser — so agents never call the Browser search directly or trust the silent 100000-row Portal default as a complete result. Totals always come from Portal `/count`, and full retrieval uses `limit=0`.

Two result types are supported in v1: `sequence` (assembled or annotated nucleotide sequences, the direct parallel to NCBI Virus) and `read_run` (raw sequencing runs with FASTQ / submitted FTP links). ENA Portal queries must include a narrowing signal such as `tax_eq(<taxid>)`, `tax_tree(<taxid>)`, or an accession field.

### 20. `count_ena_records`

Count ENA records via the Portal `/count` endpoint without downloading them.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result` | string | **required** | `sequence` or `read_run` |
| `query` | string | **required** | ENA Portal query, e.g. `tax_eq(2697049)` |

**Result fields:** `result`, `count`, `pagination_complete`

---

### 21. `search_ena_records`

Preview Portal search results: the verifiable total from `/count` plus up to `preview_limit` inline metadata rows. `pagination_complete` is true only when the preview captured every matching row.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result` | string | **required** | `sequence` or `read_run` |
| `query` | string | **required** | ENA Portal query (must be narrowed) |
| `preview_limit` | int | `25` | Inline rows to return (max 100) |

**Result fields:** `result`, `total_available`, `returned`, `records[]`, `pagination_complete`

---

### 22. `get_ena_sequence`

Fetch one assembled or annotated sequence by accession via the Browser API. This is the documented exception to the Portal-first workflow: when you already have a specific accession, no Portal search is needed.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession` | string | **required** | ENA / INSDC sequence accession, e.g. `BN000065` |
| `format` | string | `fasta` | `fasta` (parsed records) or `embl` (flat file text) |

**Result fields (FASTA):** `format`, `returned`, `records[]` (`header`, `sequence`, `length`)

---

### 23. `retrieve_ena_dataset`

Retrieve a full ENA dataset, coordinating the two APIs deterministically:

- `result="sequence"`: Portal `/count` → Portal `/search` (`limit=0`) → Browser download in 10000-accession chunks (FASTA or EMBL).
- `result="read_run"`: Portal `/count` → Portal `/search` (`limit=0`) returning run metadata and FASTQ / submitted FTP links. No Browser step; FTP file transfer is out of scope (URLs are returned for downstream tooling).

Pass `confirm_download=true` to allow retrievals larger than the safety cap and to write the dataset to disk. Without it, large queries are refused and nothing is written.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result` | string | **required** | `sequence` or `read_run` |
| `query` | string | **required** | ENA Portal query (must be narrowed) |
| `format` | string | `fasta` | `fasta` or `embl` (sequence only) |
| `confirm_download` | bool | `false` | Required to exceed the cap and write files |
| `outfolder` | string | — | Output directory (requires `confirm_download`) |

**Result fields:** `result`, `total_available`, `records[]`/`content`, `accessions`, `api_sequence`, `pagination_complete`

---

### 24. `get_query_history`

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

## VirBench public subset (accuracy proof)

Inspired by the [Anthropic biology agents blog](blog.md) and VirBench (Nasri et al., 2026). Kiki ships a **public query subset** with ground-truth counts (including the blog Ebola example, expected **266**).

```bash
# Safe smoke benchmark (4 queries × 3 runs) — runs in pytest too
python -m kiki.benchmark --safe-only

# Optional: blog dataset query (downloads sequences, slow)
KIKI_RUN_INTEGRATION_BENCHMARK=1 pytest tests/test_virbench_subset.py -m integration
```

Reports: `kiki_output/virbench/*.json` and `*.md`. See [kiki/benchmark/README.md](kiki/benchmark/README.md).

---

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
        # All 24 tools:
        # get_virus_metadata, count_virus_sequences, retrieve_virus_dataset,
        # get_nucleotide_sequence, get_nucleotide_metadata, get_assembly_metadata, retrieve_nucleotide_batch,
        # submit_blast_search, get_blast_results,
        # get_sequence, retrieve_sequence_batch, search_genes, get_gene_info, get_reference,
        # search_proteins, count_proteins, get_protein, retrieve_protein_dataset, map_protein_ids,
        # count_ena_records, search_ena_records, get_ena_sequence, retrieve_ena_dataset,
        # get_query_history

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

**Safe tools for hosted testing:** `get_virus_metadata`, `count_virus_sequences`, `get_nucleotide_sequence`, `get_nucleotide_metadata`, `get_assembly_metadata`, `search_genes`, `get_gene_info`, `get_sequence`, `get_reference`, `search_proteins`, `count_proteins`, `get_protein`, `map_protein_ids`, `count_ena_records`, `search_ena_records`, `get_ena_sequence`

**Dataset tools** (`retrieve_virus_dataset`, `retrieve_protein_dataset`) write to the container filesystem — prefer local/self-hosted runs unless you add persistent storage.

---

## Project layout

```
kiki/
  server.py              # FastMCP app
  cli.py                 # kiki serve
  tools/                 # MCP tool definitions (virus + ensembl + uniprot)
  services/              # gget + UniProt REST clients
  models/                # QueryManifest
  query/                 # normalize, validate, presets
  errors.py              # KikiError codes
tests/
server.py                # Horizon entrypoint (imports kiki.server.mcp)
```

See `notebook.md` for roadmap and `gget_virus_docs.md` for full gget.virus parameter reference.

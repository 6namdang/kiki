# Database retrieval: pagination traps and API call order

Per [note1.md](../note1.md): each wrapper must hardcode pagination loops and multi-API
sequences so agents never re-derive them.

## NCBI Virus (gget)

| Item | Detail |
|------|--------|
| **Service** | `kiki/services/ncbi.py`, `gget_virus.py` |
| **Pagination trap** | NCBI Virus metadata is paged; stopping early under-counts (blog: 106 vs 266 Ebola) |
| **Fix** | `gget.fetch_virus_metadata` paginates internally; Kiki counts full JSONL before preview |
| **Multi-API order** | gget coordinates REST + Datasets + E-utilities + local deferred filters |
| **Agent tools** | `get_virus_metadata`, `count_virus_sequences`, `retrieve_virus_dataset` |

## NCBI E-utilities (nucleotide / assembly)

| Item | Detail |
|------|--------|
| **Service** | `kiki/services/ncbi_eutils.py` |
| **Pagination trap** | `efetch` with many IDs should use history server (`epost` → `efetch`) |
| **Fix** | Batch FASTA: `epost` → `efetch` (WebEnv + QueryKey); max 50 accessions |
| **Assembly trap** | Bare `esearch` term can return wrong assembly |
| **Assembly order** | `esearch` (`[Assembly Accession]` field, `retmax=1`) → `esummary` |
| **Nucleotide metadata** | Single `esummary` by accession (no pagination) |
| **Agent tools** | `get_nucleotide_*`, `get_assembly_metadata`, `retrieve_nucleotide_batch` |

## NCBI BLAST (URL API)

| Item | Detail |
|------|--------|
| **Service** | `kiki/services/ncbi_blast.py` |
| **Pagination trap** | N/A — hit list capped by `HITLIST_SIZE` |
| **Multi-API order** | `CMD=Put` (submit) → `CMD=Get` + `FORMAT_OBJECT=SearchInfo` (status) → `CMD=Get` + `FORMAT_TYPE=JSON2` (results) |
| **Agent tools** | `submit_blast_search` → `get_blast_results` (agent retries when `running`) |

## UniProt REST

| Item | Detail |
|------|--------|
| **Service** | `kiki/services/uniprot.py` |
| **Pagination trap** | Default `size` caps results; `Link: rel="next"` cursor required for full retrieval |
| **Fix** | Cursor loop in `_paginate_json_results` / `iter_fasta_pages` until `X-Total-Results` satisfied |
| **Count** | Single request with `size=1`; read `X-Total-Results` (no cursor loop) |
| **ID mapping order** | `POST /idmapping/run` → poll `GET /idmapping/status/{job}` → `GET /idmapping/results/{job}` |
| **Agent tools** | `search_proteins`, `count_proteins`, `retrieve_protein_dataset`, `map_protein_ids` |

## Ensembl (REST + public SQL)

| Item | Detail |
|------|--------|
| **Service** | `kiki/services/ensembl.py` |
| **Pagination trap** | SQL gene search without `LIMIT` can return unbounded rows |
| **Fix** | `LIMIT` in SQL (default/max `ENSEMBL_MAX_SEARCH_LIMIT`); `pagination_complete` when truncated |
| **Sequence order** | `lookup/id` (gene) → `sequence/id` per transcript when `isoforms` or `translate` |
| **Archived REST** | Per-ID `GET` only (no batch POST) on `e{release}.rest.ensembl.org` |
| **Agent tools** | `search_genes`, `get_gene_info`, `get_sequence`, `retrieve_sequence_batch`, `get_reference` |

## ENA (Portal + Browser APIs)

| Item | Detail |
|------|--------|
| **Service** | `kiki/services/ena.py` |
| **Pagination trap** | Portal `/search` defaults to a 100000-row cap that looks complete but is not |
| **Fix** | Totals from Portal `/count`; full retrieval via Portal `/search?limit=0` (no offset cursor on Portal) |
| **Browser batch limit** | 10000 accessions per Browser request — `browser_fasta_batch` chunks downloads |
| **Sequence order** | Portal `/count` → Portal `/search` (`limit=0`, accession field) → Browser `/fasta` or `/embl` in 10k chunks |
| **read_run order** | Portal `/count` → Portal `/search` (`limit=0`, metadata + FASTQ/submitted FTP links); no Browser step |
| **Single accession** | Browser `/fasta` or `/embl` directly (no Portal step needed) |
| **Scope guard** | `validate_ena_scope` requires a narrowing signal (`tax_eq`, `tax_tree`, or an accession field) |
| **Rate limit** | ENA allows 50 req/s; Kiki throttles to a small inter-request gap and maps HTTP 429 to `UPSTREAM_ERROR` |
| **Agent tools** | `count_ena_records`, `search_ena_records`, `get_ena_sequence`, `retrieve_ena_dataset` |

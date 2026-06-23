import os
from pathlib import Path

SERVER_NAME = "kiki-mcp"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_TRANSPORT = "http"
MAX_METADATA_LIMIT = 100

# Taxon IDs known to have very large NCBI Virus holdings.
LARGE_TAXIDS = frozenset({"2697049", "10239"})

# Default root for dataset downloads (override with KIKI_OUTPUT_DIR).
DEFAULT_OUTPUT_ROOT = Path.cwd() / "kiki_output"

# Append-only manifest audit log (override with KIKI_AUDIT_DIR).
DEFAULT_AUDIT_DIR = Path.cwd() / "kiki_audit"

# UniProt REST API
UNIPROT_BASE_URL = "https://rest.uniprot.org"
UNIPROT_MAX_PAGE_SIZE = 500
UNIPROT_MAX_PREVIEW = 100
UNIPROT_REQUEST_TIMEOUT = 60
UNIPROT_ID_MAPPING_POLL_INTERVAL = 1.5
UNIPROT_ID_MAPPING_TIMEOUT = 120

# Ensembl REST + public SQL (pinned release for reproducibility)
ENSEMBL_MAX_BATCH_SIZE = 50
ENSEMBL_MAX_SEARCH_LIMIT = 100
ENSEMBL_REQUEST_TIMEOUT = 60
# Archived REST host: https://e{release}.rest.ensembl.org — pin via KIKI_ENSEMBL_RELEASE
ENSEMBL_DEFAULT_RELEASE = int(os.environ.get("KIKI_ENSEMBL_RELEASE", "114"))
ENSEMBL_FTP_URL = "https://ftp.ensembl.org/pub/"
ENSEMBL_FTP_URL_NV = "https://ftp.ensemblgenomes.org/pub/"
ENSEMBL_MYSQL_HOST = "mysql-eg-publicsql.ebi.ac.uk"
ENSEMBL_MYSQL_PORTS = (3306, 5306, 4157, 3337, 5316)

# NCBI E-utilities (nucleotide / assembly — deterministic accession lookups)
NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_EUTILS_TIMEOUT = 60
NCBI_MAX_NUCLEOTIDE_BATCH = 50
# NCBI allows ~3 req/s without API key, ~10/s with key — stay under the limit.
NCBI_EUTILS_MIN_INTERVAL = float(os.environ.get("NCBI_EUTILS_MIN_INTERVAL", "0.34"))
NCBI_EUTILS_MIN_INTERVAL_WITH_KEY = float(
    os.environ.get("NCBI_EUTILS_MIN_INTERVAL_WITH_KEY", "0.11")
)

# NCBI BLAST Common URL API (https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html)
NCBI_BLAST_BASE = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
NCBI_BLAST_TIMEOUT = 120
NCBI_BLAST_MIN_INTERVAL = float(os.environ.get("NCBI_BLAST_MIN_INTERVAL", "3.0"))
NCBI_BLAST_MAX_FASTA_BYTES = 50 * 1024
NCBI_BLAST_MAX_HITLIST_SIZE = 500
NCBI_BLAST_NUCL_DATABASES = frozenset({"core_nt", "refseq_rna"})
NCBI_BLAST_PROT_DATABASES = frozenset({"swissprot", "refseq_protein"})
NCBI_BLAST_TOOL_ID = "kiki-mcp"

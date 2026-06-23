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

# UniProt REST API
UNIPROT_BASE_URL = "https://rest.uniprot.org"
UNIPROT_MAX_PAGE_SIZE = 500
UNIPROT_MAX_PREVIEW = 100
UNIPROT_REQUEST_TIMEOUT = 60
UNIPROT_ID_MAPPING_POLL_INTERVAL = 1.5
UNIPROT_ID_MAPPING_TIMEOUT = 120

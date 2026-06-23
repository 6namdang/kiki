from pathlib import Path

SERVER_NAME = "kiki-virus-mcp"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_TRANSPORT = "http"
MAX_METADATA_LIMIT = 100

# Taxon IDs known to have very large NCBI Virus holdings.
LARGE_TAXIDS = frozenset({"2697049", "10239"})

# Default root for dataset downloads (override with KIKI_OUTPUT_DIR).
DEFAULT_OUTPUT_ROOT = Path.cwd() / "kiki_output"

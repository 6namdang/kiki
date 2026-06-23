# Kiki

MCP infrastructure for **deterministic biological sequence data retrieval** — Phase 1: NCBI Virus.

## Quick start

```bash
pip install -e .
kiki serve --transport http --port 8000
```

## Tools

| Tool | Purpose | Downloads? |
|------|---------|------------|
| `get_virus_metadata` | Query NCBI Virus metadata (JSON) | No |
| `retrieve_virus_dataset` | Filtered dataset via `gget.virus` | Yes — requires `confirm_download=true` |

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

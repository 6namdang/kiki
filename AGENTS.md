# Agent instructions (Kiki)

This repo builds **Kiki** — an MCP server for deterministic biological data retrieval.

## Read first

- `CONTRIBUTING.md` — collaboration rules (required)
- `README.md` — all MCP tools and example payloads
- `blog.md` — deterministic retrieval rationale (VirBench / gget virus)
- `gget_virus_docs.md` — full gget.virus parameter reference

## Quick constraints

- Tools return **QueryManifest** via `success_manifest()` / `uniprot_success_manifest()`
- Use **KikiError** + `@tool_safe` for guardrails
- **Never** fail a tool because audit logging failed (use writable-path fallback)
- **Never** run unfiltered large taxon downloads in tests
- Horizon entrypoint: `server.py:mcp`
- Run `pytest` after changes

## Layout

```
kiki/tools/       MCP tools
kiki/services/    gget (virus) + ncbi eutils (genome) + ncbi blast + ensembl REST/SQL + UniProt + ENA (portal/browser)
kiki/query/       presets, validate, normalize
kiki/audit/       provenance, history, deferred filter explanations
server.py         Horizon deploy entrypoint
```

Cursor rules live in `.cursor/rules/` for file-specific guidance.

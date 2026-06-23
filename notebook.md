https://www.anthropic.com/research/agents-in-biology

# Building a Biological Data Infrastructure Layer for AI Agents

## The Problem We're Solving

AI agents like Claude are increasingly being used for scientific research — viral surveillance, drug discovery, outbreak response. But their accuracy is bottlenecked not by reasoning, but by **data retrieval**.

When agents try to fetch raw biological sequence data from databases like NCBI Virus, even the best models (Claude, GPT) achieve only 16–91% accuracy. In biology, the bar is effectively 100% — a missing genome can shift an outbreak's inferred origin by months, or make a therapeutic look effective when it isn't.

The root cause: biological databases were built for humans clicking through browsers, not for machines. There is no reliable, deterministic, agent-friendly interface for raw sequence data.

**We are building that interface.**

---

## What We Are Building

A suite of MCP (Model Context Protocol) servers that wrap the messiest biological sequence databases into clean, deterministic, reproducible tool-calls that any AI agent can invoke reliably.

Think of it as **plumbing** — the layer underneath agent reasoning that makes sure when Claude asks for "all complete Ebola genomes from humans in Africa since 2014," it gets exactly that, every single time.

### The Gap We're Filling

BioMCP (biomcp.org) already exists and does this well for **clinical questions**:
- What drugs treat melanoma?
- What trials are recruiting for BRAF V600E?
- What are known adverse events for pembrolizumab?

Nobody has done this well for **sequence data questions**:
- Give me all complete Ebola genomes matching these exact filters
- Retrieve every SARS-CoV-2 spike protein deposited in the last 30 days
- Build a training dataset of Influenza A sequences for a protein model

The output of a clinical question is an **answer**. The output of a sequence question is a **dataset**. The accuracy requirements are completely different.

---

## Target Databases (Roadmap)

| Phase | Database | What it contains | Why it matters |
|-------|----------|-----------------|----------------|
| 1 | NCBI Virus (via gget) | Viral sequences, metadata | Outbreak surveillance, diagnostic design |
| 2 | SRA (Sequence Read Archive) | Raw sequencing reads | Training data for ML models |
| 3 | ENA (European Nucleotide Archive) | European sequence mirror | Redundancy, global coverage |
| 4 | GISAID | Influenza + SARS-CoV-2 sequences | Pandemic response |
| 5 | Nextstrain | Phylogenetic builds | Outbreak phylogenetics |

---

## Technical Architecture

### What an MCP server is

MCP (Model Context Protocol) is Anthropic's open standard for giving AI agents access to external tools. When you build an MCP server, Claude (and any MCP-compatible agent) can call your functions natively — as if they were built into the model itself.

### Stack

- **Language:** Python
- **MCP framework:** FastMCP (`pip install fastmcp`)
- **Data retrieval:** gget (`pip install gget`) for Phase 1
- **Distribution:** PyPI for local installs, hosted HTTP endpoint for teams

### How it works

```
Agent (Claude / Biomni / GPT)
        ↓  calls tool
  MCP Server (our code)
        ↓  calls
  gget / direct API
        ↓  queries
  NCBI Virus / SRA / ENA
        ↓  returns
  Clean, standardized dataset
        ↑  back to agent
```

### Core design principles

1. **Deterministic** — same query always returns same result
2. **Reproducible** — detailed logs showing exactly how the result was produced
3. **Standardized output** — clean JSON/CSV readable by both humans and machines
4. **Agent-first** — error messages written for agents, not just humans
5. **Auditable** — agents (and humans) can inspect not just what was retrieved, but how

---

## Distribution Model

### Option A: Local install (open source, builds credibility)

Users install and run locally:

```bash
pip install gget-virus-mcp
```

Add to Cursor / Claude Desktop / any MCP client:

```json
{
  "mcpServers": {
    "gget-virus": {
      "command": "gget-virus-mcp",
      "args": ["serve"]
    }
  }
}
```

### Option B: Hosted HTTP endpoint (where the business is)

We host the server. Teams, pharma companies, and agent platforms (Biomni, Edison) hit our URL:

```python
mcp_servers=[{
    "type": "url",
    "url": "https://api.seqmcp.com/mcp"
}]
```

Pricing model: per query, per seat, or enterprise contract.

---

## Learning Path (Before Building)

### Prerequisites
- Python basics: functions, imports, decorators
- Know what an API is conceptually

### Step-by-step

1. **Read FastMCP docs** — https://gofastmcp.com (focus: Getting Started, Tools, Running your server) — 30 min
2. **Read BioMCP source** — https://github.com/genomoncology/biomcp (focus: how tools are defined, error handling, package structure) — 1 hour
3. **Build a trivial MCP server** — a tool that adds two numbers, connect it to Cursor, confirm it works — 1 hour
4. **Wrap gget.virus** — one MCP tool that calls gget.virus with the right parameters — 2 hours
5. **Test against VirBench queries** — use the benchmark from the Anthropic blog to verify accuracy

Total: one focused day to a working v0.

---

## Build Sequence (Phases)

### Phase 1 — Prove it works (Week 1-2)
- [ ] Build MCP server wrapping gget.virus
- [ ] Test against VirBench benchmark (target: match or beat 99.7% GPT-5.5 + gget result)
- [ ] Publish to PyPI
- [ ] Write one great README with a concrete Ebola surveillance example
- [ ] Post to Anthropic MCP connector marketplace

### Phase 2 — Get users (Week 3-4)
- [ ] Share with virology labs and computational biology communities
- [ ] Add SRA retrieval
- [ ] Document reproducibility guarantees explicitly

### Phase 3 — Make it a business (Month 2)
- [ ] Host HTTP endpoint
- [ ] Approach Biomni, Edison Scientific, pharma agent teams
- [ ] Pricing: free tier for academics, paid for commercial/team use

### Phase 4 — Expand (Month 3+)
- [ ] ENA, GISAID, Nextstrain
- [ ] Benchmark every database addition against ground truth
- [ ] Build towards being the "BioMCP for sequence data"

---

## Why This Is Acquirable by Anthropic

The Anthropic blog explicitly states:

> "If we want agents to help with scientific discovery — from outbreak response to drug design to biological modeling — we need to build biological data infrastructure that they can navigate as reliably as humans do."

They identified the problem. They published the benchmark (VirBench). They don't want to build the infrastructure themselves — that's not their core business. But they need it to exist for their scientific agents to be credible.

A team that:
- Owns the deterministic retrieval layer for biological sequence data
- Has benchmark results proving accuracy
- Has adoption from virology labs and agent platforms

...is exactly what Anthropic acquires to make Claude the default agent for scientific discovery.

---

## Key References

- Anthropic blog: "Paving the way for agents in biology" (June 2026)
- VirBench benchmark: Nasri et al., 2026
- gget: https://github.com/pachterlab/gget
- BioMCP (clinical layer, not sequence): https://biomcp.org
- FastMCP: https://gofastmcp.com
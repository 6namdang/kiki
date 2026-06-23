# Building a Biological Data Infrastructure Layer for AI Agents

## The Problem We're Solving

AI agents like Claude are increasingly being used for scientific research — viral surveillance, drug discovery, outbreak response. But their accuracy is bottlenecked not by reasoning, but by **data retrieval**.

When agents try to fetch raw biological sequence data from databases like NCBI Virus, even the best models achieve mean accuracies ranging from **16.9% to 91.3%** (across Claude Sonnet 4, Claude Opus 4.7, Biomni OSS, Edison Analysis, GPT-5.2-pro, and GPT-5.5). In biology, the bar is effectively **100%** — a missing genome can shift an outbreak's inferred origin by months, or make a therapeutic look effective when it isn't.

Real consequences documented in the blog:
- A phylogenetic tree built from incomplete sequences pushed the inferred origin of the 2014 Ebola outbreak back to **1922** (correct answer: January 2014)
- Incomplete sequences caused a different run to miss sequences from Guinea entirely, shifting the outbreak timing to April 2014
- Antibody therapeutic epitope analysis produced **three completely different conclusions** across three identical runs

The root cause: biological databases were built for humans clicking through browsers, not for machines. As Andrej Karpathy put it after spending a week clicking through web dashboards: *"The code was the easiest part. Nobody should have to do this. We must build for agents."*

**We are building that interface.**

---

## Why Agents Fail Today (The Specific Failure Modes)

Understanding exactly why agents fail is the foundation of building something that fixes it. The blog documents four distinct failure modes:

1. **Pagination failures** — agents stop partway through large result sets. Worst for databases with many records: Influenza A, HIV-1, SARS-CoV-2. Results are silently incomplete.
2. **Filter application errors** — agents apply filters incorrectly, causing over-counting. A query returns more records than expected, but wrong ones.
3. **Context-dependent metadata** — fields whose meaning depends on convention or where information happens to be stored (e.g. segment names in segmented viruses, RefSeq vs GenBank record types). Agents have to infer what expert humans already know.
4. **Complexity degradation** — performance degrades significantly beyond 3–4 simultaneous filters. Real-world queries routinely need 5–8.

The insidious part: results can look plausible while being wrong. Sequence retrieval is always the first step in a longer workflow — errors propagate silently downstream.

---

## What We Are Building

A suite of MCP (Model Context Protocol) servers that wrap the messiest biological sequence databases into clean, deterministic, reproducible tool-calls that any AI agent can invoke reliably.

Think of it as **context engines** — the term the Anthropic blog uses — reliable, agent-accessible infrastructure for biological data that sits underneath agent reasoning and makes sure the data layer is boringly correct.

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
| 1 | NCBI Virus (via gget) | Viral sequences + metadata | Outbreak surveillance, diagnostic design |
| 1 | Pathoplexus | Viral sequences (syncs into NCBI Virus) | International sequence sharing, INSDC ecosystem |
| 2 | SRA (Sequence Read Archive) | Raw sequencing reads | Training data for ML models |
| 3 | ENA (European Nucleotide Archive) | European sequence mirror | Redundancy, global coverage |
| 4 | GISAID | Influenza + SARS-CoV-2 sequences | Pandemic response |
| 5 | Nextstrain | Phylogenetic builds | Outbreak phylogenetics |

Note: NCBI Virus is itself a portal over multiple underlying resources — GenBank, RefSeq, and the international INSDC ecosystem (synchronized across the US, Europe, and Japan). gget virus already handles coordinating across these. We wrap gget, not the raw APIs.

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
  gget.virus / direct API
        ↓  queries
  NCBI Virus / Pathoplexus / SRA / ENA
        ↓  returns
  Clean, standardized dataset + audit log
        ↑  back to agent
```

### Core design principles

1. **Deterministic** — same query always returns same result
2. **Reproducible** — detailed logs showing exactly how the result was produced, not just what
3. **Standardized output** — clean JSON/CSV readable by both humans and machines
4. **Agent-first** — error messages and metadata written for agents, not just humans
5. **Auditable** — agents and humans can inspect not just what was retrieved, but how (this is what turns a plausible-looking answer into something checkable)
6. **Handles scale** — correct batching and pagination for large datasets (Influenza A, SARS-CoV-2) without silent truncation

---

## Competitive Landscape

The Anthropic blog names the broader ecosystem of "context engines" and agent harnesses we exist alongside:

- **BioMCP** — clinical/oncology evidence layer (drugs, variants, trials). Not sequence data. Complementary, not competing.
- **ToolUniverse** — general biological tool harness
- **Edison Scientific's Robin** — agent harness connecting agents to biological data sources
- **Biomni** — biomedical agent platform (uses Claude Sonnet 4 as underlying LLM)
- **gget** — the underlying retrieval library we wrap (built by Pachterlab, collaborated with NCBI)

Our position: we are the **MCP-native, agent-first sequence data layer** — the piece none of these have built properly yet.

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

Pricing model: free tier for academics, per query / per seat / enterprise contract for commercial use.

Option A builds credibility and adoption. Option B is the revenue model. Ship A first, then B.

---

## Learning Path (Before Building)

### Prerequisites
- Python basics: functions, imports, decorators (`@something` syntax)
- Know what an API is conceptually
- Have Cursor installed

### Step-by-step

1. **Read FastMCP docs** — https://gofastmcp.com (focus: Getting Started, Tools, Running your server) — 30 min
2. **Read BioMCP source** — https://github.com/genomoncology/biomcp (focus: how tools are defined, error handling, package structure) — 1 hour
3. **Build a trivial MCP server** — a tool that adds two numbers, connect it to Cursor, confirm Claude calls it — 1 hour
4. **Wrap gget.virus** — one MCP tool that calls gget.virus with the right parameters — 2 hours
5. **Test against VirBench queries** — use the benchmark from the Anthropic blog to verify accuracy against ground truth

Total: one focused day to a working v0.

---

## Build Sequence (Phases)

### Phase 1 — Prove it works (Week 1-2)
- [ ] Build MCP server wrapping gget.virus
- [ ] Test against VirBench benchmark — target: match gget virus standalone accuracy (~100%)
- [ ] Handle the four documented failure modes explicitly (pagination, filter errors, metadata, complexity)
- [ ] Publish to PyPI
- [ ] Write one great README with a concrete Ebola surveillance example
- [ ] Post to Anthropic MCP connector marketplace

### Phase 2 — Get users (Week 3-4)
- [ ] Share with virology labs and computational biology communities
- [ ] Add Pathoplexus support
- [ ] Add SRA retrieval
- [ ] Document reproducibility guarantees and audit logs explicitly

### Phase 3 — Make it a business (Month 2)
- [ ] Host HTTP endpoint
- [ ] Approach Biomni, Edison Scientific, pharma agent teams
- [ ] Pricing: free tier for academics, paid for commercial/team use

### Phase 4 — Expand (Month 3+)
- [ ] ENA, GISAID, Nextstrain
- [ ] Benchmark every database addition against ground truth
- [ ] Build towards being the "BioMCP for sequence data"

---

## Why This Could Be Acquired by Anthropic

*Note: this is our strategic inference, not a claim the Anthropic blog makes.*

The blog explicitly states:

> "If we want agents to help with scientific discovery — from outbreak response to drug design to biological modeling — we need to build biological data infrastructure that they can navigate as reliably as humans do."

They identified the problem. They published the benchmark (VirBench). They collaborated with NCBI to build gget virus. But infrastructure tooling is not Anthropic's core business — they build models.

A team that:
- Owns the deterministic retrieval layer for biological sequence data
- Has VirBench benchmark results proving accuracy
- Has adoption from virology labs and agent platforms
- Is the MCP-native entry point for sequence data in Claude's connector ecosystem

...becomes strategically valuable to Anthropic as they push Claude into scientific discovery use cases. Whether that ends in acquisition, deep partnership, or simply being the default tool Claude agents reach for — all three are good outcomes.

---

## Key References

- Anthropic blog: "Paving the way for agents in biology" — Laura Luebbert et al., June 2026
- VirBench benchmark: Nasri et al., 2026 (preprint)
- gget (Pachterlab): https://github.com/pachterlab/gget
- BioMCP (clinical layer): https://biomcp.org
- FastMCP: https://gofastmcp.com
- Pathoplexus: synchronizes into NCBI Virus, part of INSDC ecosystem
- Andrej Karpathy talk: "Software in the era of AI" (referenced in blog)
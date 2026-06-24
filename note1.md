Based on the paper and this conversation, here is precisely what you need to do:

---

**The core problem you are solving**

LLM agents calling biology databases directly produce variable results on identical queries because they re-derive retrieval logic each run. You are hardcoding that logic into deterministic Python wrappers, then exposing them via MCP so agents call the wrapper instead of the database directly.

---

**Step 1: For each database, read the actual API documentation and identify exactly two things:**

1. **Pagination traps** — does the API cap results silently? What parameter forces complete retrieval? (e.g. ENA: `&limit=0`, RCSB PDB: `return_all_hits`)
2. **Multi-API sequences** — does answering one query require calling more than one endpoint in a specific order? What is that exact order?

You cannot skip this step. You cannot guess. You must read the docs for each database.

Databases not yet covered by gget that need this analysis: ENA, DDBJ, UCSC, SRA, InterPro, RCSB PDB search API.

---

**Step 2: For each database, build a Python wrapper that:**

1. Hardcodes the correct pagination loop so it always retrieves complete results
2. Hardcodes the correct multi-API call sequence
3. Takes explicit parameters as input (same as gget style)
4. Returns consistent structured output (JSON)

You are not building an LLM layer here. This is pure deterministic Python.

---

**Step 3: Verify each wrapper produces the same result on three identical calls**

This is the exact test from the paper. If the same parameters return different counts across three runs, the wrapper is not deterministic. Fix it before moving on.

---

**Step 4: Build gget extensions or standalone modules**

Since you are building on top of gget, you have two options:
- Contribute new modules to gget directly (e.g. `gget ena`, `gget sra`)
- Build a separate package that imports gget and adds the missing wrappers

Decide this before writing code, because it affects how you structure imports and dependencies.

---

**Step 5: Build an MCP server on top of all wrappers**

Each wrapper becomes one MCP tool. Each tool must have:
- A precise natural language description of what it does
- Explicit typed parameters with descriptions
- One deterministic function call underneath

The MCP layer adds nothing to the retrieval logic. It is only an interface so agents can call the wrappers.

---

**What you are NOT doing:**

- You are not building an LLM layer inside the wrappers
- You are not letting agents decide how to paginate
- You are not building a general-purpose biology agent — you are building the retrieval infrastructure that agents sit on top of
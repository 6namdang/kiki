from kiki.errors import ErrorCode, KikiError
from kiki.query.blast import (
    build_blast_params,
    validate_database,
    validate_expect,
    validate_hitlist_size,
    validate_program,
    validate_query,
    validate_rid,
)
from kiki.services.ncbi_blast import get_blast_results_once
from kiki.services.ncbi_blast import submit_blast_search as ncbi_submit_blast_search
from kiki.tools._errors import tool_safe
from kiki.tools.blast._helpers import BLAST_RID_NOTE, blast_success_manifest


def register_blast_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def submit_blast_search(
        program: str,
        query: str,
        database: str | None = None,
        expect: float | None = None,
        hitlist_size: int | None = None,
        word_size: int | None = None,
        filter: str | None = None,
    ) -> dict:
        """Submit an NCBI BLAST search and receive a Request ID (RID).

        **When to use:** Sequence similarity search — e.g. "does this outbreak sequence
        match known Ebola genomes?" or "what protein is this?". This is step 1 of 2.
        Always follow with `get_blast_results(rid=...)`.

        **Programs (required):**
        - `blastn` — nucleotide vs nucleotide. Default database: `core_nt`.
          Allowed: `core_nt`, `refseq_rna`.
        - `blastp` — protein vs protein. Default database: `swissprot`.
          Allowed: `swissprot`, `refseq_protein`.

        **Query (required):** Either:
        - NCBI accession (single token), e.g. `NC_045512.2` or `NP_828854.1`
        - Inline FASTA or raw sequence (max 50 KB)

        **Not included in v1:** `nt`, `nr` (too large — timeouts / partial results).

        **Optional parameters** (NCBI defaults apply when omitted):
        - `expect` — E-value threshold (default 10)
        - `hitlist_size` — max hits to keep (default 100, max 500)
        - `word_size` — seed word size
        - `filter` — low-complexity filter (`L`/`mL` for blastn, `F` to disable on blastp)

        **Returns:** `rid`, `rtoe_seconds` (estimated wait), `program`, `database`.
        **RID expires in ~24 hours** — call `get_blast_results` soon; Kiki does not store RIDs.

        **Agent workflow:**
        1. Call this tool → save `rid`
        2. Wait at least `rtoe_seconds` (or 60s minimum per NCBI)
        3. Call `get_blast_results` with the `rid`
        4. If status is `running`, wait 60+ seconds and call `get_blast_results` again
        """
        program = validate_program(program)
        query_text, query_type = validate_query(program, query)
        database = validate_database(program, database)
        expect = validate_expect(expect)
        hitlist_size = validate_hitlist_size(hitlist_size)

        if word_size is not None and word_size <= 0:
            raise KikiError(
                ErrorCode.INVALID_PARAMETER,
                "word_size must be a positive integer.",
                details={"word_size": word_size},
            )

        params = build_blast_params(
            program=program,
            query=query_text,
            query_type=query_type,
            database=database,
            expect=expect,
            hitlist_size=hitlist_size,
            word_size=word_size,
            filter_value=filter,
        )

        submission = ncbi_submit_blast_search(
            program=program,
            query=query_text,
            database=database,
            expect=expect,
            hitlist_size=hitlist_size,
            word_size=word_size,
            filter_value=filter,
        )

        rtoe = submission.get("rtoe_seconds")
        wait_hint = rtoe if rtoe is not None else 60
        result = {
            "status": "submitted",
            **submission,
            "query_type": query_type,
            "retry_after_seconds": max(wait_hint, 60),
            "rid_note": BLAST_RID_NOTE,
            "next_step": "Call get_blast_results with rid after waiting retry_after_seconds.",
        }

        return blast_success_manifest(
            tool="submit_blast_search",
            params=params,
            query_type="ncbi_blast_submit",
            query_value=query_text,
            result=result,
            engine="ncbi.blast.urlapi",
            operation="blast_submit",
            message=(
                f"Submitted {program} search against {database}. "
                f"RID={submission['rid']}. Wait ~{max(wait_hint, 60)}s then call get_blast_results."
            ),
            provenance_extra={"rid_ephemeral": True, "rid_note": BLAST_RID_NOTE},
        )

    @mcp.tool()
    @tool_safe
    def get_blast_results(rid: str) -> dict:
        """Retrieve NCBI BLAST results for a submitted search (poll once).

        **When to use:** Step 2 after `submit_blast_search`. Pass the `rid` returned
        from submit.

        **This tool polls NCBI exactly once.** If the job is still running you will
        get `status: "running"` — wait at least `retry_after_seconds` (60s) and
        call this tool again with the same `rid`. Do not call more often than once
        per minute for the same RID (NCBI policy).

        **Status values:**
        - `running` — job not finished; retry later
        - `ready` — parseable hits in `hits[]` (accession, e-value, identity, coords)
        - `failed` — job failed or RID expired (~24h); submit a new search

        **RID retention:** Kiki does not persist RIDs. The manifest audit log records
        this call for provenance; save hits from the response if you need them long-term.

        **Determinism note:** Hit lists reflect the NCBI database build at search time
        and may change when databases are updated, even with identical parameters.
        """
        rid = validate_rid(rid)
        params = {"rid": rid}
        result = get_blast_results_once(rid)

        return blast_success_manifest(
            tool="get_blast_results",
            params=params,
            query_type="ncbi_blast_rid",
            query_value=rid,
            result=result,
            engine="ncbi.blast.urlapi",
            operation="blast_results",
            message=result.get("message", f"BLAST status for RID {rid}: {result['status']}."),
            provenance_extra={"rid_ephemeral": True, "rid_note": BLAST_RID_NOTE},
        )

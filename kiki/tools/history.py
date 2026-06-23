from kiki.audit.history import get_manifest_by_query_id, query_history
from kiki.tools._errors import tool_safe


def register_history_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def get_query_history(
        query_id: str | None = None,
        tool: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Inspect prior QueryManifest records from the local audit log.

        Every successful tool call is appended to a JSONL file under KIKI_AUDIT_DIR
        (default: ./kiki_audit/manifest_history.jsonl). Use query_id to retrieve
        the most recent run of a deterministic query, or list recent runs by tool.

        Returns matching history entries with full manifest snapshots so agents
        can verify how a prior result was produced.
        """
        if query_id:
            entry = get_manifest_by_query_id(query_id)
            entries = [entry] if entry else []
        else:
            entries = query_history(tool=tool, limit=limit)

        return {
            "success": True,
            "tool": "get_query_history",
            "result": {
                "count": len(entries),
                "entries": entries,
            },
            "message": f"Returned {len(entries)} audit history entr{'y' if len(entries) == 1 else 'ies'}.",
        }

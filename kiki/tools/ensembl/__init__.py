from kiki.tools.ensembl.lookup import register_ensembl_lookup_tools
from kiki.tools.ensembl.reference import register_ensembl_reference_tools
from kiki.tools.ensembl.sequence import register_ensembl_sequence_tools


def register_ensembl_tools(mcp) -> None:
    register_ensembl_sequence_tools(mcp)
    register_ensembl_lookup_tools(mcp)
    register_ensembl_reference_tools(mcp)

from kiki.tools.uniprot.count import register_uniprot_count_tools
from kiki.tools.uniprot.dataset import register_uniprot_dataset_tools
from kiki.tools.uniprot.get import register_uniprot_get_tools
from kiki.tools.uniprot.mapping import register_uniprot_mapping_tools
from kiki.tools.uniprot.search import register_uniprot_search_tools


def register_uniprot_tools(mcp) -> None:
    register_uniprot_search_tools(mcp)
    register_uniprot_count_tools(mcp)
    register_uniprot_get_tools(mcp)
    register_uniprot_dataset_tools(mcp)
    register_uniprot_mapping_tools(mcp)

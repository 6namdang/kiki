from kiki.tools.count import register_count_tools
from kiki.tools.dataset import register_dataset_tools
from kiki.tools.metadata import register_metadata_tools
from kiki.tools.uniprot import register_uniprot_tools

__all__ = ["register_all_tools"]


def register_all_tools(mcp) -> None:
    register_metadata_tools(mcp)
    register_count_tools(mcp)
    register_dataset_tools(mcp)
    register_uniprot_tools(mcp)

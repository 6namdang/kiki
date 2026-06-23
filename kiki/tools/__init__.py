from kiki.tools.dataset import register_dataset_tools
from kiki.tools.metadata import register_metadata_tools

__all__ = ["register_all_tools"]


def register_all_tools(mcp) -> None:
    register_metadata_tools(mcp)
    register_dataset_tools(mcp)

from kiki.tools.blast import register_blast_tools
from kiki.tools.count import register_count_tools
from kiki.tools.dataset import register_dataset_tools
from kiki.tools.ena import register_ena_tools
from kiki.tools.ensembl import register_ensembl_tools
from kiki.tools.genome import register_genome_tools
from kiki.tools.history import register_history_tools
from kiki.tools.metadata import register_metadata_tools
from kiki.tools.uniprot import register_uniprot_tools

__all__ = ["register_all_tools"]


def register_all_tools(mcp) -> None:
    register_metadata_tools(mcp)
    register_count_tools(mcp)
    register_dataset_tools(mcp)
    register_genome_tools(mcp)
    register_blast_tools(mcp)
    register_ena_tools(mcp)
    register_ensembl_tools(mcp)
    register_uniprot_tools(mcp)
    register_history_tools(mcp)

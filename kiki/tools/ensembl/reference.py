from kiki.services.gget_ensembl import fetch_reference
from kiki.tools._errors import tool_safe
from kiki.tools.ensembl._helpers import ensembl_success_manifest


def register_ensembl_reference_tools(mcp) -> None:
    @mcp.tool()
    @tool_safe
    def get_reference(
        species: str | None = None,
        which: str | list[str] = "all",
        release: int | None = None,
        list_species: bool = False,
        list_iv_species: bool = False,
        ftp: bool = False,
    ) -> dict:
        """Fetch Ensembl reference genome annotation FTP links via gget.ref.

        Returns FTP URLs and release metadata for GTF, cDNA, DNA, CDS, etc.
        Use list_species=true to list available species. Does not download files.
        which can be 'all', 'gtf', 'cdna', 'dna', 'cds', 'ncrna', 'pep', or a list.
        """
        params = {
            "species": species,
            "which": which,
            "list_species": list_species,
            "list_iv_species": list_iv_species,
            "ftp": ftp,
        }
        if release is not None:
            params["release"] = release

        payload = fetch_reference(
            species,
            which=which,
            release=release,
            list_species=list_species,
            list_iv_species=list_iv_species,
            ftp=ftp,
        )

        if list_species or list_iv_species:
            query_type = "ensembl_species_list"
            query_value = "invertebrates" if list_iv_species else "vertebrates"
            message = "Returned available Ensembl species."
        else:
            query_type = "ensembl_reference"
            query_value = species or ""
            message = f"Returned reference genome metadata for {species}."

        return ensembl_success_manifest(
            tool="get_reference",
            params={key: value for key, value in params.items() if value is not None},
            query_type=query_type,
            query_value=query_value,
            result=payload,
            engine="gget.ref",
            operation="reference_metadata",
            message=message,
        )

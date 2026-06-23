"""gget Ensembl wrappers for sequence, search, info, and reference retrieval."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gget

from kiki.errors import ErrorCode, KikiError


def normalize_ensembl_ids(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        ids = [part.strip() for part in value.replace(",", " ").split() if part.strip()]
    else:
        ids = [item.strip() for item in value if item and str(item).strip()]
    if not ids:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "At least one Ensembl ID is required.")
    return ids


def parse_fasta_blocks(blocks: list[str]) -> list[dict[str, Any]]:
    """Parse gget.seq output — headers and sequence may be in separate blocks."""
    records: list[dict[str, Any]] = []
    index = 0
    while index < len(blocks):
        block = str(blocks[index]).strip()
        if not block:
            index += 1
            continue

        lines = block.split("\n")
        if lines[0].startswith(">"):
            header = lines[0]
            sequence = "".join(line.strip() for line in lines[1:] if line.strip())
            if not sequence and index + 1 < len(blocks):
                next_block = str(blocks[index + 1]).strip()
                if next_block and not next_block.startswith(">"):
                    sequence = "".join(
                        line.strip() for line in next_block.split("\n") if line.strip()
                    )
                    index += 1
            records.append(
                {
                    "header": header,
                    "sequence": sequence,
                    "length": len(sequence),
                }
            )
        else:
            sequence = "".join(line.strip() for line in lines if line.strip())
            records.append(
                {
                    "header": ">unknown",
                    "sequence": sequence,
                    "length": len(sequence),
                }
            )
        index += 1
    return records


def _raise_if_empty(result: Any, *, message: str) -> None:
    if result is None:
        raise KikiError(ErrorCode.NOT_FOUND, message)
    if isinstance(result, list) and not result:
        raise KikiError(ErrorCode.NOT_FOUND, message)
    if isinstance(result, dict) and not result:
        raise KikiError(ErrorCode.NOT_FOUND, message)


def fetch_sequences(
    ens_ids: str | list[str],
    *,
    translate: bool = False,
    isoforms: bool = False,
    transcribe: bool | None = None,
    seqtype: str | None = None,
) -> list[dict[str, Any]]:
    ids = normalize_ensembl_ids(ens_ids)
    kwargs: dict[str, Any] = {
        "translate": translate,
        "isoforms": isoforms,
        "save": False,
        "verbose": False,
    }
    if transcribe is not None:
        kwargs["transcribe"] = transcribe
    if seqtype is not None:
        kwargs["seqtype"] = seqtype

    try:
        raw = gget.seq(ids[0] if len(ids) == 1 else ids, **kwargs)
    except Exception as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"gget.seq failed: {exc}",
            details={"ensembl_ids": ids},
        ) from exc

    _raise_if_empty(raw, message=f"No sequences returned for Ensembl ID(s): {', '.join(ids)}.")
    blocks = raw if isinstance(raw, list) else [raw]
    return parse_fasta_blocks(blocks)


def write_fasta(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record["header"])
            if not record["header"].endswith("\n"):
                handle.write("\n")
            sequence = record["sequence"]
            for index in range(0, len(sequence), 80):
                handle.write(sequence[index : index + 80])
                handle.write("\n")


def search_genes(
    searchwords: str | list[str],
    species: str,
    *,
    id_type: str = "gene",
    seqtype: str | None = None,
    andor: str = "or",
    limit: int | None = 20,
    release: int | None = None,
) -> dict[str, Any]:
    if isinstance(searchwords, str):
        terms = [searchwords.strip()] if searchwords.strip() else []
    else:
        terms = [word.strip() for word in searchwords if word and str(word).strip()]
    if not terms:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "searchwords is required.")
    if not species or not species.strip():
        raise KikiError(ErrorCode.INVALID_PARAMETER, "species is required (e.g. homo_sapiens).")

    kwargs: dict[str, Any] = {
        "searchwords": terms if len(terms) > 1 else terms[0],
        "species": species.strip(),
        "id_type": id_type,
        "andor": andor,
        "json": True,
        "save": False,
        "verbose": False,
    }
    if seqtype is not None:
        kwargs["seqtype"] = seqtype
    if limit is not None:
        kwargs["limit"] = limit
    if release is not None:
        kwargs["release"] = release

    try:
        raw = gget.search(**kwargs)
    except Exception as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"gget.search failed: {exc}",
            details={"searchwords": terms, "species": species},
        ) from exc

    records = raw if isinstance(raw, list) else []
    return {
        "returned": len(records),
        "records": records,
    }


def fetch_gene_info(
    ens_ids: str | list[str],
    *,
    ncbi: bool = True,
    uniprot: bool = True,
    pdb: bool = False,
    ensembl_only: bool = False,
    expand: bool = False,
) -> dict[str, Any]:
    ids = normalize_ensembl_ids(ens_ids)
    try:
        raw = gget.info(
            ids[0] if len(ids) == 1 else ids,
            json=True,
            save=False,
            verbose=False,
            ncbi=ncbi,
            uniprot=uniprot,
            pdb=pdb,
            ensembl_only=ensembl_only,
            expand=expand,
        )
    except Exception as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"gget.info failed: {exc}",
            details={"ensembl_ids": ids},
        ) from exc

    _raise_if_empty(raw, message=f"No metadata returned for Ensembl ID(s): {', '.join(ids)}.")
    if not isinstance(raw, dict):
        raw = {ids[0]: raw}
    return {
        "returned": len(raw),
        "records": raw,
    }


def fetch_reference(
    species: str | None = None,
    *,
    which: str | list[str] = "all",
    release: int | None = None,
    list_species: bool = False,
    list_iv_species: bool = False,
    ftp: bool = False,
) -> dict[str, Any]:
    if not list_species and not list_iv_species and (not species or not species.strip()):
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "species is required unless list_species or list_iv_species is true.",
        )

    kwargs: dict[str, Any] = {
        "which": which,
        "save": False,
        "verbose": False,
        "list_species": list_species,
        "list_iv_species": list_iv_species,
        "ftp": ftp,
    }
    if species:
        kwargs["species"] = species.strip()
    if release is not None:
        kwargs["release"] = release

    try:
        raw = gget.ref(**kwargs)
    except Exception as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"gget.ref failed: {exc}",
            details={"species": species, "which": which},
        ) from exc

    _raise_if_empty(raw, message="No reference genome metadata returned.")
    if isinstance(raw, dict):
        return {"references": raw}
    return {"references": {"result": raw}}

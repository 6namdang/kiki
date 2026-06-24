"""Direct Ensembl REST + pinned public SQL client (no gget).

All calls target a fixed Ensembl release (``KIKI_ENSEMBL_RELEASE`` / ``release`` param)
so the same inputs yield the same outputs against that release snapshot.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import mysql.connector
import requests

from kiki.config import (
    ENSEMBL_FTP_URL,
    ENSEMBL_MAX_SEARCH_LIMIT,
    ENSEMBL_MYSQL_HOST,
    ENSEMBL_MYSQL_PORTS,
    ENSEMBL_REQUEST_TIMEOUT,
)
from kiki.errors import ErrorCode, KikiError
from kiki.query.ensembl import resolve_ensembl_release
from kiki.services.pagination import pagination_meta

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "kiki-mcp/0.1 (https://github.com/kiki)",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
)

_KNOWN_CORE_DB: dict[tuple[str, int], str] = {
    ("homo_sapiens", 114): "homo_sapiens_core_114_38",
    ("mus_musculus", 114): "mus_musculus_core_114_39",
}


def normalize_ensembl_ids(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        ids = [part.strip() for part in value.replace(",", " ").split() if part.strip()]
    else:
        ids = [item.strip() for item in value if item and str(item).strip()]
    if not ids:
        raise KikiError(ErrorCode.INVALID_PARAMETER, "At least one Ensembl ID is required.")
    return ids


def strip_ensembl_version(ensembl_id: str) -> str:
    if ensembl_id.startswith("ENS") and "." in ensembl_id:
        return ensembl_id.split(".", 1)[0]
    return ensembl_id


def rest_base_url(release: int) -> str:
    return f"https://e{release}.rest.ensembl.org"


def _request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    try:
        response = SESSION.request(
            method,
            url,
            params=params,
            json=json_body,
            timeout=ENSEMBL_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "Ensembl REST request failed.",
            details={"url": url, "error": str(exc)},
        ) from exc

    if response.status_code == 404:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            "Ensembl resource not found.",
            details={"url": url, "status": 404},
        )
    if response.status_code >= 400:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            f"Ensembl returned HTTP {response.status_code}.",
            details={"url": url, "body": response.text[:500]},
        )
    return response.json()


def parse_fasta_blocks(blocks: list[str]) -> list[dict[str, Any]]:
    """Parse FASTA-style blocks into header/sequence/length records."""
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


def _sequence_records_from_rest(items: list[dict[str, Any]], *, header_prefix: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in items:
        seq_id = item.get("id") or item.get("query") or header_prefix
        desc = item.get("desc") or ""
        header = f">{seq_id} {desc}".strip()
        sequence = item.get("seq") or ""
        records.append({"header": header, "sequence": sequence, "length": len(sequence)})
    return records


def _lookup_single(ensembl_id: str, *, release: int, expand: bool) -> dict[str, Any] | None:
    base = rest_base_url(release)
    params = {"expand": 1} if expand else None
    try:
        return _request_json("GET", f"{base}/lookup/id/{ensembl_id}", params=params)
    except KikiError as exc:
        if exc.code == ErrorCode.NOT_FOUND:
            return None
        raise


def _lookup_ids(ids: list[str], *, release: int, expand: bool = True) -> dict[str, Any]:
    """Lookup Ensembl IDs via per-ID GET (works on archived release hosts)."""
    found: dict[str, Any] = {}
    for raw_id in ids:
        clean_id = strip_ensembl_version(raw_id)
        item = _lookup_single(clean_id, release=release, expand=expand)
        if item is None and expand:
            item = _lookup_single(clean_id, release=release, expand=False)
        if item is not None:
            found[clean_id] = item
    return found


def _fetch_nucleotide_sequences(ids: list[str], *, release: int) -> list[dict[str, Any]]:
    base = rest_base_url(release)
    records: list[dict[str, Any]] = []
    for raw_id in ids:
        clean_id = strip_ensembl_version(raw_id)
        item = _request_json(
            "GET",
            f"{base}/sequence/id/{clean_id}",
            params={"type": "genomic"},
        )
        records.extend(_sequence_records_from_rest([item], header_prefix=clean_id))
    return records


def _fetch_protein_sequences(transcript_ids: list[str], *, release: int) -> list[dict[str, Any]]:
    base = rest_base_url(release)
    records: list[dict[str, Any]] = []
    for transcript_id in transcript_ids:
        clean_id = strip_ensembl_version(transcript_id)
        item = _request_json("GET", f"{base}/sequence/id/{clean_id}", params={"type": "protein"})
        records.extend(_sequence_records_from_rest([item], header_prefix=clean_id))
    return records


def _transcript_ids_for_gene(lookup: dict[str, Any], *, isoforms: bool) -> list[str]:
    if not isoforms:
        canonical = lookup.get("canonical_transcript")
        if canonical:
            return [strip_ensembl_version(str(canonical))]
        return []
    transcripts = lookup.get("Transcript") or []
    ids: list[str] = []
    for transcript in transcripts:
        if isinstance(transcript, dict) and transcript.get("id"):
            ids.append(strip_ensembl_version(str(transcript["id"])))
    return ids


def fetch_sequences(
    ens_ids: str | list[str],
    *,
    translate: bool = False,
    isoforms: bool = False,
    release: int | None = None,
    transcribe: bool | None = None,
    seqtype: str | None = None,
) -> list[dict[str, Any]]:
    if seqtype is not None:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "seqtype is deprecated; use translate=true for protein sequences.",
        )
    if transcribe is not None:
        translate = transcribe

    ids = normalize_ensembl_ids(ens_ids)
    ens_release = resolve_ensembl_release(release)
    records: list[dict[str, Any]] = []

    for ensembl_id in ids:
        clean_id = strip_ensembl_version(ensembl_id)
        if translate:
            lookup = _lookup_ids([clean_id], release=ens_release, expand=True)
            gene = lookup.get(clean_id)
            if not gene:
                continue
            object_type = str(gene.get("object_type", ""))
            if object_type == "Gene":
                transcript_ids = _transcript_ids_for_gene(gene, isoforms=isoforms)
            elif object_type == "Transcript":
                transcript_ids = [clean_id]
            else:
                continue
            records.extend(_fetch_protein_sequences(transcript_ids, release=ens_release))
            continue

        if isoforms:
            lookup = _lookup_ids([clean_id], release=ens_release, expand=True)
            gene = lookup.get(clean_id)
            if not gene or str(gene.get("object_type", "")) != "Gene":
                records.extend(_fetch_nucleotide_sequences([clean_id], release=ens_release))
                continue
            transcript_ids = _transcript_ids_for_gene(gene, isoforms=True)
            for transcript_id in transcript_ids:
                records.extend(_fetch_nucleotide_sequences([transcript_id], release=ens_release))
        else:
            records.extend(_fetch_nucleotide_sequences([clean_id], release=ens_release))

    if not records:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"No sequences returned for Ensembl ID(s): {', '.join(ids)}.",
            details={"ensembl_ids": ids, "release": ens_release},
        )
    return records


def write_fasta(records: list[dict[str, Any]], path: Any) -> None:
    from pathlib import Path

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record["header"])
            if not record["header"].endswith("\n"):
                handle.write("\n")
            sequence = record["sequence"]
            for index in range(0, len(sequence), 80):
                handle.write(sequence[index : index + 80])
                handle.write("\n")


def _normalize_species(species: str) -> str:
    normalized = species.strip().lower().replace("/", "")
    if normalized == "human":
        return "homo_sapiens"
    if normalized == "mouse":
        return "mus_musculus"
    return normalized


def _resolve_core_database(species: str, release: int) -> str:
    species = _normalize_species(species)
    cached = _KNOWN_CORE_DB.get((species, release))
    if cached:
        return cached

    listing_url = f"{ENSEMBL_FTP_URL}release-{release}/mysql/"
    try:
        response = SESSION.get(listing_url, timeout=ENSEMBL_REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "Failed to list Ensembl MySQL databases for release.",
            details={"release": release, "error": str(exc)},
        ) from exc

    matches = [
        name
        for name in re.findall(r'href="([^"]+_core_\d+_\d+)/"', response.text)
        if species in name
    ]
    if not matches:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"Species '{species}' not found for Ensembl release {release}.",
            details={"species": species, "release": release},
        )
    if len(matches) > 1 and species == "homo_sapiens":
        return f"homo_sapiens_core_{release}_38"
    if len(matches) > 1 and species == "mus_musculus":
        return f"mus_musculus_core_{release}_39"
    return sorted(matches)[0]


def _mysql_connection(database: str) -> mysql.connector.MySQLConnection:
    last_error: Exception | None = None
    for port in ENSEMBL_MYSQL_PORTS:
        try:
            return mysql.connector.connect(
                host=ENSEMBL_MYSQL_HOST,
                database=database,
                user="anonymous",
                password="",
                port=port,
            )
        except mysql.connector.Error as exc:
            last_error = exc
    raise KikiError(
        ErrorCode.UPSTREAM_ERROR,
        "Could not connect to Ensembl public MySQL.",
        details={"database": database, "error": str(last_error)},
    )


def _search_url(species: str, release: int) -> str:
    clean_db = species if "core" in species else _normalize_species(species)
    if "core" not in clean_db:
        clean_db = _resolve_core_database(clean_db, release)
        clean_db = "_".join(clean_db.split("_")[:2]).replace("_core", "")
    return f"https://www.ensembl.org/{clean_db}/Gene/Summary?g="


def search_genes(
    searchwords: str | list[str],
    species: str,
    *,
    id_type: str = "gene",
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

    ens_release = resolve_ensembl_release(release)
    species_norm = _normalize_species(species)
    database = (
        species_norm
        if "core" in species_norm
        else _resolve_core_database(species_norm, ens_release)
    )

    effective_limit = min(limit if limit is not None else ENSEMBL_MAX_SEARCH_LIMIT, ENSEMBL_MAX_SEARCH_LIMIT)
    sql_limit = effective_limit + 1

    id_type = id_type.lower()
    table = "gene" if id_type == "gene" else "transcript"
    id_col = "gene.stable_id" if id_type == "gene" else "transcript.stable_id"
    desc_col = "gene.description" if id_type == "gene" else "transcript.description"
    from_clause = "gene" if id_type == "gene" else "transcript"
    attrib_join = (
        "LEFT JOIN gene_attrib ON gene.gene_id = gene_attrib.gene_id"
        if id_type == "gene"
        else "LEFT JOIN transcript_attrib ON transcript.transcript_id = transcript_attrib.transcript_id"
    )
    attrib_col = (
        "gene_attrib.value" if id_type == "gene" else "transcript_attrib.value"
    )

    connection = _mysql_connection(database)
    try:
        cursor = connection.cursor(dictionary=True)
        frames: list[list[dict[str, Any]]] = []
        for term in terms:
            like = f"%{term}%"
            query = f"""
            SELECT {id_col} AS ensembl_id,
                   xref.display_label AS gene_name,
                   {desc_col} AS ensembl_description,
                   xref.description AS ext_ref_description,
                   {from_clause}.biotype AS biotype,
                   external_synonym.synonym AS synonym
            FROM {from_clause}
            LEFT JOIN xref ON {from_clause}.display_xref_id = xref.xref_id
            LEFT JOIN external_synonym ON {from_clause}.display_xref_id = external_synonym.xref_id
            {attrib_join}
            WHERE ({desc_col} LIKE %s OR xref.description LIKE %s OR xref.display_label LIKE %s
                   OR external_synonym.synonym LIKE %s OR {attrib_col} LIKE %s)
            ORDER BY ensembl_id
            LIMIT {sql_limit}
            """
            cursor.execute(query, (like, like, like, like, like))
            frames.append(cursor.fetchall())
    finally:
        connection.close()

    if not frames:
        meta = pagination_meta(total_available=0, retrieved=0, pages_fetched=0, complete=True)
        return {"returned": 0, "records": [], "release": ens_release, **meta}

    if andor == "and":
        id_sets = [ {row["ensembl_id"] for row in frame} for frame in frames ]
        keep_ids = set.intersection(*id_sets) if id_sets else set()
        merged = [row for row in frames[0] if row["ensembl_id"] in keep_ids]
    else:
        merged: list[dict[str, Any]] = []
        for frame in frames:
            merged.extend(frame)

    grouped: dict[str, dict[str, Any]] = {}
    synonyms: dict[str, set[str | None]] = defaultdict(set)
    for row in merged:
        ens_id = row["ensembl_id"]
        if ens_id not in grouped:
            grouped[ens_id] = {
                "ensembl_id": ens_id,
                "gene_name": row.get("gene_name"),
                "ensembl_description": row.get("ensembl_description"),
                "ext_ref_description": row.get("ext_ref_description"),
                "biotype": row.get("biotype"),
            }
        synonyms[ens_id].add(row.get("synonym"))

    records: list[dict[str, Any]] = []
    url_prefix = _search_url(species_norm, ens_release)
    for ens_id in sorted(grouped):
        record = grouped[ens_id]
        syn_list = sorted(
            (item for item in synonyms[ens_id] if item is not None),
            key=str,
        )
        record["synonym"] = syn_list or [None]
        record["url"] = f"{url_prefix}{ens_id}"
        records.append(record)

    truncated = len(records) > effective_limit
    if truncated:
        records = records[:effective_limit]

    meta = pagination_meta(
        total_available=None,
        retrieved=len(records),
        pages_fetched=1,
        complete=not truncated,
    )
    return {
        "returned": len(records),
        "records": records,
        "release": ens_release,
        "limit_applied": effective_limit,
        "truncated": truncated,
        **meta,
        "api_sequence": ["ensembl_sql_search"],
    }


def _normalize_gene_record(ensembl_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    version = payload.get("version")
    ensembl_versioned = (
        f"{payload['id']}.{version}" if version is not None and "id" in payload else payload.get("id")
    )
    record: dict[str, Any] = {
        "ensembl_id": ensembl_versioned,
        "ensembl_gene_name": payload.get("display_name"),
        "ensembl_description": payload.get("description"),
        "species": payload.get("species"),
        "assembly_name": payload.get("assembly_name"),
        "object_type": payload.get("object_type"),
        "biotype": payload.get("biotype"),
        "canonical_transcript": payload.get("canonical_transcript"),
        "seq_region_name": payload.get("seq_region_name"),
        "strand": payload.get("strand"),
        "start": payload.get("start"),
        "end": payload.get("end"),
        "parent_gene": payload.get("Parent"),
    }

    transcripts = []
    for transcript in payload.get("Transcript") or []:
        if not isinstance(transcript, dict):
            continue
        tid = transcript.get("id")
        tver = transcript.get("version")
        transcript_id = f"{tid}.{tver}" if tid and tver is not None else tid
        transcripts.append(
            {
                "transcript_id": transcript_id,
                "transcript_biotype": transcript.get("biotype"),
                "transcript_name": transcript.get("display_name"),
                "transcript_strand": transcript.get("strand"),
                "transcript_start": transcript.get("start"),
                "transcript_end": transcript.get("end"),
            }
        )
    record["all_transcripts"] = transcripts
    return record


def fetch_gene_info(
    ens_ids: str | list[str],
    *,
    release: int | None = None,
    ncbi: bool = True,
    uniprot: bool = True,
    pdb: bool = False,
    ensembl_only: bool = False,
    expand: bool = False,
) -> dict[str, Any]:
    if expand or ensembl_only:
        pass  # kept for MCP signature compatibility

    ids = normalize_ensembl_ids(ens_ids)
    ens_release = resolve_ensembl_release(release)
    lookup = _lookup_ids(ids, release=ens_release, expand=True)

    records: dict[str, Any] = {}
    for ensembl_id in ids:
        clean_id = strip_ensembl_version(ensembl_id)
        payload = lookup.get(clean_id)
        if not payload:
            continue
        record = _normalize_gene_record(clean_id, payload)
        if ncbi or uniprot or pdb:
            record.setdefault("ncbi_gene_id", None)
            record.setdefault("ncbi_description", None)
            record.setdefault("uniprot_id", None)
            record.setdefault("uniprot_description", None)
            record.setdefault("pdb_id", None)
            record.setdefault("synonyms", [])
        records[clean_id] = record

    if not records:
        raise KikiError(
            ErrorCode.NOT_FOUND,
            f"No metadata returned for Ensembl ID(s): {', '.join(ids)}.",
            details={"ensembl_ids": ids, "release": ens_release},
        )

    return {
        "returned": len(records),
        "records": records,
        "release": ens_release,
    }


def _ftp_list_directories(url: str) -> list[str]:
    try:
        response = SESSION.get(url, timeout=ENSEMBL_REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise KikiError(
            ErrorCode.UPSTREAM_ERROR,
            "Failed to read Ensembl FTP directory.",
            details={"url": url, "error": str(exc)},
        ) from exc
    return re.findall(r'href="([^"/]+)/"', response.text)


def _ftp_file_url(base_dir: str, filename: str) -> str:
    return f"{base_dir}{filename}"


def _species_capitalized(species: str) -> str:
    parts = species.split("_")
    return "_".join(part.capitalize() for part in parts)


def fetch_reference(
    species: str | None,
    *,
    which: str | list[str] = "all",
    release: int | None = None,
    list_species: bool = False,
    list_iv_species: bool = False,
    ftp: bool = False,
) -> dict[str, Any]:
    ens_release = resolve_ensembl_release(release)

    if list_species:
        species_list = sorted(_ftp_list_directories(f"{ENSEMBL_FTP_URL}release-{ens_release}/gtf/"))
        dna_list = set(_ftp_list_directories(f"{ENSEMBL_FTP_URL}release-{ens_release}/fasta/"))
        available = sorted(set(species_list) & dna_list)
        return {"species": available, "release": ens_release}

    if list_iv_species:
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "Invertebrate species listing is not yet supported in the direct Ensembl client.",
            details={"release": ens_release},
        )

    if not species or not species.strip():
        raise KikiError(
            ErrorCode.INVALID_PARAMETER,
            "species is required unless list_species or list_iv_species is true.",
        )

    species_norm = _normalize_species(species)
    which_list = [which] if isinstance(which, str) else list(which)
    if "all" in which_list:
        which_list = ["gtf", "cdna", "dna", "cds", "ncrna", "pep"]

    capitalized = _species_capitalized(species_norm)
    assembly = "GRCh38" if species_norm == "homo_sapiens" else "GRCm39"
    payload: dict[str, Any] = {"release": ens_release}
    species_payload: dict[str, Any] = {}

    if "gtf" in which_list:
        filename = f"{capitalized}.{assembly}.{ens_release}.gtf.gz"
        species_payload["annotation_gtf"] = {
            "ftp_url": _ftp_file_url(
                f"{ENSEMBL_FTP_URL}release-{ens_release}/gtf/{species_norm}/",
                filename,
            ),
            "release": ens_release,
        }
    if "cdna" in which_list:
        filename = f"{capitalized}.{assembly}.cdna.all.fa.gz"
        species_payload["transcriptome_cdna"] = {
            "ftp_url": _ftp_file_url(
                f"{ENSEMBL_FTP_URL}release-{ens_release}/fasta/{species_norm}/cdna/",
                filename,
            ),
            "release": ens_release,
        }
    if "dna" in which_list:
        filename = f"{capitalized}.{assembly}.dna.primary_assembly.fa.gz"
        species_payload["genome_dna"] = {
            "ftp_url": _ftp_file_url(
                f"{ENSEMBL_FTP_URL}release-{ens_release}/fasta/{species_norm}/dna/",
                filename,
            ),
            "release": ens_release,
        }
    if "cds" in which_list:
        filename = f"{capitalized}.{assembly}.cds.all.fa.gz"
        species_payload["cds"] = {
            "ftp_url": _ftp_file_url(
                f"{ENSEMBL_FTP_URL}release-{ens_release}/fasta/{species_norm}/cds/",
                filename,
            ),
            "release": ens_release,
        }
    if "pep" in which_list:
        filename = f"{capitalized}.{assembly}.pep.all.fa.gz"
        species_payload["peptide"] = {
            "ftp_url": _ftp_file_url(
                f"{ENSEMBL_FTP_URL}release-{ens_release}/fasta/{species_norm}/pep/",
                filename,
            ),
            "release": ens_release,
        }

    payload["references"] = {species_norm: species_payload}
    if ftp:
        urls = [
            entry["ftp_url"]
            for entry in species_payload.values()
            if isinstance(entry, dict) and entry.get("ftp_url")
        ]
        payload["ftp_urls"] = urls
    return payload

#!/usr/bin/env python3
"""Prepare an explicit 6-control/6-pulpitis sample sheet for GSE77459."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import tarfile
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_metadata(matrix: Path) -> dict[str, list[list[str]]]:
    metadata: dict[str, list[list[str]]] = {}
    with gzip.open(matrix, "rt", encoding="utf-8", newline="") as fh:
        for line in fh:
            if line.startswith("!series_matrix_table_begin"):
                break
            if line.startswith("!Sample_") or line.startswith("!Series_"):
                row = next(csv.reader([line.rstrip("\n")], delimiter="\t"))
                metadata.setdefault(row[0], []).append(row[1:])
    return metadata


def first(metadata: dict[str, list[list[str]]], key: str) -> list[str]:
    rows = metadata.get(key, [])
    return rows[0] if rows else []


def characteristics(metadata: dict[str, list[list[str]]]) -> list[list[str]]:
    return [row for row in metadata.get("!Sample_characteristics_ch1", [])]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--raw-tar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()

    metadata = read_metadata(args.matrix)
    accessions = first(metadata, "!Sample_geo_accession")
    titles = first(metadata, "!Sample_title")
    sources = first(metadata, "!Sample_source_name_ch1")
    organisms = first(metadata, "!Sample_organism_ch1")
    chars = characteristics(metadata)
    if not accessions or len({len(accessions), len(titles), len(sources), len(organisms)}) != 1:
        raise SystemExit("GSE77459 matrix metadata is incomplete or has inconsistent widths")

    char_by_sample = [" | ".join(row[i] for row in chars if i < len(row)) for i in range(len(accessions))]
    rows: list[dict[str, str]] = []
    with tarfile.open(args.raw_tar, "r") as archive:
        members = [member.name for member in archive.getmembers()]
    for i, accession in enumerate(accessions):
        joined = f"{sources[i]} {char_by_sample[i]}".lower()
        if "normal" in joined:
            group = "control"
        elif "inflam" in joined or "pulpitis" in joined:
            group = "case"
        else:
            group = "unresolved"
        matches = [name for name in members if Path(name).name.startswith(accession + "_") and name.endswith(".CEL.gz")]
        if len(matches) != 1:
            raise SystemExit(f"Expected one CEL member for {accession}, found {matches}")
        rows.append({
            "sample_id": accession,
            "geo_accession": accession,
            "group": group,
            "title": titles[i],
            "source": sources[i],
            "organism": organisms[i],
            "characteristics": char_by_sample[i],
            "raw_archive": str(args.raw_tar),
            "raw_cel_member": matches[0],
        })

    groups = {group: sum(row["group"] == group for row in rows) for group in ("control", "case")}
    if groups != {"control": 6, "case": 6}:
        raise SystemExit(f"Unexpected GSE77459 groups: {groups}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sample_sheet = args.output_dir / "GSE77459_samples.csv"
    fields = list(rows[0])
    with sample_sheet.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "schema_version": "1.0",
        "status": "success",
        "dataset_id": "GSE77459",
        "source_url": args.source_url,
        "matrix_path": str(args.matrix),
        "raw_archive_path": str(args.raw_tar),
        "matrix_sha256": sha256(args.matrix),
        "raw_archive_sha256": sha256(args.raw_tar),
        "sample_count": len(rows),
        "groups": groups,
        "platform": "GPL17692 / Affymetrix Human Gene 2.1 ST Array",
        "organism": "Homo sapiens",
        "raw_cel_members": len([m for m in members if m.endswith(".CEL.gz")]),
        "parser": "scripts/prepare_gse77459_metadata.py",
    }
    (args.output_dir / "GSE77459_metadata_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

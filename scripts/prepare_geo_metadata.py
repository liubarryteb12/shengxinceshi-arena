#!/usr/bin/env python3
"""Prepare a reproducible sample sheet from a GEO series matrix.

This script only parses metadata; it does not perform statistical analysis.
It intentionally takes paths as arguments instead of hard-coding them.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import re
import tarfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_quoted_row(line: str) -> list[str]:
    return next(csv.reader([line], delimiter="\t"))


def read_series_metadata(matrix: Path) -> dict[str, list[str]]:
    metadata: dict[str, list[str]] = {}
    with gzip.open(matrix, "rt", encoding="utf-8", newline="") as handle:
        for line in handle:
            if line.startswith("!series_matrix_table_begin"):
                break
            if line.startswith("!Sample_") or line.startswith("!Series_"):
                row = parse_quoted_row(line.rstrip("\n"))
                metadata[row[0]] = row[1:]
    return metadata


def parse_characteristics(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in re.split(r"',\s*'|;\s*", value.strip("' \"")):
        if ":" not in item:
            continue
        key, val = item.split(":", 1)
        result[key.strip()] = val.strip(" '\"")
    return result


def group_from_metadata(title: str, source: str, chars: dict[str, str]) -> str:
    joined = " ".join([title, source, chars.get("", ""), *chars.values()]).lower()
    if "pss" in joined or "patient" in joined:
        return "pSS"
    if "control" in joined or "healthy" in joined:
        return "control"
    return "unresolved"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--raw-tar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()

    metadata = read_series_metadata(args.matrix)
    accessions = metadata.get("!Sample_geo_accession", [])
    titles = metadata.get("!Sample_title", [])
    sources = metadata.get("!Sample_source_name_ch1", [])
    chars = metadata.get("!Sample_characteristics_ch1", [])
    organisms = metadata.get("!Sample_organism_ch1", [])

    if not accessions:
        raise SystemExit("No sample accessions found in series matrix")
    widths = {len(accessions), len(titles), len(sources), len(chars), len(organisms)}
    if len(widths) != 1:
        raise SystemExit(f"Metadata columns have inconsistent lengths: {sorted(widths)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sample_sheet = args.output_dir / f"{args.dataset_id}_samples.csv"
    fields = ["sample_id", "geo_accession", "group", "title", "organism", "gender", "age", "tissue", "raw_archive", "raw_cel_member", "raw_chp_member"]
    rows = []
    for accession, title, source, char_text, organism in zip(accessions, titles, sources, chars, organisms):
        parsed = parse_characteristics(char_text)
        group = group_from_metadata(title, source, parsed)
        rows.append({
            "sample_id": accession,
            "geo_accession": accession,
            "group": group,
            "title": title,
            "organism": organism,
            "gender": parsed.get("gender", ""),
            "age": parsed.get("age", ""),
            "tissue": parsed.get("tissue", ""),
            "raw_archive": str(args.raw_tar),
            "raw_cel_member": f"{accession}.CEL.gz",
            "raw_chp_member": f"{accession}.CHP.gz",
        })

    with sample_sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with tarfile.open(args.raw_tar, "r") as archive:
        members = [member.name for member in archive.getmembers()]
    cel_members = sorted(name for name in members if name.endswith(".CEL.gz"))
    chp_members = sorted(name for name in members if name.endswith(".CHP.gz"))
    accession_set = set(accessions)
    cel_accessions = {Path(name).name.split(".")[0] for name in cel_members}
    chp_accessions = {Path(name).name.split(".")[0] for name in chp_members}

    control = sum(row["group"] == "control" for row in rows)
    pss = sum(row["group"] == "pSS" for row in rows)
    unresolved = sum(row["group"] == "unresolved" for row in rows)
    summary = {
        "dataset_id": args.dataset_id,
        "source_url": args.source_url,
        "matrix_file": str(args.matrix),
        "raw_archive": str(args.raw_tar),
        "matrix_sha256": sha256(args.matrix),
        "raw_archive_sha256": sha256(args.raw_tar),
        "sample_count": len(rows),
        "groups": {"control": control, "pSS": pss, "unresolved": unresolved},
        "balanced_groups": control == pss and unresolved == 0,
        "platform": "GPL570 / Affymetrix Human Genome U133 Plus 2.0",
        "organisms": sorted(set(row["organism"] for row in rows)),
        "raw_archive_members": len(members),
        "cel_members": len(cel_members),
        "chp_members": len(chp_members),
        "all_samples_have_cel": accession_set == cel_accessions,
        "all_samples_have_chp": accession_set == chp_accessions,
        "parser": "scripts/prepare_geo_metadata.py",
    }
    manifest = args.output_dir / f"{args.dataset_id}_metadata_summary.yaml"
    with manifest.open("w", encoding="utf-8") as handle:
        handle.write("schema_version: \"1.0\"\n")
        handle.write("status: success\n")
        for key, value in summary.items():
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, list):
                rendered = "[" + ", ".join(str(x) for x in value) + "]"
            elif isinstance(value, dict):
                handle.write(f"{key}:\n")
                for subkey, subvalue in value.items():
                    handle.write(f"  {subkey}: {subvalue}\n")
                continue
            else:
                rendered = str(value)
            handle.write(f"{key}: {rendered}\n")

    print(f"wrote {sample_sheet}")
    print(f"wrote {manifest}")
    print(f"samples={len(rows)} control={control} pSS={pss} unresolved={unresolved}")
    print(f"raw_archive_members={len(members)} CEL={len(cel_members)} CHP={len(chp_members)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

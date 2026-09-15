#!/usr/bin/env python3
"""Validate the lightweight GSE77459 raw-CEL smoke output."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.workspace.resolve()
    out = root / "analysis/outputs/gse77459_smoke"
    failures = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        print(f"{'PASS' if ok else 'FAIL'}  {label}{(' :: ' + detail) if detail else ''}")
        failures += not ok

    for rel in [
        "inputs/raw/GSE77459/GSE77459_RAW.tar",
        "inputs/raw/GSE77459/metadata/GSE77459_series_matrix.txt.gz",
        "inputs/metadata/GSE77459/GSE77459_samples.csv",
        "analysis/outputs/gse77459_smoke/manifest.yaml",
        "analysis/outputs/gse77459_smoke/run/summary.json",
        "analysis/outputs/gse77459_smoke/records/handoff.md",
        "analysis/outputs/gse77459_smoke/records/checkpoint.yaml",
    ]:
        path = root / rel
        check(rel, path.exists() and path.stat().st_size > 0)
    summary_path = out / "run/summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        check("summary.status", summary.get("status") == "success", str(summary.get("status")))
        check("summary.input_mode", summary.get("input_mode") == "full_raw", str(summary.get("input_mode")))
        check("summary.n_samples", summary.get("n_samples") == 12, str(summary.get("n_samples")))
        check("summary.groups", summary.get("groups") == {"control": 6, "case": 6}, str(summary.get("groups")))
        check("summary.rma", summary.get("rma_status") == "success_oligo_rma", str(summary.get("rma_status")))
        check("summary.limma", summary.get("limma_status") == "success", str(summary.get("limma_status")))
        check("summary.pathway", summary.get("pathway_method_executed") == "limma::goana", str(summary.get("pathway_method_executed")))
        check("platform boundary", "not MAS5" in str(summary.get("absent_filter_method")), str(summary.get("absent_filter_method")))
    else:
        failures += 1
    formats = {p.suffix.lower().lstrip(".") for p in (out / "figures").glob("Figure_1_QC.*")}
    check("Figure_1_QC five formats", formats == {"pdf", "svg", "png", "tiff", "jpg"}, str(sorted(formats)))
    manifest_path = out / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        check("manifest.status", manifest.get("status") == "success", str(manifest.get("status")))
        check("manifest.platform", manifest.get("platform") == "GPL17692", str(manifest.get("platform")))
        check("manifest.tool transparency", "not be called MAS5" in str(manifest.get("method_boundary")), "explicit compatibility note")
    else:
        failures += 1
    if failures:
        print(f"GSE77459 SMOKE VALIDATION: FAIL ({failures} issue(s))")
        return 1
    print("GSE77459 SMOKE VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

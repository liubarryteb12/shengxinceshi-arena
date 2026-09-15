#!/usr/bin/env python3
"""Validate a completed P1 module output using only the standard library."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--module-output", default="analysis/outputs/affymetrix_expression_gse7451")
    args = parser.parse_args()
    root = args.workspace.resolve()
    output = root / args.module_output
    required = [
        output / "manifest.yaml",
        output / "records/qc_report.yaml",
        output / "records/handoff.md",
        output / "records/diff.md",
        output / "records/checkpoint.yaml",
        output / "records/next_tasklist.md",
        output / "run/summary.json",
        root / "analysis/_index/p1_to_p2_evidence.yaml",
        root / "analysis/_index/p1_to_p4_quality.yaml",
    ]
    failures = 0
    for path in required:
        ok = path.exists() and path.stat().st_size > 0
        print(f"{'PASS' if ok else 'FAIL'}  {path.relative_to(root)}")
        failures += not ok
    summary_path = output / "run/summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL  summary JSON: {exc}")
            failures += 1
        else:
            for key in ("n_samples", "filtered_probe_count", "significant_gene_count", "pathway_status", "status"):
                ok = key in summary
                print(f"{'PASS' if ok else 'FAIL'}  summary.{key}")
                failures += not ok
            if summary.get("status") != "success":
                print("FAIL  summary.status is not success")
                failures += 1
    else:
        failures += 1
    figures = {path.suffix.lower().lstrip(".") for path in (output / "figures").glob("Figure_1_QC.*")}
    expected = {"pdf", "svg", "png", "tiff", "jpg"}
    ok = figures == expected
    print(f"{'PASS' if ok else 'FAIL'}  Figure_1_QC five-format set: {sorted(figures)}")
    failures += not ok
    for rel in ("analysis/_index/p1_to_p2_evidence.yaml", "analysis/_index/p1_to_p4_quality.yaml"):
        text = (root / rel).read_text(encoding="utf-8") if (root / rel).exists() else ""
        for marker in ("source_run_id:",):
            ok = marker in text
            print(f"{'PASS' if ok else 'FAIL'}  {rel} :: {marker}")
            failures += not ok
        status_ok = any(f"status: {value}" in text for value in ("success", "partial"))
        print(f"{'PASS' if status_ok else 'FAIL'}  {rel} :: status success/partial")
        failures += not status_ok
    if failures:
        print(f"P1 OUTPUT VALIDATION: FAIL ({failures} issue(s))")
        return 1
    print("P1 OUTPUT VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

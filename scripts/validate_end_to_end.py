#!/usr/bin/env python3
"""Validate the executable P1 -> P2 -> P3 -> P4 handoff without upgrading partial evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ACCEPTED = {"success", "partial"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.workspace.resolve()
    failures = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"PASS  {label}{(' :: ' + detail) if detail else ''}")
        else:
            failures += 1
            print(f"FAIL  {label}{(' :: ' + detail) if detail else ''}")

    def load(rel: str) -> dict:
        path = root / rel
        check(rel, path.exists() and path.stat().st_size > 0)
        if not path.exists():
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            check(f"{rel} YAML", False, str(exc))
            return {}
        check(f"{rel} YAML", isinstance(data, dict))
        return data if isinstance(data, dict) else {}

    def file_check(rel: str) -> None:
        path = root / rel
        check(rel, path.exists() and path.stat().st_size > 0)

    # Input provenance and the P1 semantic run identity.
    for rel in (
        "inputs/migration_log.yaml",
        "inputs/metadata/GSE7451/GSE7451_samples.csv",
        "inputs/raw/GSE7451/GSE7451_RAW.tar",
        "inputs/raw/GSE7451/metadata/GSE7451_series_matrix.txt.gz",
    ):
        file_check(rel)
    summary_path = root / "analysis/outputs/affymetrix_expression_gse7451/run/summary.json"
    file_check("analysis/outputs/affymetrix_expression_gse7451/run/summary.json")
    summary: dict = {}
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run_id = summary.get("run_id")
    check("P1 summary semantic run_id", isinstance(run_id, str) and run_id.startswith("run_"), str(run_id))
    check("P1 summary status", summary.get("status") == "success", str(summary.get("status")))
    check("P1 sample count", summary.get("n_samples") == 20, str(summary.get("n_samples")))
    check("P1 groups", summary.get("groups") == {"control": 10, "pSS": 10}, str(summary.get("groups")))
    check("P1 limma", summary.get("limma_status") == "success", str(summary.get("limma_status")))

    p1_evidence = load("analysis/_index/p1_to_p2_evidence.yaml")
    p1_quality = load("analysis/_index/p1_to_p4_quality.yaml")
    for label, data in (("P1->P2", p1_evidence), ("P1->P4", p1_quality)):
        check(f"{label} status", data.get("status") in ACCEPTED, str(data.get("status")))
        run_detail = "matched " + str(run_id) if data.get("source_run_id") == run_id else f"{data.get('source_run_id')} != {run_id}"
        check(f"{label} run identity", data.get("source_run_id") == run_id, run_detail)

    # P2 contract and declared files.
    p2 = load("02_writing/p2_to_p3_manuscript.yaml")
    p2_quality = load("02_writing/p2_to_p4b_quality.yaml")
    check("P2 status", p2.get("status") in ACCEPTED, str(p2.get("status")))
    p2_detail = "matched " + str(run_id) if p2.get("p1_run_id") == run_id else f"{p2.get('p1_run_id')} != {run_id}"
    check("P2 run identity", p2.get("p1_run_id") == run_id, p2_detail)
    check("P2 quality status", p2_quality.get("status") in ACCEPTED, str(p2_quality.get("status")))
    p2q_detail = "matched " + str(run_id) if p2_quality.get("p1_run_id") == run_id else f"{p2_quality.get('p1_run_id')} != {run_id}"
    check("P2 quality run identity", p2_quality.get("p1_run_id") == run_id, p2q_detail)
    for rel in (
        "02_writing/manuscript/v1/main.md",
        "02_writing/manuscript/v1/main.docx",
        "02_writing/refs/refs.bib",
        "02_writing/figures/Figure_1_QC.png",
    ):
        file_check(rel)

    # P3 contract, artifact and the five-format figure handoff.
    p3 = load("03_typesetting/p3_export_manifest.yaml")
    p3_run = load("03_typesetting/_runs/p3_run.yaml")
    check("P3 status", p3.get("status") in ACCEPTED, str(p3.get("status")))
    p3_detail = "matched " + str(run_id) if p3.get("p1_run_id") == run_id else f"{p3.get('p1_run_id')} != {run_id}"
    p3r_detail = "matched " + str(run_id) if p3_run.get("p1_run_id") == run_id else f"{p3_run.get('p1_run_id')} != {run_id}"
    check("P3 run identity", p3.get("p1_run_id") == run_id, p3_detail)
    check("P3 run record identity", p3_run.get("p1_run_id") == run_id, p3r_detail)
    for rel in (
        "03_typesetting/check_report.md",
        "03_typesetting/output/manuscript.pdf",
        "03_typesetting/output/manuscript_编辑版.docx",
        "03_typesetting/output/manuscript_审稿版.docx",
        "03_typesetting/output/manuscript_安全版.docx",
        "03_typesetting/output/submission_package.zip",
    ):
        file_check(rel)
    report_path = root / "03_typesetting/check_report.md"
    report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    check("P3 F25 five formats", "| F25 五格式齐全 | pass |" in report)

    # P4 remains provisional, but must contain source-aware candidates rather than empty scaffolding.
    recommended = load("04_journal/recommended_journals.yaml")
    p4_quality = load("04_journal/quality_assessment.yaml")
    predatory = load("04_journal/predatory_check.yaml")
    check("P4 recommendation status", recommended.get("status") in ACCEPTED, str(recommended.get("status")))
    candidates = recommended.get("recommended", [])
    check("P4 candidate count", isinstance(candidates, list) and 1 <= len(candidates) <= 3, str(len(candidates) if isinstance(candidates, list) else candidates))
    for index, candidate in enumerate(candidates if isinstance(candidates, list) else [], start=1):
        check(f"P4 candidate {index} source", bool(candidate.get("source")) and candidate.get("source_verified") is True)
        check(f"P4 candidate {index} verification time", bool(candidate.get("verified_at")))
        check(f"P4 candidate {index} uncertain score explicit", candidate.get("total_score") == "待确认")
    check("P4 quality status", p4_quality.get("status") in ACCEPTED, str(p4_quality.get("status")))
    check("P4 predatory check conservative", predatory.get("status") == "partial", str(predatory.get("status")))

    if failures:
        print(f"END-TO-END INTERFACE VALIDATION: FAIL ({failures} issue(s))")
        return 1
    print("END-TO-END INTERFACE VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

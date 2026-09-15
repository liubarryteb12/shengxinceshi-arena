#!/usr/bin/env python3
"""Validate the Round 1 skeleton without requiring third-party packages."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "inputs", "analysis", "02_writing", "03_typesetting", "04_journal",
    "handoff", "checkpoints", "next_tasklist", "logs", "governance",
    "schemas", "quality", "scripts", ".github/workflows",
]

REQUIRED_FILES = [
    "README.md", "workspace.yaml", "docs/architecture.md",
    "governance/meta_principles.yaml", "governance/states.yaml",
    "governance/interface_matrix.yaml", "quality/rules_registry.yaml",
    "quality/round1_acceptance.md",
    "analysis/_index/p1_to_p2_evidence.yaml",
    "analysis/_index/p1_to_p4_quality.yaml",
    "02_writing/p2_to_p3_manuscript.yaml",
    "02_writing/p2_to_p4b_quality.yaml",
    "03_typesetting/check_report.md",
    "04_journal/journal_direction_package.yaml",
    "04_journal/recommended_journals.yaml",
    "04_journal/submission_order.yaml",
    "04_journal/feedback.yaml",
    "analysis/_index/dormant_registry.yaml",
    "02_writing/dormant_registry.yaml",
    "03_typesetting/dormant_registry.yaml",
    "04_journal/dormant_registry.yaml",
]

SOURCE_FILES = [
    "总纲要.txt", "P1纲要.txt", "P2纲要.txt", "P3纲要.txt",
    "P4纲要.txt", "工作安排提示词.txt",
]

CONTRACT_MARKERS = {
    "analysis/_index/p1_to_p2_evidence.yaml": ["contract_id: p1_to_p2_evidence", "evidence:", "methods:", "figures:", "tables:"],
    "analysis/_index/p1_to_p4_quality.yaml": ["contract_id: p1_to_p4_quality", "analysis_summary:", "quality_assessment:", "topic_assessment:"],
    "02_writing/p2_to_p3_manuscript.yaml": ["contract_id: p2_to_p3_manuscript", "structure:", "files:", "figures:", "tables:", "declarations:"],
    "02_writing/p2_to_p4b_quality.yaml": ["contract_id: p2_to_p4b_quality", "quality_assessment:", "topic_assessment:"],
    "04_journal/journal_direction_package.yaml": ["contract_id: journal_direction_package", "topic_judgment:", "journal_direction:", "analysis_requirements:", "writing_constraints:", "typesetting_constraints:"],
}


def check_path(rel: str, is_dir: bool = False) -> bool:
    path = ROOT / rel
    ok = path.is_dir() if is_dir else path.is_file()
    print(f"{'PASS' if ok else 'FAIL'}  {rel}")
    return ok


def main() -> int:
    failures = 0
    if ROOT.name != "shengxinceshi-arena":
        print(f"FAIL  repository basename is {ROOT.name!r}")
        failures += 1
    else:
        print("PASS  repository basename shengxinceshi-arena")

    for rel in REQUIRED_DIRS:
        failures += not check_path(rel, is_dir=True)
    for rel in REQUIRED_FILES:
        failures += not check_path(rel)
    for name in SOURCE_FILES:
        failures += not check_path(f"docs/source/{name}")

    for rel, markers in CONTRACT_MARKERS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for marker in markers:
            ok = marker in text
            print(f"{'PASS' if ok else 'FAIL'}  {rel} :: {marker}")
            failures += not ok

    # JSON schemas must at least be valid JSON.
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            print(f"PASS  JSON schema {path.relative_to(ROOT)}")
        except json.JSONDecodeError as exc:
            print(f"FAIL  JSON schema {path.relative_to(ROOT)} :: {exc}")
            failures += 1

    print()
    if failures:
        print(f"ROUND 1 VALIDATION: FAIL ({failures} issue(s))")
        return 1
    print("ROUND 1 VALIDATION: PASS")
    print("Note: PASS here means the skeleton exists; scientific analyses remain pending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Small P1 guard mutation test: every case must fail before it passes."""
from __future__ import annotations

import json
from pathlib import Path


def has_five_formats(exts: set[str]) -> bool:
    return exts >= {"pdf", "svg", "png", "tiff", "jpg"}


def has_canonical_name(names: set[str]) -> bool:
    return any(name.startswith("Figure_") for name in names)


def dpi_at_least(spec: dict, minimum: int) -> bool:
    return int(spec.get("dpi", 0)) >= minimum


def is_grayscale(spec: dict) -> bool:
    return spec.get("color_mode") == "grayscale_8bit"


def has_vector(spec: dict) -> bool:
    return bool(spec.get("vector_formats"))


def interface_matches(index: dict, expected: str) -> bool:
    return index.get("figure_id") == expected and index.get("path", "").endswith(expected + ".pdf")


def run_case(case_id: str, check, bad_value, good_value) -> dict:
    bad_passed = bool(check(bad_value))
    good_passed = bool(check(good_value))
    return {
        "case_id": case_id,
        "expect_fail": True,
        "caught": not bad_passed and good_passed,
        "verdict": "pass" if not bad_passed and good_passed else "空规",
    }


def main() -> int:
    full_exts = {"pdf", "svg", "png", "tiff", "jpg"}
    cases = [
        run_case("P1-Q1", has_five_formats, full_exts - {"svg"}, full_exts),
        run_case("P1-Q2", has_canonical_name, {"plot.pdf"}, {"Figure_1_QC.pdf"}),
        run_case("P1-Q3", lambda x: dpi_at_least(x, 600), {"dpi": 300}, {"dpi": 600}),
        run_case("P1-Q4", is_grayscale, {"color_mode": "RGB"}, {"color_mode": "grayscale_8bit"}),
        run_case("P1-Q5", has_vector, {"vector_formats": []}, {"vector_formats": ["pdf", "svg"]}),
        run_case("P1-Q6", lambda x: interface_matches(x, "Figure_1_QC"), {"figure_id": "Figure_2", "path": "figures/Figure_2.pdf"}, {"figure_id": "Figure_1_QC", "path": "figures/Figure_1_QC.pdf"}),
    ]
    result = {
        "n_pass": sum(case["caught"] for case in cases),
        "total": len(cases),
        "coverage": f"{sum(case['caught'] for case in cases) / len(cases) * 100:.0f}%",
        "cases": cases,
    }
    root = Path("analysis/_runs")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "mutation_results.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["n_pass"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

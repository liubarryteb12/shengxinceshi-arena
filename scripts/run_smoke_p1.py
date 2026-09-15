#!/usr/bin/env python3
"""Execute the lightweight GSE77459 raw-CEL smoke path."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Shanghai")
MODULE_ID = "affymetrix_expression_gse77459_smoke"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_samples(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def extract_cels(raw_tar: Path, samples: list[dict[str, str]], destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with tarfile.open(raw_tar, "r") as archive:
        names = set(archive.getnames())
        for row in samples:
            member = row["raw_cel_member"]
            if member not in names:
                raise RuntimeError(f"Missing archive member: {member}")
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"Cannot read archive member: {member}")
            target = destination / f"{row['sample_id']}.CEL"
            with gzip.GzipFile(fileobj=source, mode="rb") as compressed, target.open("wb") as out:
                shutil.copyfileobj(compressed, out, length=1024 * 1024)
            paths.append(target)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.workspace.resolve()
    raw_tar = root / "inputs/raw/GSE77459/GSE77459_RAW.tar"
    sample_sheet = root / "inputs/metadata/GSE77459/GSE77459_samples.csv"
    matrix = root / "inputs/raw/GSE77459/metadata/GSE77459_series_matrix.txt.gz"
    for path in (raw_tar, sample_sheet, matrix):
        if not path.exists():
            raise SystemExit(f"Required input missing: {path}")
    samples = read_samples(sample_sheet)
    groups = {group: sum(row["group"] == group for row in samples) for group in ("control", "case")}
    if len(samples) != 12 or groups != {"control": 6, "case": 6}:
        raise SystemExit(f"Unexpected GSE77459 design: n={len(samples)}, groups={groups}")

    run_id = "smoke_" + dt.datetime.now(LOCAL_TZ).strftime("%Y%m%d_%H%M%S")
    output = root / "analysis/outputs/gse77459_smoke"
    result_dir = output / "results"
    table_dir = output / "tables"
    figure_dir = output / "figures"
    record_dir = output / "records"
    run_dir = output / "run"
    log_dir = output / "logs"
    for directory in (result_dir, table_dir, figure_dir, record_dir, run_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)
    run_record = root / "analysis/_runs" / run_id
    run_record.mkdir(parents=True, exist_ok=True)
    run_yaml = run_record / "run.yaml"
    write(run_yaml, f'''schema_version: "1.0"\nrun_id: {run_id}\ndataset_id: GSE77459\nmodule_id: {MODULE_ID}\nstatus: running\nexecution_backend: github_actions\ninput_mode: full_raw\n''')

    with tempfile.TemporaryDirectory(prefix="gse77459_cel_") as tmp:
        cel_files = extract_cels(raw_tar, samples, Path(tmp))
        config = {
            "schema_version": "1.0",
            "meta": {"run_id": run_id, "dataset_id": "GSE77459", "module_id": MODULE_ID, "random_seed": 42},
            "input_paths": {"sample_sheet": str(sample_sheet), "raw_archive": str(raw_tar), "series_matrix": str(matrix)},
            "outputs": {"output_dir": str(output), "summary_json": str(run_dir / "summary.json")},
            "parameters": {"random_seed": 42, "absent_probe_threshold": 0.75, "multiple_testing": "BH", "cel_files": [str(p) for p in cel_files]},
        }
        config_path = run_dir / f"input_{run_id}.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        log_path = log_dir / f"{run_id}.log"
        script = root / "analysis/modules/affymetrix_expression_gse7451/scripts/r/run_affy_st_smoke.R"
        completed = subprocess.run(["Rscript", str(script), str(config_path)], cwd=root, text=True, capture_output=True)
        log_path.write_text(completed.stdout + "\n--- STDERR ---\n" + completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            write(run_yaml, f'''schema_version: "1.0"\nrun_id: {run_id}\ndataset_id: GSE77459\nmodule_id: {MODULE_ID}\nstatus: failed\nerror_log: {log_path.relative_to(root)}\n''')
            raise SystemExit(f"Smoke R pipeline failed; see {log_path}")

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    outputs = [result_dir / "normalized_expression_matrix.csv", result_dir / "filtered_expression_matrix.csv", table_dir / "probe_detection_summary.csv", table_dir / "differential_expression.csv", table_dir / "pathway_enrichment.csv"]
    figures = sorted(figure_dir.glob("Figure_1_QC.*"))
    if not all(p.exists() for p in outputs) or {p.suffix.lower().lstrip('.') for p in figures} != {"pdf", "svg", "png", "tiff", "jpg"}:
        raise SystemExit("Smoke output completeness check failed")
    manifest_items = "\n".join(f"    - {p.relative_to(root)} (sha256:{sha256(p)})" for p in outputs + figures)
    write(output / "manifest.yaml", f'''schema_version: "1.0"\nmodule_id: {MODULE_ID}\ndataset_id: GSE77459\nrun_id: {run_id}\nstatus: success\ninput_mode: full_raw\nplatform: GPL17692\ninputs:\n  - path: {sample_sheet.relative_to(root)}\n    sha256: sha256:{sha256(sample_sheet)}\n  - path: {raw_tar.relative_to(root)}\n    sha256: sha256:{sha256(raw_tar)}\n  - path: {matrix.relative_to(root)}\n    sha256: sha256:{sha256(matrix)}\noutputs:\n{manifest_items}\nmethod_boundary:\n  rma: oligo::rma\n  absent_filter: {summary.get('absent_filter_method')}\n  requested_absent_filter: MAS5-style present/absent threshold\n  note: GSE77459 GPL17692 is an Affymetrix Gene ST platform; the compatible detection method is explicitly labelled and must not be called MAS5.\n  differential_expression: limma with BH\n  pathway_requested: MAPPFinder\n  pathway_executed: {summary.get('pathway_method_executed')}\n''')
    (record_dir / "handoff.md").write_text(f'''# GSE77459 smoke handoff\n\n- Run: `{run_id}`\n- Design: 12 human samples, control=6, case=6.\n- Platform: GPL17692 Affymetrix Human Gene 2.1 ST.\n- RMA: `oligo::rma`; limma/BH: executed.\n- Absent filtering: `{summary.get('absent_filter_status')}` using `{summary.get('absent_filter_method')}`; this is not MAS5.\n- Evidence boundary: technical smoke test, not pSS/GSE7451 evidence.\n''', encoding="utf-8")
    write(record_dir / "checkpoint.yaml", f'''schema_version: "1.0"\nrun_id: {run_id}\nstatus: completed\nnext_step: compare smoke contract with GSE7451 P1 interface\n''')
    write(run_yaml, f'''schema_version: "1.0"\nrun_id: {run_id}\ndataset_id: GSE77459\nmodule_id: {MODULE_ID}\nstatus: completed\ninput_mode: full_raw\nmanifest: {str((output / 'manifest.yaml').relative_to(root))}\n''')
    print(json.dumps({"run_id": run_id, "status": "completed", "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

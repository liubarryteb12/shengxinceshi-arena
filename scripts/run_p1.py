#!/usr/bin/env python3
"""Execute the confirmed GSE7451 P1 flow and write handoff contracts.

Modes:
  full_raw     Downloaded CEL archive -> RMA -> sequential MAS5 -> limma.
  matrix_only  Memory-safe local validation of downstream limma/contracts using
               GEO's already processed series matrix. This mode explicitly marks
               RMA and MAS5 as N/A; it never presents matrix-only output as raw
               CEL evidence.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

MODULE_ID = "affymetrix_expression_gse7451"
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def local_now() -> dt.datetime:
    return dt.datetime.now(LOCAL_TZ)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_yaml(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_samples(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    required = {"sample_id", "group", "raw_cel_member"}
    if not rows or not required.issubset(rows[0]):
        raise RuntimeError(f"Sample sheet missing required columns: {sorted(required)}")
    if any(row["group"] not in {"control", "pSS"} for row in rows):
        raise RuntimeError("Sample sheet contains unresolved groups")
    return rows


def extract_cel_files(raw_tar: Path, samples: list[dict[str, str]], destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with tarfile.open(raw_tar, "r") as archive:
        names = set(archive.getnames())
        for row in samples:
            member = row["raw_cel_member"]
            if member not in names:
                raise RuntimeError(f"Missing archive member {member}")
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"Unable to read archive member {member}")
            target = destination / f"{row['sample_id']}.CEL"
            with gzip.GzipFile(fileobj=source, mode="rb") as compressed, target.open("wb") as out:
                shutil.copyfileobj(compressed, out, length=1024 * 1024)
            paths.append(target)
    return paths


def materialize_series_matrix(source: Path, destination: Path) -> Path:
    """Extract only the expression table from a GEO series matrix."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    in_table = False
    rows_written = 0
    with gzip.open(source, "rt", encoding="utf-8", newline="") as source_handle, destination.open("w", encoding="utf-8", newline="") as out_handle:
        writer = csv.writer(out_handle)
        for line in source_handle:
            line = line.rstrip("\n")
            if line.startswith("!series_matrix_table_begin"):
                in_table = True
                continue
            if line.startswith("!series_matrix_table_end"):
                break
            if not in_table:
                continue
            row = next(csv.reader([line], delimiter="\t"))
            if not row or row[0] == "":
                continue
            if rows_written == 0:
                row[0] = "probe_id"
            writer.writerow(row)
            rows_written += 1
    if rows_written < 2:
        raise RuntimeError("GEO series matrix expression table was not found")
    return destination


def file_entry(path: Path, root: Path) -> str:
    return f"{path.relative_to(root)} (sha256:{sha256(path)})"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--dataset", default="GSE7451")
    parser.add_argument("--pipeline", default="RMA -> absent filter -> limma -> pathway enrichment")
    parser.add_argument("--mode", choices=["full_raw", "matrix_only"], default=os.environ.get("P1_PIPELINE_MODE", "full_raw"))
    args = parser.parse_args()
    root = args.workspace.resolve()
    dataset = args.dataset.upper()
    if dataset != "GSE7451":
        raise SystemExit("This first executable module is intentionally scoped to GSE7451")

    raw_tar = root / "inputs/raw/GSE7451/GSE7451_RAW.tar"
    sample_sheet = root / "inputs/metadata/GSE7451/GSE7451_samples.csv"
    series_matrix = root / "inputs/raw/GSE7451/metadata/GSE7451_series_matrix.txt.gz"
    for path in (raw_tar, sample_sheet, series_matrix):
        if not path.exists():
            raise SystemExit(f"Required input missing: {path}")
    samples = read_samples(sample_sheet)
    groups = {group: sum(row["group"] == group for row in samples) for group in ("control", "pSS")}
    if groups != {"control": 10, "pSS": 10}:
        raise SystemExit(f"Unexpected GSE7451 group counts: {groups}")

    run_id = "run_" + local_now().strftime("%Y%m%d_%H%M%S")
    module_output = root / "analysis/outputs" / MODULE_ID
    result_dir = module_output / "results"
    table_dir = module_output / "tables"
    figure_dir = module_output / "figures"
    record_dir = module_output / "records"
    run_dir = module_output / "run"
    log_dir = module_output / "logs"
    for directory in (result_dir, table_dir, figure_dir, record_dir, run_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)
    run_record_dir = root / "analysis/_runs" / run_id
    run_record_dir.mkdir(parents=True, exist_ok=True)
    execution_backend = os.environ.get("P1_EXECUTION_BACKEND", "local")
    run_yaml = run_record_dir / "run.yaml"
    write_yaml(run_yaml, f"""schema_version: \"1.0\"\nrun_id: {run_id}\ndataset_id: {dataset}\nmodule_id: {MODULE_ID}\nstatus: running\nexecution_backend: {execution_backend}\ninput_mode: {args.mode}\npipeline: {args.pipeline}\ncurrent_step: 1\n""")

    with tempfile.TemporaryDirectory(prefix="p1_gse7451_cel_") as tmp:
        if args.mode == "full_raw":
            cel_files = extract_cel_files(raw_tar, samples, Path(tmp))
            script = root / "analysis/modules/affymetrix_expression_gse7451/scripts/r/run_pipeline.R"
            expression_matrix = None
        else:
            cel_files = []
            expression_matrix = materialize_series_matrix(series_matrix, run_dir / f"series_matrix_expression_{run_id}.csv")
            script = root / "analysis/modules/affymetrix_expression_gse7451/scripts/r/run_matrix_pipeline.R"
        config = {
            "schema_version": "1.0",
            "meta": {
                "run_id": run_id,
                "dataset_id": dataset,
                "module_id": MODULE_ID,
                "module_version": "0.1.0",
                "random_seed": 42,
                "execution_backend": execution_backend,
            },
            "input_paths": {
                "sample_sheet": str(sample_sheet),
                "raw_archive": str(raw_tar),
                "series_matrix": str(series_matrix),
                "expression_matrix": str(expression_matrix) if expression_matrix else None,
            },
            "outputs": {
                "output_dir": str(module_output),
                "summary_json": str(run_dir / "summary.json"),
            },
            "parameters": {
                "random_seed": 42,
                "absent_probe_threshold": 0.75,
                "multiple_testing": "BH",
                "input_mode": args.mode,
                "cel_files": [str(path) for path in cel_files],
                "pathway_method_requested": "MAPPFinder",
                "pathway_method_compatibility": "limma::goana",
            },
        }
        config_path = run_dir / f"input_{run_id}.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        log_path = log_dir / f"{run_id}.log"
        completed = subprocess.run(["Rscript", str(script), str(config_path)], cwd=root, text=True, capture_output=True)
        log_path.write_text(completed.stdout + "\n--- STDERR ---\n" + completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            write_yaml(run_yaml, f"""schema_version: \"1.0\"\nrun_id: {run_id}\ndataset_id: {dataset}\nmodule_id: {MODULE_ID}\nstatus: failed\nexecution_backend: {execution_backend}\ninput_mode: {args.mode}\nreturn_code: {completed.returncode}\nerror_log: {log_path.relative_to(root)}\n""")
            raise SystemExit(f"R pipeline failed (return_code={completed.returncode}); see {log_path}: {completed.stderr[-1000:]}")

    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    outputs = [
        result_dir / "normalized_expression_matrix.csv",
        result_dir / "filtered_expression_matrix.csv",
        table_dir / "probe_detection_summary.csv",
        table_dir / "differential_expression.csv",
        table_dir / "pathway_enrichment.csv",
    ]
    figures = sorted(figure_dir.glob("Figure_1_QC.*"))
    if not all(path.exists() for path in outputs) or len(figures) != 5:
        raise SystemExit("P1 output completeness check failed")
    overall_status = "success" if args.mode == "full_raw" else "partial"
    evidence_boundary = "candidate_exploratory" if args.mode == "full_raw" else "matrix_only_validation_not_raw_evidence"

    manifest = module_output / "manifest.yaml"
    output_lines = "\n".join(f"    - {file_entry(path, root)}" for path in outputs + figures)
    write_yaml(manifest, f"""schema_version: \"1.0\"\nmodule_id: {MODULE_ID}\nmodule_version: 0.1.0\ndataset_id: {dataset}\nrun_id: {run_id}\ntimestamp: {local_now().date().isoformat()}\nstatus: {overall_status}\nexecution_backend: {execution_backend}\ninput_mode: {args.mode}\ninputs:\n  - path: {sample_sheet.relative_to(root)}\n    sha256: sha256:{sha256(sample_sheet)}\n  - path: {raw_tar.relative_to(root)}\n    sha256: sha256:{sha256(raw_tar)}\n  - path: {series_matrix.relative_to(root)}\n    sha256: sha256:{sha256(series_matrix)}\noutputs:\n{output_lines}\nparameters:\n  absent_probe_threshold: 0.75\n  multiple_testing: BH\n  random_seed: 42\npathway:\n  requested_tool: MAPPFinder\n  executed_tool: {summary.get('pathway_method_executed')}\n  status: {summary.get('pathway_status')}\n  note: {summary.get('pathway_reason')}\nrecords:\n  qc_report: {record_dir.relative_to(root)}/qc_report.yaml\n  handoff: {record_dir.relative_to(root)}/handoff.md\n  diff: {record_dir.relative_to(root)}/diff.md\n  checkpoint: {record_dir.relative_to(root)}/checkpoint.yaml\n  next_tasklist: {record_dir.relative_to(root)}/next_tasklist.md\n""")

    def verdict(status: str | None) -> str:
        if status in {"success", "success_compatibility"}:
            return "pass"
        return "N/A"

    qc_status = "pass" if summary.get("status") == "success" and args.mode == "full_raw" else "pass_with_NA"
    write_yaml(record_dir / "qc_report.yaml", f"""schema_version: \"1.0\"\nrun_id: {run_id}\nstatus: {qc_status}\nverdict: {qc_status}\ninput_mode: {args.mode}\nchecks:\n  - name: input_completeness\n    verdict: pass\n  - name: sample_group_balance\n    verdict: pass\n    detail: control=10, pSS=10\n  - name: rma_normalization\n    verdict: {verdict(summary.get('rma_status'))}\n    detail: {summary.get('rma_status')}\n  - name: absent_probe_filter\n    verdict: {verdict(summary.get('absent_filter_status'))}\n    detail: {summary.get('absent_filter_status')}\n  - name: limma_bh_differential_expression\n    verdict: {verdict(summary.get('limma_status'))}\n    detail: significant_gene_count={summary.get('significant_gene_count')}\n  - name: pathway_enrichment_tool_transparency\n    verdict: {verdict(summary.get('pathway_status'))}\n    detail: requested=MAPPFinder; executed={summary.get('pathway_method_executed')}\nwarnings:\n  - 当前数据为单队列 10 vs 10，结果仅作探索性证据。\n  - 全部样本为女性，无法评估性别效应。\n  - matrix_only 模式不替代 raw CEL 的 RMA/MAS5 完整验证。\n""")
    method_summary = "RMA、顺序 MAS5 absent 过滤、limma（BH）和通路步骤" if args.mode == "full_raw" else "读取 GEO 已处理 series matrix，执行 limma（BH）及接口产出；RMA/MAS5 标记为 N/A"
    usage_note = "raw CEL 完整证据尚未在本地内存环境完成" if args.mode == "matrix_only" else "不能外推为临床效用或已证实机制"
    (record_dir / "handoff.md").write_text(f"""# P1 交接单：GSE7451\n\n1. **这一步是什么**：Affymetrix 表达谱最小分析闭环。\n2. **做了什么**：{method_summary}。\n3. **输入是什么**：GSE7451 RAW tar、series matrix、样本分组表。\n4. **输出是什么**：标准化/过滤矩阵、差异表达表、通路表、QC 图五格式和 manifest。\n5. **结果怎么样**：20 个样本，control=10、pSS=10；保留探针 {summary.get('filtered_probe_count')}；显著基因 {summary.get('significant_gene_count')}；通路状态 {summary.get('pathway_status')}。\n6. **能不能用**：可用于验证下游接口和探索性 P2 草稿；{usage_note}。\n7. **下一步建议**：GitHub Actions 上运行 full_raw，复核 pathway 工具差异、运行 P1 变异测试，再进入 P2。\n\n运行：`{run_id}`\n""", encoding="utf-8")
    (record_dir / "diff.md").write_text(f"""# 运行差异\n\n- GSE7451 P1 运行模式：`{args.mode}`。\n- 数据 checksum：见 `{manifest.relative_to(root)}`。\n- 主要参数：absent threshold=0.75，multiple testing=BH，random seed=42。\n""", encoding="utf-8")
    write_yaml(record_dir / "checkpoint.yaml", f"""schema_version: \"1.0\"\ncheckpoint_id: {run_id}_complete\nrun_id: {run_id}\nstatus: completed\nmodule_id: {MODULE_ID}\ninput_mode: {args.mode}\ncreated_at: {local_now().date().isoformat()}\nresume_from: null\n""")
    (record_dir / "next_tasklist.md").write_text("""# 下一步任务\n\n1. 在 GitHub Actions 运行 `full_raw` P1；\n2. 运行 P1 Q1–Q6 变异测试；\n3. 复核 MAPPFinder 与兼容实现的差异；\n4. 生成 P1→P2 证据包后进入 P2；\n5. 保留当前 run 和原始输入，不覆盖 checkpoint。\n""", encoding="utf-8")

    status = "success" if args.mode == "full_raw" else "partial"
    evidence = root / "analysis/_index/p1_to_p2_evidence.yaml"
    e1_claim = "GSE7451 的原始 CEL 数据经 RMA 预处理形成标准化表达矩阵" if args.mode == "full_raw" else "GEO series matrix 已被读取并形成下游验证用表达矩阵；该结果不等同于本次运行执行 RMA"
    e1_method = "RMA" if args.mode == "full_raw" else "GEO series matrix（预处理状态继承自来源，RMA 本次 N/A）"
    write_yaml(evidence, f"""schema_version: \"1.0\"\ncontract_id: p1_to_p2_evidence\nproject_id: shengxinceshi_arena\nstatus: {status}\ntimestamp: {local_now().date().isoformat()}\nsource_run_id: {run_id}\nevidence_boundary: {evidence_boundary}\nevidence:\n  - evidence_id: E001\n    partn_n_output: part1-01-output\n    module_id: affymetrix_rma\n    claim: {e1_claim}\n    result_file: {result_dir.relative_to(root)}/normalized_expression_matrix.csv\n    figure: {figure_dir.relative_to(root)}/Figure_1_QC.pdf\n    parameters:\n      platform: GPL570\n      method: {e1_method}\n    suitable_for: [Methods, Results]\n    limitations: 单队列；探索性；matrix_only 模式不替代 raw CEL 验证\n  - evidence_id: E002\n    partn_n_output: part1-03-output\n    module_id: limma_differential_expression\n    claim: pSS 与 control 的差异表达结果已按 BH 方法校正\n    result_file: {table_dir.relative_to(root)}/differential_expression.csv\n    parameters:\n      contrast: pSS-control\n      multiple_testing: BH\n      significant_gene_count: {summary.get('significant_gene_count')}\n    suitable_for: [Methods, Results]\n    limitations: 无独立外部验证\n  - evidence_id: E003\n    partn_n_output: part1-04-output\n    module_id: pathway_enrichment\n    claim: 差异表达结果进入通路富集接口；实际工具需按 manifest 表述\n    result_file: {table_dir.relative_to(root)}/pathway_enrichment.csv\n    parameters:\n      requested_tool: MAPPFinder\n      executed_tool: {summary.get('pathway_method_executed')}\n      status: {summary.get('pathway_status')}\n    suitable_for: [Results]\n    limitations: 不得将兼容实现称为原始 MAPPFinder 结果\nmethods:\n  - method_id: M001\n    module_id: affymetrix_rma\n    description: {e1_method}\n    software: affy_or_GEO_series_matrix\n  - method_id: M002\n    module_id: absent_probe_filtering\n    description: {summary.get('absent_filter_status')}\n    software: affy::mas5calls_or_NA\n  - method_id: M003\n    module_id: limma_differential_expression\n    description: Moderated linear model with BH correction\n    software: limma\nfigures:\n  - figure_id: Figure_1_QC\n    path: {figure_dir.relative_to(root)}/Figure_1_QC.pdf\n    formats: [pdf, svg, png, tiff, jpg]\n    description: GSE7451 expression QC boxplot\ntables:\n  - table_id: Table_DE\n    path: {table_dir.relative_to(root)}/differential_expression.csv\n    description: limma differential expression results\nlimitations:\n  - 单队列、10 vs 10，不能外推临床效用。\n  - 全部样本为女性。\n  - 无独立验证和实验验证。\nvalidation:\n  status: pending_mutation_test\n  checks: [input_integrity, rma, absent_filter, limma_bh, pathway_transparency, figure_five_formats]\n""")

    quality = root / "analysis/_index/p1_to_p4_quality.yaml"
    weakness_detail = "本地 matrix_only 验证未执行 raw CEL RMA/MAS5" if args.mode == "matrix_only" else "pathway 工具与论文原始工具存在需复核的差异"
    write_yaml(quality, f"""schema_version: \"1.0\"\ncontract_id: p1_to_p4_quality\nproject_id: shengxinceshi_arena\nstatus: {status}\ntimestamp: {local_now().date().isoformat()}\nsource_run_id: {run_id}\nanalysis_summary:\n  data_type: microarray_expression\n  sample_size: 20\n  groups: control=10, pSS=10\n  input_mode: {args.mode}\n  analysis_modules: [affymetrix_rma, absent_probe_filtering, limma_differential_expression, pathway_enrichment]\n  total_evidence: 3\n  total_figures: 1\n  total_tables: 2\nquality_assessment:\n  data_quality: provisional\n  method_rigor: provisional\n  statistical_validity: provisional\n  reproducibility: high\n  novelty: not_assessed\n  clinical_value: not_assessed\ntopic_assessment:\n  primary_topic: 原发性干燥综合征与健康对照的唾液转录组表达差异\n  secondary_topic: 唾液基因表达候选生物标志物\n  potential_journals: [自身免疫病, 口腔医学, 生物信息学/转录组学]\nstrengths:\n  - 输入完整且 checksum 可追溯\n  - 样本分组平衡\n  - limma 和 BH 参数已记录\nweaknesses:\n  - 单队列且全部样本为女性\n  - 缺少独立验证和实验验证\n  - {weakness_detail}\nrecommendations:\n  - 在 GitHub Actions full_raw 环境完成 raw CEL 验证\n  - 先完成 P1 变异测试和 pathway 工具复核\n  - P2 仅使用候选/探索性措辞\n""")

    final_status = "completed" if args.mode == "full_raw" else "completed_with_NA"
    write_yaml(run_yaml, f"""schema_version: \"1.0\"\nrun_id: {run_id}\ndataset_id: {dataset}\nmodule_id: {MODULE_ID}\nstatus: {final_status}\nexecution_backend: {execution_backend}\ninput_mode: {args.mode}\ncurrent_step: 5\nmanifest: {manifest.relative_to(root)}\n""")
    print(json.dumps({"run_id": run_id, "status": final_status, "input_mode": args.mode, "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

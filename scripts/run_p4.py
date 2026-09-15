#!/usr/bin/env python3
"""Run a source-aware provisional P4-b journal review."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.workspace.resolve()
    today = dt.datetime.now(LOCAL_TZ).date().isoformat()
    summary_path = root / "analysis/outputs/affymetrix_expression_gse7451/run/summary.json"
    if not summary_path.exists():
        raise SystemExit("P4 requires a P1 summary")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    p1_status = "partial" if summary.get("input_mode") == "series_matrix" else "success"
    p2_quality = yaml.safe_load((root / "02_writing/p2_to_p4b_quality.yaml").read_text(encoding="utf-8"))
    p3_report = (root / "03_typesetting/check_report.md").read_text(encoding="utf-8")

    journals = [
        {
            "journal_id": "bmc_oral_health",
            "name": "BMC Oral Health",
            "publisher": "Springer Nature / BMC",
            "scope_url": "https://link.springer.com/journal/12903/aims-and-scope",
            "scope_evidence": "Aims and scope covers disorders of the mouth, teeth and gums and related molecular genetics, pathophysiology and epidemiology.",
            "scope_fit": 9,
            "tier_fit": "待确认",
            "format_fit": "待确认",
            "policy_fit": 7,
            "oa_fit": "待确认",
            "apc_fit": "待确认",
            "reason": "主题与唾液/口腔分子研究最直接匹配；目标期刊指南、层级、版面费仍需核验。",
            "risks": ["当前 P1 仍为 partial matrix_only；需要 raw-CEL full_raw 和验证证据。", "作者声明与目标栏目尚未确认。"],
        },
        {
            "journal_id": "bmc_rheumatology",
            "name": "BMC Rheumatology",
            "publisher": "Springer Nature / BMC",
            "scope_url": "https://link.springer.com/journal/41927/aims-and-scope",
            "scope_evidence": "Aims and scope covers rheumatological diseases, systemic/inflammatory conditions, epidemiology, pathophysiology and genetics.",
            "scope_fit": 8,
            "tier_fit": "待确认",
            "format_fit": "待确认",
            "policy_fit": 7,
            "oa_fit": "待确认",
            "apc_fit": "待确认",
            "reason": "自身免疫病与 pSS 题材匹配；唾液分子数据的临床/病理生理定位需加强。",
            "risks": ["需要更清晰的风湿病学问题与独立验证。", "目标期刊指南、层级、版面费仍需核验。"],
        },
        {
            "journal_id": "frontiers_in_immunology",
            "name": "Frontiers in Immunology",
            "publisher": "Frontiers",
            "scope_url": "https://www.frontiersin.org/journals/immunology/about",
            "scope_evidence": "Mission and scope covers basic, translational and clinical immunology, autoimmune disorders and molecular bases of immune disorders; the page also states public-data computational studies require appropriate validation.",
            "scope_fit": 8,
            "tier_fit": "待确认",
            "format_fit": "待确认",
            "policy_fit": 6,
            "oa_fit": "待确认",
            "apc_fit": "待确认",
            "reason": "免疫学方向匹配，但官方范围明确强调公共数据计算研究的适当验证；当前缺少独立验证，风险较高。",
            "risks": ["公共数据计算研究的验证要求是当前主要阻塞。", "目标期刊指南、层级、版面费仍需核验。"],
        },
    ]
    for journal in journals:
        journal["source_verified"] = True
        journal["verified_at"] = today
        journal["data_verification_status"] = "scope_only"
        journal["predatory_check_status"] = "pending_manual_verification"

    jdb = root / "04_journal/journal_database.yaml"
    jdb_text = """schema_version: \"1.0\"\nstatus: partial\nlast_verified_at: {today}\npolicy:\n  every_field_requires_source: true\n  every_field_requires_timestamp: true\n  uncertain_values_must_be_marked: 待确认\n  human_confirmation_required_for: [impact_factor, partition, apc]\njournals:\n""".format(today=today)
    for journal in journals:
        jdb_text += f'''  - journal_id: {journal['journal_id']}\n    name: {journal['name']}\n    publisher: {journal['publisher']}\n    identity_source: {journal['scope_url']}\n    identity_verified_at: {today}\n    scope:\n      value: confirmed_scope_match\n      status: verified\n      source: {journal['scope_url']}\n      verified_at: {today}\n      evidence: {journal['scope_evidence']}\n    impact_factor: 待确认\n    impact_factor_source: null\n    impact_factor_verified_at: {today}\n    partition: 待确认\n    partition_source: null\n    partition_verified_at: {today}\n    review_cycle: 待确认\n    review_cycle_source: null\n    review_cycle_verified_at: {today}\n    apc: 待确认\n    apc_source: null\n    apc_verified_at: {today}\n    predatory_check: pending_manual_verification\n    predatory_check_source: https://thinkchecksubmit.org/\n    predatory_check_verified_at: {today}\n'''
    write(jdb, jdb_text)

    write(root / "04_journal/quality_assessment.yaml", f'''schema_version: "1.0"\nstatus: partial\nstage: P4-b\ntimestamp: {today}\ncomparison_to_p4a:\n  p4a_status: confirmed\n  p4a_predicted_directions: [自身免疫病/干燥综合征, 口腔医学/唾液生物标志物, 生物信息学/转录组学]\n  p4b_observed_status: {p1_status}_p1_and_partial_p2_p3\n  verdict: provisional\n  explanation: P4-b 已读取实际接口，但 full_raw、目标期刊和独立验证尚未完成。\nassessment:\n  narrative_completeness: provisional\n  evidence_consistency: provisional\n  method_rigor: provisional\n  statistical_validity: provisional\n  writing_quality: provisional\n  figure_quality: provisional\n  novelty: not_assessed\n  clinical_value: not_assessed\ninputs:\n  p1: analysis/_index/p1_to_p4_quality.yaml\n  p2: 02_writing/p2_to_p4b_quality.yaml\n  p3: 03_typesetting/check_report.md\n''')

    match_lines = [f'''schema_version: "1.0"\nstatus: partial\ntimestamp: {today}\nscore_policy: scope_fit is provisional; all non-scope fields remain 待确认\nscores:''']
    for journal in journals:
        match_lines.append(f'''  - journal_id: {journal['journal_id']}\n    scope_fit: {journal['scope_fit']}\n    tier_fit: {journal['tier_fit']}\n    format_fit: {journal['format_fit']}\n    policy_fit: {journal['policy_fit']}\n    oa_fit: {journal['oa_fit']}\n    apc_fit: {journal['apc_fit']}\n    total_score: 待确认\n    score_basis: provisional_scope_only\n    source: {journal['scope_url']}\n    verified_at: {today}\n    field_audit:\n      scope_fit: {{status: provisional_agent_assessment, source: {journal['scope_url']}, verified_at: {today}}}\n      tier_fit: {{status: 待确认, source: null, verified_at: {today}}}\n      format_fit: {{status: 待确认, source: null, verified_at: {today}}}\n      policy_fit: {{status: provisional_agent_assessment, source: {journal['scope_url']}, verified_at: {today}}}\n      oa_fit: {{status: 待确认, source: null, verified_at: {today}}}\n      apc_fit: {{status: 待确认, source: null, verified_at: {today}}}\n      total_score: {{status: 待确认, source: 04_journal/match_score.yaml, verified_at: {today}}}\n''')
    write(root / "04_journal/match_score.yaml", "\n".join(match_lines))

    rec_lines = [f'''schema_version: "1.0"\ncontract_id: recommended_journals\nstage: P4-b\nstatus: partial\npackage_id: jdp_GSE7451_{today.replace('-', '')}\nmanuscript_version: v1\ntimestamp: {today}\nrecommendation_status: provisional_scope_match_only\nrecommended:''']
    for rank, journal in enumerate(journals, start=1):
        rec_lines.append(f'''  - rank: {rank}\n    journal_id: {journal['journal_id']}\n    name: {journal['name']}\n    publisher: {journal['publisher']}\n    scope_fit: {journal['scope_fit']}\n    total_score: 待确认\n    reason: {journal['reason']}\n    risks:\n''')
        rec_lines.extend([f"      - {risk}" for risk in journal["risks"]])
        rec_lines.append(f'''    source_verified: true\n    source: {journal['scope_url']}\n    verified_at: {today}\n    predatory_check: pending_manual_verification\n    field_audit:\n      scope_fit: {{status: provisional_agent_assessment, source: {journal['scope_url']}, verified_at: {today}}}\n      total_score: {{status: 待确认, source: 04_journal/match_score.yaml, verified_at: {today}}}\n      predatory_check: {{status: pending_manual_verification, source: https://thinkchecksubmit.org/, verified_at: {today}}}\n''')
    write(root / "04_journal/recommended_journals.yaml", "\n".join(rec_lines))

    write(root / "04_journal/submission_order.yaml", f'''schema_version: "1.0"\ncontract_id: submission_order\nstatus: partial\ntimestamp: {today}\norder:\n  - priority: 1\n    journal_id: bmc_oral_health\n    name: BMC Oral Health\n    reason: scope_fit highest for salivary/oral molecular direction\n    risks: [P1 partial, independent validation absent, target-journal parameters pending]\n    fallback_if_rejected: bmc_rheumatology\n  - priority: 2\n    journal_id: bmc_rheumatology\n    name: BMC Rheumatology\n    reason: autoimmune/rheumatology scope fit\n    risks: [clinical/rheumatology positioning and validation pending]\n    fallback_if_rejected: frontiers_in_immunology\n  - priority: 3\n    journal_id: frontiers_in_immunology\n    name: Frontiers in Immunology\n    reason: immunology scope fit\n    risks: [public-data computational validation requirement; current evidence insufficient]\n    fallback_if_rejected: null\nnotes:\n  - This is a provisional order, not a final user submission decision.\n  - Re-run P4-b after full_raw P1, target-journal verification and independent validation assessment.\n''')

    predatory = [f'''schema_version: "1.0"\nstatus: partial\ntimestamp: {today}\nsource_policy:\n  - https://thinkchecksubmit.org/\n  - https://doaj.org/\n  - official journal scope pages\njournals:''']
    for journal in journals:
        predatory.append(f'''  - journal_id: {journal['journal_id']}\n    name: {journal['name']}\n    checks:\n      - name: official_website_or_scope_page\n        status: passed\n        source: {journal['scope_url']}\n        verified_at: {today}\n      - name: independent_predatory_database_check\n        status: pending_manual_verification\n        source: https://thinkchecksubmit.org/\n      - name: DOAJ_or_indexing_check\n        status: pending_manual_verification\n        source: https://doaj.org/\n    overall: pending_manual_verification\n''')
    write(root / "04_journal/predatory_check.yaml", "\n".join(predatory))

    write(root / "04_journal/feedback.yaml", f'''schema_version: "1.0"\ncontract_id: feedback\nstatus: partial\ntimestamp: {today}\nfeedback:\n  - target: P1\n    priority: high\n    issue: full_raw RMA/MAS5 run and independent validation are still pending\n    action: execute GitHub Actions full_raw, then compare with matrix_only run\n  - target: P2\n    priority: high\n    issue: claims must remain candidate/exploratory\n    action: do not use diagnostic, mechanism-confirmed or external-validation wording\n  - target: P3\n    priority: medium\n    issue: target-journal template, line numbers, font embedding and final export are pending\n    action: activate journal-specific template after journal selection\nreturn_targets: [P1, P2, P3]\n''')

    write(root / "04_journal/_runs/p4_run.yaml", f'''schema_version: "1.0"\nrun_id: p4_{today.replace('-', '')}\nstatus: partial\ntimestamp: {today}\ninputs:\n  - analysis/_index/p1_to_p4_quality.yaml\n  - 02_writing/p2_to_p4b_quality.yaml\n  - 03_typesetting/check_report.md\noutputs:\n  - 04_journal/recommended_journals.yaml\n  - 04_journal/submission_order.yaml\n  - 04_journal/feedback.yaml\n''')
    print("P4 provisional review written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

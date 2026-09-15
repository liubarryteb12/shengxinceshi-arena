# 跨阶段接口字段清单

| 接口 | 生产方 | 消费方 | 当前状态 |
|---|---|---|---|
| `journal_direction_package.yaml` | P4-a | P1/P2/P3/P4-b | draft |
| `p1_to_p2_evidence.yaml` | P1 | P2 | pending |
| `p1_to_p4_quality.yaml` | P1 | P4-b | pending |
| `p2_to_p3_manuscript.yaml` | P2 | P3 | pending |
| `p2_to_p4b_quality.yaml` | P2 | P4-b | pending |
| `check_report.md` | P3 | P4-b | pending |
| `recommended_journals.yaml` | P4-b | 用户 | pending |
| `submission_order.yaml` | P4-b | 用户 | pending |
| `feedback.yaml` | P4-b | P1/P2/P3 | pending |

## 字段完整性要求

- P4-a 方向包：题材判断、期刊方向、分析要求、写作约束、排版约束、风险、不确定性、待定制项。
- P1→P2：evidence、methods、figures、tables、limitations，以及每条证据的来源、参数和适用范围。
- P1→P4-b：数据概况、模块清单、证据/图表数量、质量评估、优缺点和建议。
- P2→P3：结构序、稿件文件、图表位置、参考文献、声明块和检查状态。
- P2→P4-b：八维稿件质量、题材评估、优缺点和建议。
- P3→P4-b：检查报告、投稿包、失败项和修复建议。
- P4-b→用户：推荐期刊 1–3 个、逐项评分、理由、风险、来源、投稿顺序和反馈路径。

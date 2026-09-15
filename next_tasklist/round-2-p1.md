# 第 2 轮任务：P1 最小闭环

状态：`pending`

## 启动前必须确认

- [ ] 首个数据集 ID 或本地数据路径
- [ ] 数据类型与样本/分组信息
- [ ] 是否允许下载/联网
- [ ] P4-a 方向包中的分析要求
- [ ] 执行后端：local 或 GitHub Actions

## 计划交付

1. 数据迁移与 checksum 记录；
2. 数据可用性分析；
3. 至少一个模块的 `module.yaml`、脚本草案和复审记录；
4. `flow_draft.yaml` 与用户确认后的 `flow_confirmed.yaml`；
5. 一个分析步骤的 manifest、QC、handoff、diff、checkpoint、next_tasklist；
6. `p1_to_p2_evidence.yaml` 与 `p1_to_p4_quality.yaml` 的真实内容；
7. P1 变异测试：先 FAIL 后 PASS。

## 不做

- 不在数据和方向未确认前擅自分析；
- 不编造结果、样本量、P 值或期刊事实；
- 不把骨架 `pending` 当作 `pass`。

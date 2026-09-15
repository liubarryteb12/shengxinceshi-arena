# shengxinceshi-arena

> P1–P4 SCI 论文生产系统：证据生产 → 稿件生产 → 投稿包生产 → 投稿策略。

## 当前状态

- **Repository**：`shengxinceshi-arena`
- **形态**：本地 Git repository（已初始化；当前分支 `main`）
- **当前里程碑**：M3 · P1→P4 接口闭环已验证
- **P1 本地验证**：`matrix_only` 已完成，状态 `completed_with_NA`；仅用于下游接口验证，不替代 raw-CEL 证据
- **P2/P3/P4**：P2 已生成 L1 探索性稿件；P3 已生成通用安全投稿包；P4-b 已生成带来源/时间/未确认项的候选期刊评估，均保留 `partial`
- **长任务后端**：GitHub Actions；真实 `full_raw` workflow 已写入 `.github/workflows/end_to_end_validation.yml`，尚待远程触发
- **规范源**：`docs/source/`，保存用户提供的 6 个原始文本文件，原样保留

## 系统分层

| 部分 | 职责 | 主要接口 |
|---|---|---|
| P1 | 生信分析，生产结构化证据 | `analysis/_index/p1_to_p2_evidence.yaml`、`p1_to_p4_quality.yaml` |
| P2 | SCI 写作，生产稿件包 | `02_writing/p2_to_p3_manuscript.yaml`、`p2_to_p4b_quality.yaml` |
| P3 | 自动排版，生产投稿包 | `03_typesetting/check_report.md` |
| P4 | 期刊策略，前端约束与后端复审 | `04_journal/` |

## 重要纪律

1. 用户管方向与取舍，agent 管执行与记录。
2. 所有数字、结论和期刊数据必须有来源或明确标记为待确认。
3. 证据强度不得被写作或排版升级。
4. 判定统一采用 `pass / fail / N/A` 三态；未运行不得伪装为通过。
5. 每条 A 档规则必须有变异用例；抓不到就是空规。
6. 原始输入只读；缓存可重建；结果和记录保留。

## 目录入口

```text
workspace.yaml                 工作空间元信息
README.md                      当前工作说明
docs/source/                   用户提供的规范原文
governance/                    元原则、状态和接口矩阵
schemas/                       接口契约（机器可读）
quality/                       判据登记与验收记录
analysis/                      P1
02_writing/                    P2
03_typesetting/                P3
04_journal/                    P4
handoff/                       跨阶段交接
checkpoints/                   恢复锚点
next_tasklist/                 下一步任务
scripts/                       仓库检查脚本
.github/workflows/             云端执行入口
```

## 本地检查

在仓库根目录执行：

```bash
python scripts/validate_workspace.py
```

本检查验证目录/接口契约；不会自动下载数据或执行生信分析。已完成的 P1 运行需使用 `scripts/validate_p1_outputs.py`，P1 变异护栏需使用 `scripts/guard_selftest.py`。

## 执行策略

在用户已确认目标、数据来源和后端后，agent 默认自主推进：自动下载、实现、运行、复审、修复和迭代，不再逐步询问“是否继续”。只有以下情况会暂停并报告：缺少不可推断的关键事实、需要用户承担不可逆/高风险操作，或远程凭据/权限阻塞。

本项目已配置 GitHub Actions 作为 P1 长任务后端，远程地址为 `https://github.com/liubarryteb12/shengxinceshi-arena.git`。

## 下一步

agent 将在不重复询问“是否继续”的前提下自主推进：

1. 触发 GitHub Actions 的 `P1 full_raw` job，执行真实 raw-CEL RMA → 超过 75% 样本 absent 探针过滤 → limma（BH）→ 明确标注的通路兼容实现；
2. 保存 Actions 日志、下载 manifest、checksum、QC、handoff、diff、checkpoint 和接口 artifact；
3. 对 full_raw 与当前 matrix_only 结果做差异复核；
4. 在目标期刊仍未确认时维持 P4-b `partial`，不填写未经核验的影响因子、分区、审稿周期或 APC；
5. 远程 GitHub push 仍需可用的 HTTPS/SSH 凭据，凭据恢复前不擅自替用户执行不可逆远程操作。

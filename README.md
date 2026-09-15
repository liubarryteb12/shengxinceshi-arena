# shengxinceshi-arena

> P1–P4 SCI 论文生产系统：证据生产 → 稿件生产 → 投稿包生产 → 投稿策略。

## 当前状态

- **Repository**：`shengxinceshi-arena`
- **形态**：本地 Git repository（已初始化；当前分支 `main`）
- **当前里程碑**：M1 · 骨架立起
- **当前轮次**：第 1 轮 · 目录树、接口定义、空规则登记
- **执行后端**：local（GitHub Actions 作为可选后端，尚未启用）
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

本检查只验证第 1 轮骨架和接口契约，不会下载数据、不执行生信分析，也不会虚构任何结果。

## 下一步

进入第 2 轮前需要用户确认：

1. 首个验证数据集（建议先使用基础集中的一个小数据集）；
2. 工作空间/数据来源与是否允许下载；
3. P4-a 研究方向包中的目标方向、证据边界和写作/排版偏好；
4. 是否启用 GitHub Actions 作为 P1 长任务后端。

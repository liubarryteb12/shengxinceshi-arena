# 决策记录

## 2026-09-16 · 建立本地 repository

- 决策：创建本地 Git repository `shengxinceshi-arena`。
- 原因：当前工具环境可直接操作共享工作区，但没有可用的远程 GitHub 创建接口或远程 URL。
- 结果：仓库位于 `/home/user/shengxinceshi-arena`，分支为 `main`。
- 规范原文：复制到 `docs/source/`，不修改。

## 2026-09-16 · 第 1 轮骨架

- 决策：先实现目录树、元原则、接口契约、休眠登记、空规则登记和骨架校验脚本。
- 原因：符合总纲要的 M1 验收标准，并在开始实际分析前锁定跨阶段接口。
- 未决：首个数据集、P4-a 方向包、目标期刊、是否启用云端执行。

## 2026-09-16 · GSE7451 与分析边界

- 决策：使用 GSE7451；按用户确认的 `RMA → 超过 75% 样本 absent 探针过滤 → limma（BH）→ 通路富集` 执行。
- 决策：本地只把 `matrix_only` 作为内存安全的下游契约验证；raw-CEL `full_raw` 不在本地失败运行的基础上生成科学结果。
- 原因：本地 raw-CEL MAS5/RMA 曾被环境杀死；保守地将长任务转交 GitHub Actions，并保留 `N/A` 边界。
- 结果：本地 run `run_20260916_010330` 完成 `completed_with_NA`；20 个样本，control=10、pSS=10，limma 成功；RMA/MAS5/通路在该模式下为 N/A。

## 2026-09-16 · P2/P3/P4 交接

- 决策：生成 P2 L1 探索性稿件、P3 通用安全投稿包和 P4-b provisional 期刊候选评估。
- 决策：候选期刊只核验官方 scope；影响因子、分区、审稿周期、APC 和独立反掠夺核查均保留 `待确认`/`pending_manual_verification`，不虚构数值。
- 结果：P2→P3→P4 文件接口实际产出；P3 五格式图件已传递并通过 F25，最终目标期刊模板仍未启用。

## 2026-09-16 · GitHub Actions 长任务

- 决策：将真实 `full_raw` 下载、R/Bioconductor 安装、P1、P2、P3、P4 和 artifact 上传写入 `.github/workflows/end_to_end_validation.yml`。
- 约束：workflow 默认固定运行 `full_raw`，不把 `matrix_only` 当作替代路径；远程触发与 push 仍受 HTTPS/SSH 凭据阻塞。
- 记录：2026-09-16 执行 HTTPS `git push origin main`，因环境无法读取 HTTPS Username 失败；已生成本地 ED25519 SSH key，公钥与 fingerprint 记录于 `logs/github_ssh_setup_20260916.md`，等待加入 GitHub 账户后使用 SSH push。详情见 `logs/push_attempt_20260916.md`。

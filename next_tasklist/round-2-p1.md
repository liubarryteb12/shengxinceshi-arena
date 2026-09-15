# 第 2 轮任务：P1 最小闭环

状态：`completed_locally_with_NA`; 真实 `full_raw` 长任务已转入 GitHub Actions workflow，尚待远程触发

## 已完成

- [x] 首个数据集确定为 GSE7451
- [x] NCBI GEO 下载、目标路径、大小与 SHA-256 记录
- [x] 样本元数据解析：20 个样本，control=10、pSS=10
- [x] P1 `matrix_only` 下游验证：limma/BH、QC、manifest、handoff、diff、checkpoint
- [x] P1 输出验证：`P1 OUTPUT VALIDATION: PASS`
- [x] P1-Q1–Q6 变异护栏：6/6，coverage=100%
- [x] P2 L1、P3 通用安全格式和 P4-b provisional 评估已生成

## 未完成/不可替代项

- [ ] GitHub Actions 真实 `full_raw`：RMA → 超过 75% 样本 absent 探针过滤 → limma（BH）→ 通路富集
- [ ] full_raw 的 Affymetrix 注释与 pathway compatibility run 核查
- [ ] full_raw 与 matrix_only 的结果差异复核
- [ ] 独立验证或实验验证（当前输入未提供，不擅自生成）
- [ ] 目标期刊模板、影响因子、分区、审稿周期、APC 和索引核查

## 纪律

- matrix_only 只能作为接口/内存安全验证，不能替代 raw-CEL RMA/MAS5 科学结果；
- MAPPFinder 与 `limma::goana` 兼容实现不得混写；manifest、QC、证据接口必须写清实际执行工具；
- 未运行、未核验和不适用项目分别标记为 `pending`、`待确认` 和 `N/A`；
- 所有 P2 结论保持 candidate/exploratory，不升级为临床效用、因果、机制已证实或外部验证。
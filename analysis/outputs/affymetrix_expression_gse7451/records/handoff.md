# P1 交接单：GSE7451

1. **这一步是什么**：Affymetrix 表达谱最小分析闭环。
2. **做了什么**：读取 GEO 已处理 series matrix，执行 limma（BH）及接口产出；RMA/MAS5 标记为 N/A。
3. **输入是什么**：GSE7451 RAW tar、series matrix、样本分组表。
4. **输出是什么**：标准化/过滤矩阵、差异表达表、通路表、QC 图五格式和 manifest。
5. **结果怎么样**：20 个样本，control=10、pSS=10；保留探针 54675；显著基因 0；通路状态 N/A_no_annotation_in_matrix_validation_mode。
6. **能不能用**：可用于验证下游接口和探索性 P2 草稿；raw CEL 完整证据尚未在本地内存环境完成。
7. **下一步建议**：GitHub Actions 上运行 full_raw，复核 pathway 工具差异、运行 P1 变异测试，再进入 P2。

运行：`run_20260916_010655`

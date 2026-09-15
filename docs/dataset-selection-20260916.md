# 轻量端到端验证数据集选择

日期：2026-09-16（Asia/Shanghai）

## 决定

选择 **GSE77459** 作为新的轻量 raw-CEL smoke test；保留 GSE7451 作为原发性干燥综合征/pSS 科学模块，不用 smoke test 的结果替换 GSE7451 结果。

## 选择理由

- NCBI GEO 记录为 12 个样本，normal pulp=6、inflamed pulp=6；设计平衡，适合检查分组、RMA、差异表达和完整交接。
- raw archive 下载大小为 57,456,640 bytes（约 54.8 MiB），明显小于当前 GSE7451 的 84,531,200 bytes。
- 平台为 GPL17692 / Affymetrix Human Gene 2.1 ST Array，存在 12 个 CEL 文件，可实际测试 raw-CEL 读取和 RMA。
- 主题仍属于口腔/炎症表达研究，与 P4 候选方向的口腔医学方向相容。

## 明确边界

GSE77459 是 Gene ST 平台，不能把 MAS5 present/absent calls 静默套用为原始方法。因此 smoke path 使用 `oligo::rma` 与显式标注的 `oligo::paCalls(DABG)`（必要时 `PSDABG`）兼容检测；DABG p 值先聚合到 RMA core transcript cluster，manifest、summary、handoff 都写明 `not MAS5`。这条路径用于技术可行性验证，不产生 GSE7451/pSS 科学结论，也不改变 GSE7451 的预注册 P1 定义。

## 未选数据集的原因

- GSE5800：6 样本且平台与 RMA/MAS5 兼容，但当前 GEO series 目录只有 matrix/soft/miniml，未发现 series raw CEL archive；只能做 matrix-only，不能验证 raw-CEL 长任务。
- GSE174263：4 个果蝇 RNA-seq 样本，属于另一套 DESeq2/count 生态，不能直接验证当前 Affymetrix RMA/MAS5/limma 接口。
- GSE61444：用户描述为 FPKM，小样本，不能把 FPKM 当作标准 DESeq2 raw-count 输入。
- GSE92681：Agilent 平台，需要另一套读取/预处理路径；文件也大于 GSE77459。

## 已核验来源

- GEO accession：https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE77459
- NCBI GEO filelist：https://ftp.ncbi.nlm.nih.gov/geo/series/GSE77nnn/GSE77459/suppl/filelist.txt
- Series matrix：`inputs/raw/GSE77459/metadata/GSE77459_series_matrix.txt.gz`
- Raw archive：`inputs/raw/GSE77459/GSE77459_RAW.tar`
- Matrix SHA-256：`aa0057c7be57e0b294526ee17f7beaa45623fcc7fa26fba704977387a331e8f4`
- Raw archive SHA-256：`e505d5c7d7616463c0334b050f885f1dd5cdbe54f051a678faad9cc40cb55937`

## 执行入口

- `scripts/prepare_gse77459_metadata.py`
- `scripts/run_smoke_p1.py`
- `scripts/validate_smoke_p1.py`
- `analysis/modules/affymetrix_expression_gse7451/scripts/r/run_affy_st_smoke.R`
- `.github/workflows/smoke_gse77459.yml`

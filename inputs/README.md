# inputs

原始数据、样本元数据和外部参考数据的入口。

- `raw/`：原始数据，只读；默认不纳入 Git。
- `metadata/`：样本表、分组表和补充元数据。
- `external/`：外部验证数据或参考数据。
- `migration_log.yaml`：数据迁移后生成，记录 checksum、文件数和状态。

当前已完成 GSE7451 数据迁移：NCBI GEO RAW tar、series matrix 和 filelist 已下载；下载 URL、目标路径、大小与 SHA-256 记录于 `inputs/migration_log.yaml`，样本表与元数据摘要位于 `inputs/metadata/GSE7451/`。`inputs/raw/` 仍按 `.gitignore` 排除，workflow 会在 Actions 环境重新下载。

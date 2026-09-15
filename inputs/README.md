# inputs

原始数据、样本元数据和外部参考数据的入口。

- `raw/`：原始数据，只读；默认不纳入 Git。
- `metadata/`：样本表、分组表和补充元数据。
- `external/`：外部验证数据或参考数据。
- `migration_log.yaml`：数据迁移后生成，记录 checksum、文件数和状态。

当前尚未收到具体数据，不执行数据迁移。

# P3 排版检查报告

- 项目：`shengxinceshi-arena`
- 时间：2026-09-16
- 状态：`partial`
- 目标期刊：待确认；当前使用通用安全格式
- P2 输入：`02_writing/manuscript/v1/main.docx`

## 检查结果

| 检查 | 状态 | 说明 |
|---|---|---|
| T1 中文/正文左对齐 | pass | 由 DOCX Normal 样式设置；需目标模板复核 |
| T2 中文 wordWrap=CJK | N/A | python-docx 未写入 CJK 特殊属性，目标中文排版前需补齐 |
| T3 图件宽度 ≤160 mm | pass | DOCX 插图按 6 inch 生成，低于 160 mm |
| T5 参考文献一条一段 | partial | P2 当前 refs.bib 已独立维护，最终 Word 域清除待执行 |
| T7 字体全嵌入 | N/A | 当前 PDF 由 matplotlib 生成，投稿版需用模板引擎验证嵌入 |
| T11 结构序 | partial | 使用通用 S1；目标期刊未确认 |
| T43 审稿版双倍行距 | pass | DOCX Normal 样式设置为 2.0 |
| T44 审稿版连续行号 | N/A | 需 Word 模板/OOXML 行号设置 |
| T45 安全版 1.5 倍行距 | pass | DOCX Normal 样式设置为 1.5 |
| T55 图题在图下 | pass | 图注添加在图片之后 |
| F25 五格式齐全 | pass | ['jpg', 'pdf', 'png', 'svg', 'tiff'] |
| F27 光栅图 ≥300 dpi | partial | DPI 元数据：{'png': (299.9994, 299.9994), 'tiff': (300.0, 300.0), 'jpg': (300, 300)} |
| T65 参考文献域代码清除 | N/A | 当前为静态文本草稿；最终模板导出前再检 |

## 输出

- `output/manuscript.pdf`
- `output/manuscript_编辑版.docx`
- `output/manuscript_审稿版.docx`
- `output/manuscript_安全版.docx`
- `figures/Figure_1_QC.*`

本报告的 `partial` 是有意的：没有目标期刊模板和远程 GitHub 推送权限时，不能把通用安全格式写成投稿通过。

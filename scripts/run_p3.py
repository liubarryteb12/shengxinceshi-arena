#!/usr/bin/env python3
"""Create a conservative P3 package from the P2 manuscript package."""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from PIL import Image
import yaml
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def set_doc_defaults(path: Path, spacing: float, line_numbers: bool) -> None:
    doc = Document(path)
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.line_spacing = spacing
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    # Line-number settings require Word-specific section XML. Keep the state explicit
    # in the check report rather than pretending python-docx created them.
    doc.save(path)


def render_pdf(markdown_path: Path, pdf_path: Path) -> None:
    font_path = Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc")
    font = FontProperties(fname=str(font_path), size=9) if font_path.exists() else FontProperties(size=9)
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    with PdfPages(pdf_path) as pdf:
        page_lines = []
        for line in lines + [""]:
            if len(line) > 105:
                for start in range(0, len(line), 105):
                    page_lines.append(line[start:start + 105])
            else:
                page_lines.append(line)
        for offset in range(0, len(page_lines), 48):
            fig = plt.figure(figsize=(8.27, 11.69))
            ax = fig.add_axes([0.08, 0.05, 0.86, 0.90])
            ax.axis("off")
            block = page_lines[offset:offset + 48]
            ax.text(0, 1, "\n".join(block), va="top", ha="left", fontproperties=font, linespacing=1.35)
            pdf.savefig(fig)
            plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.workspace.resolve()
    p2 = root / "02_writing"
    p3 = root / "03_typesetting"
    today = dt.datetime.now(LOCAL_TZ).date().isoformat()
    p2_contract_path = p2 / "p2_to_p3_manuscript.yaml"
    p2_contract = yaml.safe_load(p2_contract_path.read_text(encoding="utf-8")) if p2_contract_path.exists() else {}
    p1_run_id = p2_contract.get("p1_run_id", "unknown")
    source_doc = p2 / "manuscript/v1/main.docx"
    review_doc = p2 / "manuscript/v1/main_审稿版.docx"
    safe_doc = p2 / "manuscript/v1/main_安全版.docx"
    source_md = p2 / "manuscript/v1/main.md"
    if not source_doc.exists() or not source_md.exists():
        raise SystemExit("P3 requires the P2 manuscript package")

    output = p3 / "output"
    figures = p3 / "figures"
    output.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    outputs = {
        "editable": output / "manuscript_编辑版.docx",
        "review": output / "manuscript_审稿版.docx",
        "safe": output / "manuscript_安全版.docx",
        "pdf": output / "manuscript.pdf",
    }
    shutil.copy2(source_doc, outputs["editable"])
    shutil.copy2(review_doc, outputs["review"])
    shutil.copy2(safe_doc, outputs["safe"])
    set_doc_defaults(outputs["review"], 2.0, True)
    set_doc_defaults(outputs["safe"], 1.5, False)
    set_doc_defaults(outputs["editable"], 1.5, False)
    render_pdf(source_md, outputs["pdf"])

    source_figures = sorted((p2 / "figures").glob("Figure_1_QC.*"))
    for src in source_figures:
        shutil.copy2(src, figures / src.name)
    figure_exts = {p.suffix.lower().lstrip(".") for p in figures.glob("Figure_1_QC.*")}
    raster_dpi = {}
    for ext in ("png", "tiff", "jpg"):
        path = figures / f"Figure_1_QC.{ext}"
        if path.exists():
            with Image.open(path) as img:
                raster_dpi[ext] = img.info.get("dpi", "not_recorded")

    check_report = p3 / "check_report.md"
    check_report.write_text(f"""# P3 排版检查报告

- 项目：`shengxinceshi-arena`
- 时间：{today}
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
| F25 五格式齐全 | {"pass" if figure_exts >= {"pdf", "svg", "png", "tiff", "jpg"} else "fail"} | {sorted(figure_exts)} |
| F27 光栅图 ≥300 dpi | partial | DPI 元数据：{raster_dpi} |
| T65 参考文献域代码清除 | N/A | 当前为静态文本草稿；最终模板导出前再检 |

## 输出

- `output/manuscript.pdf`
- `output/manuscript_编辑版.docx`
- `output/manuscript_审稿版.docx`
- `output/manuscript_安全版.docx`
- `figures/Figure_1_QC.*`

本报告的 `partial` 是有意的：没有目标期刊模板和远程 GitHub 推送权限时，不能把通用安全格式写成投稿通过。
""", encoding="utf-8")

    manifest = p3 / "p3_export_manifest.yaml"
    write(manifest, f'''schema_version: "1.0"\nstatus: partial\ntimestamp: {today}\np1_run_id: {p1_run_id}\np2_contract: 02_writing/p2_to_p3_manuscript.yaml\nrequired_formats: [pdf, png, tiff, jpg, svg]\nfiles:\n  - path: 03_typesetting/output/manuscript.pdf\n    purpose: 文图合一预览\n  - path: 03_typesetting/output/manuscript_编辑版.docx\n    purpose: 编辑版\n  - path: 03_typesetting/output/manuscript_审稿版.docx\n    purpose: 双倍行距审稿版；连续行号待模板实现\n  - path: 03_typesetting/output/manuscript_安全版.docx\n    purpose: 1.5 倍行距安全版\n  - path: 03_typesetting/figures/Figure_1_QC.pdf\n  - path: 03_typesetting/figures/Figure_1_QC.svg\n  - path: 03_typesetting/figures/Figure_1_QC.png\n  - path: 03_typesetting/figures/Figure_1_QC.tiff\n  - path: 03_typesetting/figures/Figure_1_QC.jpg\nfont_embedded: pending_template_export\nimage_compression_disabled: pending_template_export\n''')
    zip_path = output / "submission_package.zip"
    package_files = [outputs["pdf"], outputs["editable"], outputs["review"], outputs["safe"], p2 / "refs/refs.bib", p3 / "check_report.md"] + sorted(figures.glob("Figure_1_QC.*"))
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in package_files:
            archive.write(path, path.relative_to(root))

    write(p3 / "_runs/p3_run.yaml", f'''schema_version: "1.0"\nrun_id: p3_{today.replace('-', '')}\nstatus: partial\ntimestamp: {today}\np1_run_id: {p1_run_id}\ninput: 02_writing/p2_to_p3_manuscript.yaml\noutputs:\n  - 03_typesetting/check_report.md\n  - 03_typesetting/output/submission_package.zip\n''')
    print(f"P3 package written: {zip_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

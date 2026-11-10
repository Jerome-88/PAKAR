"""Generate the editable proposal reference from its Markdown source."""
from pathlib import Path
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/PAKAR_BAHAN_PROPOSAL.md"
TARGET = SOURCE.with_suffix(".docx")


def rich(paragraph, text):
    for piece in re.split(r"(\*\*.*?\*\*|`[^`]+`)", text):
        if not piece:
            continue
        run = paragraph.add_run(piece[2:-2] if piece.startswith("**") else piece[1:-1] if piece.startswith("`") else piece)
        if piece.startswith("**"):
            run.bold = True
        elif piece.startswith("`"):
            run.font.name = "Consolas"
            run.font.size = Pt(9)


def export():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2.1)
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string("161616")
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(6)
    for name, size in [("Title", 26), ("Heading 1", 17), ("Heading 2", 13)]:
        style = doc.styles[name]
        style.font.name = "Aptos"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string("161616")
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(16)
        style.paragraph_format.space_after = Pt(8)
    header = section.header.paragraphs[0]
    header.add_run("PAKAR  /  REFERENSI PRODUK DAN TEKNOLOGI").font.size = Pt(9)
    header.runs[0].font.color.rgb = RGBColor.from_string("525252")
    footer = section.footer.paragraphs[0]
    footer.add_run("7 November 2026  ·  Bahan proposal  |  ").font.size = Pt(9)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    doc.core_properties.title = "PAKAR — Bahan Proposal, Tech Stack, dan Alur Sistem"
    doc.core_properties.subject = "Referensi implementasi produk bisnis per 7 November 2026"
    doc.core_properties.author = "PAKAR"
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    index, skip = 0, False
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            skip = not skip
            index += 1
            continue
        if skip or not line.strip():
            index += 1
            continue
        if line.startswith("| "):
            rows = []
            while index < len(lines) and lines[index].startswith("| "):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    rows.append(cells)
                index += 1
            table = doc.add_table(rows=0, cols=len(rows[0]))
            table.style = "Table Grid"
            for row_number, values in enumerate(rows):
                row = table.add_row()
                for cell, value in zip(row.cells, values):
                    rich(cell.paragraphs[0], value)
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.space_after = Pt(5)
                        paragraph.paragraph_format.space_before = Pt(4)
                        for run in paragraph.runs:
                            run.font.size = Pt(9)
                            if row_number == 0:
                                run.bold = True
                    if row_number == 0:
                        shading = OxmlElement("w:shd")
                        shading.set(qn("w:fill"), "F4F4F4")
                        cell._tc.get_or_add_tcPr().append(shading)
                if row_number == 0:
                    repeat = OxmlElement("w:tblHeader")
                    row._tr.get_or_add_trPr().append(repeat)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            continue
        if line.startswith("# "):
            rich(doc.add_paragraph(style="Title"), line[2:])
        elif line.startswith("## "):
            rich(doc.add_paragraph(style="Heading 1"), line[3:])
        elif line.startswith("### "):
            rich(doc.add_paragraph(style="Heading 2"), line[4:])
        elif line.startswith("- "):
            rich(doc.add_paragraph(style="List Bullet"), line[2:])
        else:
            # Keep explicitly numbered steps/sections as authored; no renumbering.
            rich(doc.add_paragraph(), line)
        index += 1
    doc.save(TARGET)
    print(f"Created {TARGET.relative_to(ROOT)} ({TARGET.stat().st_size:,} bytes)")


if __name__ == "__main__":
    export()

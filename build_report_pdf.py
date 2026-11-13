"""Render the plain Markdown report to a simple PDF without header or footer."""

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "REPORT.md"
OUTPUT = ROOT / "output" / "pdf" / "Zep_Reproducibility_Report.pdf"

BODY = ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=8.8, leading=11.9, spaceAfter=4.5, alignment=TA_LEFT
)
TITLE = ParagraphStyle(
    "Title", parent=BODY, fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=13
)
H2 = ParagraphStyle(
    "H2", parent=BODY, fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=10, spaceAfter=4, keepWithNext=True
)
H3 = ParagraphStyle(
    "H3", parent=BODY, fontName="Helvetica-Bold", fontSize=9.8, leading=13, spaceBefore=9, spaceAfter=4, keepWithNext=True
)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=7.5, leading=9.8, spaceAfter=0)


def inline(text):
    text = html.escape(text.strip())
    text = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="black"><u>\1</u></link>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text.replace("  ", " ")


def make_table(lines):
    rows = []
    for line in lines:
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", x) for x in cells):
            continue
        rows.append([Paragraph(inline(x), SMALL) for x in cells])
    width = A4[0] - 40 * mm
    columns = len(rows[0])
    widths = [width * 0.32] + [width * 0.68 / (columns - 1)] * (columns - 1)
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black),
                ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def render():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("| "):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            story.extend([make_table(block), Spacer(1, 6)])
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), TITLE))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), H2))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), H3))
        elif line.startswith("- ") or re.match(r"\d+\.\s", line):
            block = []
            while i < len(lines):
                item = lines[i].strip()
                if item.startswith("- "):
                    block.append(item[2:])
                elif re.match(r"\d+\.\s", item):
                    block.append(re.sub(r"^\d+\.\s", "", item))
                else:
                    break
                i += 1
            story.append(ListFlowable([ListItem(Paragraph(inline(x), BODY), leftIndent=11) for x in block], bulletType="bullet", start="circle", leftIndent=13))
            continue
        else:
            block = [line]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"(?:#|\||- |\d+\.\s)", lines[i + 1].strip()):
                i += 1
                block.append(lines[i].strip())
            story.append(Paragraph(inline(" ".join(block)), BODY))
        i += 1
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="A partial reproduction of Zep's temporal agent memory",
        author="Enterprise2333",
    )
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    render()

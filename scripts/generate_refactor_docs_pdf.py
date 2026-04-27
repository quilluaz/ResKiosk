from __future__ import annotations

from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
OUT_DIR = ROOT / "output" / "pdf"


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1d3557"),
            alignment=TA_CENTER,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="DocMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4a5568"),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Doc",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#1d3557"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Doc",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#2a4365"),
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=5,
        )
    )
    return styles


def page_canvas(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#d7dee9"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, height - 16 * mm, width - 18 * mm, height - 16 * mm)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#4a5568"))
    canvas.drawString(18 * mm, 9 * mm, "ResKiosk Youth Congress Refactor")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def convert_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<font name='Helvetica-Bold'>\1</font>", text)
    return text


def parse_markdown(md_path: Path, pdf_name: str):
    styles = build_styles()
    story = []
    bullet_buffer: list[str] = []
    lines = md_path.read_text(encoding="utf-8").splitlines()

    def flush_bullets():
        nonlocal bullet_buffer, story
        if not bullet_buffer:
            return
        items = [
            ListItem(Paragraph(convert_inline(item), styles["BodyDoc"]))
            for item in bullet_buffer
        ]
        story.append(
            ListFlowable(
                items,
                bulletType="bullet",
                start="circle",
                leftIndent=12,
                bulletFontName="Helvetica",
                bulletFontSize=8,
            )
        )
        story.append(Spacer(1, 4))
        bullet_buffer = []

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        stripped = line.strip()

        if idx == 0 and stripped.startswith("# "):
            story.append(Spacer(1, 20))
            story.append(Paragraph(convert_inline(stripped[2:].strip()), styles["DocTitle"]))
            continue

        if not stripped:
            flush_bullets()
            story.append(Spacer(1, 4))
            continue

        if idx > 0 and idx < 5 and ":" in stripped and not stripped.startswith("## "):
            story.append(Paragraph(convert_inline(stripped), styles["DocMeta"]))
            continue

        if stripped.startswith("# "):
            flush_bullets()
            story.append(PageBreak())
            story.append(Paragraph(convert_inline(stripped[2:].strip()), styles["H1Doc"]))
            continue

        if stripped.startswith("## "):
            flush_bullets()
            story.append(Paragraph(convert_inline(stripped[3:].strip()), styles["H1Doc"]))
            continue

        if stripped.startswith("### "):
            flush_bullets()
            story.append(Paragraph(convert_inline(stripped[4:].strip()), styles["H2Doc"]))
            continue

        if stripped.startswith("- "):
            bullet_buffer.append(stripped[2:].strip())
            continue

        flush_bullets()
        story.append(Paragraph(convert_inline(stripped), styles["BodyDoc"]))

    flush_bullets()
    return story


def build_pdf(md_path: Path, pdf_path: Path):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=md_path.stem,
        author="OpenAI Codex",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    template = PageTemplate(id="main", frames=[frame], onPage=page_canvas)
    doc.addPageTemplates([template])
    story = parse_markdown(md_path, pdf_path.name)
    doc.build(story)


def main():
    targets = {
        DOCS_DIR / "youth_congress_refactor_prd.md": OUT_DIR / "YouthCongress_PRD.pdf",
        DOCS_DIR / "youth_congress_refactor_pbd.md": OUT_DIR / "YouthCongress_Product_Brief.pdf",
    }
    for md_path, pdf_path in targets.items():
        build_pdf(md_path, pdf_path)
        print(f"generated:{pdf_path}")


if __name__ == "__main__":
    main()

"""Render PRESENTATION.md to a readable A4 PDF with narrow margins.

Run from the repo root:

    python build_presentation_pdf.py

Writes PRESENTATION.pdf beside the markdown. Uses Segoe UI for body text so
Romanian diacritics render, and Consolas for code blocks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "PRESENTATION.md"
TARGET = ROOT / "PRESENTATION.pdf"

MARGIN = 12 * mm  # ~0.47 in — narrow, still printable

# ------------------------------------------------------------------ fonts
FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Body", str(FONT_DIR / "segoeui.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", str(FONT_DIR / "segoeuib.ttf")))
pdfmetrics.registerFont(TTFont("Body-Italic", str(FONT_DIR / "segoeuii.ttf")))
pdfmetrics.registerFont(TTFont("Mono", str(FONT_DIR / "consola.ttf")))
pdfmetrics.registerFontFamily(
    "Body", normal="Body", bold="Body-Bold", italic="Body-Italic"
)

INK = colors.HexColor("#14161c")
MUTED = colors.HexColor("#5b6270")
RULE = colors.HexColor("#d8dce4")
ACCENT = colors.HexColor("#2b6cb0")
CODE_BG = colors.HexColor("#f4f6f9")

# ------------------------------------------------------------------ styles
S = {
    "h1": ParagraphStyle(
        "h1", fontName="Body-Bold", fontSize=19, leading=23, textColor=INK,
        spaceBefore=0, spaceAfter=7,
    ),
    "h2": ParagraphStyle(
        "h2", fontName="Body-Bold", fontSize=13.5, leading=17, textColor=ACCENT,
        spaceBefore=13, spaceAfter=5,
    ),
    "h3": ParagraphStyle(
        "h3", fontName="Body-Bold", fontSize=11, leading=14, textColor=INK,
        spaceBefore=8, spaceAfter=3,
    ),
    "body": ParagraphStyle(
        "body", fontName="Body", fontSize=9.4, leading=13.2, textColor=INK,
        alignment=TA_LEFT, spaceAfter=5,
    ),
    "quote": ParagraphStyle(
        "quote", fontName="Body-Italic", fontSize=10.4, leading=14.6,
        textColor=ACCENT, leftIndent=8, spaceBefore=4, spaceAfter=7,
    ),
    "bullet": ParagraphStyle(
        "bullet", fontName="Body", fontSize=9.4, leading=13.2, textColor=INK,
        leftIndent=13, bulletIndent=3, spaceAfter=2.5,
    ),
    "code": ParagraphStyle(
        "code", fontName="Mono", fontSize=8.1, leading=10.6, textColor=INK,
        leftIndent=6, rightIndent=6, spaceBefore=3, spaceAfter=3,
    ),
    "cell": ParagraphStyle(
        "cell", fontName="Body", fontSize=8.6, leading=11.6, textColor=INK,
    ),
    "cellhead": ParagraphStyle(
        "cellhead", fontName="Body-Bold", fontSize=8.6, leading=11.6,
        textColor=colors.white,
    ),
}


def inline(text: str) -> str:
    """Markdown inline -> ReportLab mini-HTML."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font name="Mono" size="8.6">\1</font>', text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<i>\1</i>", text)
    return text


def parse_table(lines: list[str]) -> Table:
    rows: list[list[str]] = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return Table([[""]])

    width = max(len(r) for r in rows)
    for r in rows:
        while len(r) < width:
            r.append("")

    data = [[Paragraph(inline(c), S["cellhead"]) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(inline(c), S["cell"]) for c in r])

    avail = A4[0] - 2 * MARGIN
    table = Table(data, colWidths=[avail / width] * width, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CODE_BG]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_story(markdown_text: str) -> list:
    story: list = []
    lines = markdown_text.replace("\r\n", "\n").split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.strip() == "---":
            story.append(Spacer(1, 5))
            story.append(
                Table([[""]], colWidths=[A4[0] - 2 * MARGIN], rowHeights=[0.6],
                      style=TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.6, RULE)]))
            )
            story.append(Spacer(1, 5))
            i += 1
            continue

        # fenced code
        if line.strip().startswith("```"):
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            body = "<br/>".join(
                x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
                for x in block
            ) or "&nbsp;"
            story.append(
                Table(
                    [[Paragraph(body, S["code"])]],
                    colWidths=[A4[0] - 2 * MARGIN],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                            ("BOX", (0, 0), (-1, -1), 0.4, RULE),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    ),
                )
            )
            story.append(Spacer(1, 5))
            continue

        # table
        if line.strip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            story.append(parse_table(block))
            story.append(Spacer(1, 6))
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            text = inline(heading.group(2))
            if level == 1:
                story.append(Paragraph(text, S["h1"]))
                story.append(
                    Table([[""]], colWidths=[A4[0] - 2 * MARGIN], rowHeights=[1.1],
                          style=TableStyle([("LINEABOVE", (0, 0), (-1, 0), 1.1, ACCENT)]))
                )
                story.append(Spacer(1, 8))
            elif level == 2:
                story.append(Paragraph(text, S["h2"]))
            else:
                story.append(Paragraph(text, S["h3"]))
            i += 1
            continue

        if line.lstrip().startswith(">"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                block.append(lines[i].lstrip()[1:].strip())
                i += 1
            story.append(Paragraph(inline(" ".join(block)), S["quote"]))
            continue

        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        if bullet:
            story.append(Paragraph(inline(bullet.group(1)), S["bullet"], bulletText="•"))
            i += 1
            continue

        numbered = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if numbered:
            num = re.match(r"^\s*(\d+)\.", line).group(1)
            story.append(Paragraph(inline(numbered.group(1)), S["bullet"], bulletText=f"{num}."))
            i += 1
            continue

        block = []
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].strip().startswith(("|", "```", ">", "#", "---"))
            and not re.match(r"^\s*[-*]\s+", lines[i])
            and not re.match(r"^\s*\d+\.\s+", lines[i])
        ):
            block.append(lines[i].strip())
            i += 1
        if block:
            story.append(Paragraph(inline(" ".join(block)), S["body"]))

    return story


def keep_headings_with_content(story: list) -> list:
    """Never leave a section heading alone at the foot of a page.

    A heading is glued to the flowable that follows it, so ReportLab moves the
    pair to the next page together instead of orphaning the title.
    """
    out: list = []
    i = 0
    while i < len(story):
        item = story[i]
        is_heading = (
            isinstance(item, Paragraph)
            and getattr(item.style, "name", "") in ("h2", "h3")
        )
        if is_heading and i + 1 < len(story):
            nxt = story[i + 1]
            # A spacer between heading and body is fine to swallow.
            if isinstance(nxt, Spacer) and i + 2 < len(story):
                out.append(KeepTogether([item, story[i + 2]]))
                i += 3
                continue
            out.append(KeepTogether([item, nxt]))
            i += 2
            continue
        out.append(item)
        i += 1
    return out


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 7.4)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 7 * mm, "MarketPulse AI — prezentarea platformei")
    canvas.drawRightString(A4[0] - MARGIN, 7 * mm, f"{doc.page}")
    canvas.restoreState()


def main() -> int:
    if not SOURCE.exists():
        print(f"missing {SOURCE}", file=sys.stderr)
        return 1

    text = SOURCE.read_text(encoding="utf-8")
    doc = BaseDocTemplate(
        str(TARGET),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 4 * mm,
        title="MarketPulse AI — prezentarea platformei",
        author="FiredMosquito831",
        subject="Hackathon presentation",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    doc.build(keep_headings_with_content(build_story(text)))

    size_kb = TARGET.stat().st_size / 1024
    print(f"wrote {TARGET.name} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

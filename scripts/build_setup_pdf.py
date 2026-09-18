"""Build the maintained Markdown setup guide as a polished PDF."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "SETUP_GUIDE.md"
OUTPUT = ROOT / "output" / "pdf" / "Fabrizio_Chelsea_Bot_Setup_Guide.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = 20 * mm
RIGHT = 18 * mm
TOP = 20 * mm
BOTTOM = 18 * mm
CONTENT_WIDTH = PAGE_WIDTH - LEFT - RIGHT

BLUE = colors.HexColor("#034694")
NAVY = colors.HexColor("#0B1F3A")
SKY = colors.HexColor("#38BDF8")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#5B6474")
PALE = colors.HexColor("#EEF5FC")
LINE = colors.HexColor("#D9E3F0")
GREEN = colors.HexColor("#167D4A")
AMBER = colors.HexColor("#9A5B00")


def _register_fonts() -> tuple[str, str, str, str]:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    bold_candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    mono_candidates = [
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ]
    mono_bold_candidates = [
        Path("C:/Windows/Fonts/consolab.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
    ]

    def register(name: str, paths: list[Path], fallback: str) -> str:
        for path in paths:
            if path.exists():
                pdfmetrics.registerFont(TTFont(name, path))
                return name
        return fallback

    return (
        register("GuideSans", candidates, "Helvetica"),
        register("GuideSansBold", bold_candidates, "Helvetica-Bold"),
        register("GuideMono", mono_candidates, "Courier"),
        register("GuideMonoBold", mono_bold_candidates, "Courier-Bold"),
    )


SANS, SANS_BOLD, MONO, MONO_BOLD = _register_fonts()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "GuideBody",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=9.3,
            leading=13.2,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "GuideSmall",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=7.6,
            leading=10.5,
            textColor=MUTED,
        ),
        "h2": ParagraphStyle(
            "GuideH2",
            parent=base["Heading1"],
            fontName=SANS_BOLD,
            fontSize=18,
            leading=22,
            textColor=NAVY,
            spaceAfter=10,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "GuideH3",
            parent=base["Heading2"],
            fontName=SANS_BOLD,
            fontSize=12.2,
            leading=15,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "bullet": ParagraphStyle(
            "GuideBullet",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=9.1,
            leading=12.7,
            textColor=INK,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=3,
        ),
        "number": ParagraphStyle(
            "GuideNumber",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=9.1,
            leading=12.7,
            textColor=INK,
            leftIndent=16,
            firstLineIndent=-13,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "GuideCode",
            parent=base["Code"],
            fontName=MONO,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#DCEBFF"),
            backColor=NAVY,
            borderPadding=8,
            borderRadius=4,
            spaceBefore=4,
            spaceAfter=9,
        ),
        "callout": ParagraphStyle(
            "GuideCallout",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=9.1,
            leading=13,
            textColor=NAVY,
            backColor=PALE,
            borderColor=SKY,
            borderWidth=0,
            borderPadding=8,
            leftIndent=3,
            spaceBefore=4,
            spaceAfter=9,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName=SANS_BOLD,
            fontSize=31,
            leading=35,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName=SANS,
            fontSize=15,
            leading=21,
            textColor=colors.HexColor("#DCEBFF"),
            spaceAfter=12,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontName=SANS,
            fontSize=9.5,
            leading=14,
            textColor=colors.white,
        ),
        "toc_title": ParagraphStyle(
            "TocTitle",
            parent=base["Heading1"],
            fontName=SANS_BOLD,
            fontSize=22,
            textColor=NAVY,
            spaceAfter=12,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=7.7,
            leading=10.2,
            textColor=INK,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName=SANS_BOLD,
            fontSize=7.8,
            leading=10.2,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
    }


STYLES = _styles()


def _inline(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", rf'<font name="{MONO}">\1</font>', escaped)
    escaped = re.sub(
        r"(?<![\"=>])(https://[^\s<]+)",
        r'<link href="\1" color="#034694">\1</link>',
        escaped,
    )
    return escaped


def _cover(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    canvas.setFillColor(BLUE)
    canvas.circle(PAGE_WIDTH + 10 * mm, PAGE_HEIGHT - 42 * mm, 76 * mm, stroke=0, fill=1)
    canvas.setFillColor(SKY)
    canvas.circle(PAGE_WIDTH - 12 * mm, PAGE_HEIGHT - 32 * mm, 25 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor("#0756AE"))
    canvas.rect(0, 0, PAGE_WIDTH, 15 * mm, stroke=0, fill=1)
    canvas.restoreState()


def _body_page(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(LEFT, PAGE_HEIGHT - 13 * mm, PAGE_WIDTH - RIGHT, PAGE_HEIGHT - 13 * mm)
    canvas.setFont(SANS_BOLD, 7.5)
    canvas.setFillColor(BLUE)
    canvas.drawString(LEFT, PAGE_HEIGHT - 10 * mm, "FABRIZIO CHELSEA BOT")
    canvas.setFont(SANS, 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_WIDTH - RIGHT, PAGE_HEIGHT - 10 * mm, "SETUP GUIDE | AUGUST 2026")
    canvas.line(LEFT, 12 * mm, PAGE_WIDTH - RIGHT, 12 * mm)
    canvas.setFont(SANS, 7.2)
    canvas.drawString(LEFT, 8 * mm, "Official X API v2 | Native reposts | Dry-run by default")
    canvas.drawRightString(PAGE_WIDTH - RIGHT, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


class GuideDocument(BaseDocTemplate):
    def __init__(self, filename: str) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=LEFT,
            rightMargin=RIGHT,
            topMargin=TOP,
            bottomMargin=BOTTOM,
            title="Fabrizio Chelsea Bot - Complete Setup Guide",
            author="Kashyep",
            subject="Setup, deployment, operation, security, and troubleshooting guide",
        )
        cover_frame = Frame(LEFT, 22 * mm, CONTENT_WIDTH, PAGE_HEIGHT - 44 * mm, id="cover")
        body_frame = Frame(LEFT, BOTTOM, CONTENT_WIDTH, PAGE_HEIGHT - TOP - BOTTOM, id="body")
        self.addPageTemplates(
            [
                PageTemplate(id="Cover", frames=[cover_frame], onPage=_cover),
                PageTemplate(id="Body", frames=[body_frame], onPage=_body_page),
            ]
        )

    def afterFlowable(self, flowable) -> None:  # noqa: ANN001
        if not isinstance(flowable, Paragraph):
            return
        style_name = flowable.style.name
        if style_name not in {"GuideH2", "GuideH3"}:
            return
        level = 0 if style_name == "GuideH2" else 1
        text = flowable.getPlainText()
        key = f"heading-{level}-{self.seq.nextf('heading')}"
        self.canv.bookmarkPage(key)
        if level == 0:
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


def _table(rows: list[list[str]]) -> Table:
    column_count = len(rows[0])
    if column_count == 2:
        widths = [CONTENT_WIDTH * 0.32, CONTENT_WIDTH * 0.68]
    elif column_count == 3:
        widths = [CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.53]
    else:
        widths = [CONTENT_WIDTH / column_count] * column_count
    rendered = []
    for row_index, row in enumerate(rows):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table"]
        rendered.append([Paragraph(_inline(cell), style) for cell in row])
    table = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _parse_markdown(source: str) -> list:
    lines = source.splitlines()
    story: list = []
    paragraph_buffer: list[str] = []
    in_code = False
    code_lines: list[str] = []
    first_h2 = True
    skipped_header = False
    index = 0

    def flush_paragraph() -> None:
        if not paragraph_buffer:
            return
        text = " ".join(part.strip() for part in paragraph_buffer)
        style = (
            STYLES["callout"] if text.startswith(("Critical:", "Important:")) else STYLES["body"]
        )
        story.append(Paragraph(_inline(text), style))
        paragraph_buffer.clear()

    while index < len(lines):
        line = lines[index].rstrip()

        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(XPreformatted("\n".join(code_lines), STYLES["code"] or STYLES["body"]))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not line.strip():
            flush_paragraph()
            index += 1
            continue

        if (
            line.startswith("| ")
            and index + 1 < len(lines)
            and re.match(r"^\|[ -:|]+\|$", lines[index + 1])
        ):
            flush_paragraph()
            rows: list[list[str]] = []
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([cell.strip() for cell in lines[index].strip("|").split("|")])
                index += 1
            story.append(_table(rows))
            story.append(Spacer(1, 8))
            continue

        if line == "---":
            flush_paragraph()
            story.append(Spacer(1, 3))
            story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=8))
            index += 1
            continue

        if line.startswith("# "):
            # The title and metadata are represented on the designed cover.
            skipped_header = True
            index += 1
            continue
        if skipped_header and (
            line.startswith("**Version")
            or line.startswith("**Repository")
            or line.startswith("**Purpose")
            or line.startswith("## Complete setup")
        ):
            index += 1
            continue

        if line.startswith("## "):
            flush_paragraph()
            if not first_h2:
                story.append(PageBreak())
            first_h2 = False
            story.append(Paragraph(_inline(line[3:]), STYLES["h2"]))
            story.append(HRFlowable(width=42 * mm, thickness=2.2, color=SKY, hAlign="LEFT"))
            story.append(Spacer(1, 7))
            index += 1
            continue

        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[4:]), STYLES["h3"]))
            index += 1
            continue

        bullet = re.match(r"^\s*-\s+(.+)$", line)
        number = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            story.append(Paragraph(f"-  {_inline(bullet.group(1))}", STYLES["bullet"]))
            index += 1
            continue
        if number:
            flush_paragraph()
            story.append(
                Paragraph(f"{number.group(1)}.  {_inline(number.group(2))}", STYLES["number"])
            )
            index += 1
            continue
        if line.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[2:]), STYLES["callout"]))
            index += 1
            continue

        paragraph_buffer.append(line)
        index += 1

    flush_paragraph()
    return story


def build() -> Path:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOCLevel0",
            fontName=SANS_BOLD,
            fontSize=9.2,
            leading=13,
            textColor=NAVY,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=3,
        ),
        ParagraphStyle(
            "TOCLevel1",
            fontName=SANS,
            fontSize=7.8,
            leading=10,
            textColor=MUTED,
            leftIndent=14,
            firstLineIndent=0,
        ),
    ]

    cover_badge = Table(
        [[Paragraph("OFFICIAL X API V2", STYLES["cover_meta"])]],
        colWidths=[48 * mm],
        rowHeights=[9 * mm],
    )
    cover_badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BLUE),
                ("BOX", (0, 0), (-1, -1), 0.8, SKY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story = [
        Spacer(1, 30 * mm),
        cover_badge,
        Spacer(1, 13 * mm),
        Paragraph("Fabrizio<br/>Chelsea Bot", STYLES["cover_title"]),
        Paragraph(
            "Complete setup, deployment, operations, security, and troubleshooting guide",
            STYLES["cover_subtitle"],
        ),
        Spacer(1, 29 * mm),
        HRFlowable(width=58 * mm, thickness=3, color=SKY, hAlign="LEFT"),
        Spacer(1, 7 * mm),
        Paragraph(
            "Native Chelsea-only reposts from @FabrizioRomano<br/>"
            "Dry-run by default | Idempotent state | GitHub Actions + Docker<br/><br/>"
            "Version 1.0 | August 2026 | Kashyep",
            STYLES["cover_meta"],
        ),
        NextPageTemplate("Body"),
        PageBreak(),
        Paragraph("Contents", STYLES["toc_title"]),
        Paragraph(
            "Use the linked entries below to move through the guide. "
            "Page numbers include the cover.",
            STYLES["small"],
        ),
        Spacer(1, 5 * mm),
        toc,
        PageBreak(),
    ]
    story.extend(_parse_markdown(SOURCE.read_text(encoding="utf-8")))

    document = GuideDocument(str(OUTPUT))
    document.multiBuild(story)
    return OUTPUT


if __name__ == "__main__":
    try:
        result = build()
    except Exception as exc:  # pragma: no cover - CLI build error
        print(f"PDF build failed: {exc}", file=sys.stderr)
        raise
    print(result)

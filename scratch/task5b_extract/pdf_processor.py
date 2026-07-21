"""
pdf_processor.py

Extracts structural drawing content from vector PDF blueprints: sheet
titles, text annotations, structural schedule tables (beam/column
schedules), and vector line/curve geometry — normalized into the same
kind of DOM-ish summary shape the DXF side produces, so the pipeline and
frontend can treat DWG/DXF/PDF uploads uniformly.

Two libraries, two jobs:
  - pypdf: fast page count / metadata / basic text extraction fallback.
  - pdfplumber: the real work — per-page text with positions, table
    detection (for schedules), and vector line/curve objects.

This targets vector-drawn PDFs (e.g. exported from AutoCAD/Revit). Scanned
raster PDFs will yield a page count and little else, which is reported
back explicitly rather than silently returning an empty result.
"""

import re
from collections import defaultdict
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

# Titleblock-ish text near the top of a sheet is treated as a candidate
# sheet title. Keeping this heuristic simple and explainable rather than
# guessing too cleverly at layout.
TITLE_Y_FRACTION = 0.08  # top 8% of the page

# A row of mostly-numeric/short tokens with a size-like pattern (e.g.
# "300x400", "12mm", "Ø16") is treated as schedule-table content.
SIZE_PATTERN = re.compile(
    r"(\d{2,4}\s*[xX]\s*\d{2,4})|(\u00d8\s?\d{1,2})|(\bDIA\.?\s?\d{1,2}\b)",
    re.IGNORECASE,
)
SCHEDULE_KEYWORDS = ("SCHEDULE", "COLUMN SCHEDULE", "BEAM SCHEDULE", "FOOTING SCHEDULE")


def _get_page_count(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def _extract_sheet_title(page) -> str | None:
    """Best-effort sheet title: the topmost line of text on the page,
    which is where titleblocks and sheet headers conventionally sit."""
    words = page.extract_words()
    if not words:
        return None
    top_cutoff = page.height * TITLE_Y_FRACTION
    top_words = [w for w in words if w["top"] <= top_cutoff]
    if not top_words:
        top_words = words[:8]
    top_words.sort(key=lambda w: (round(w["top"]), w["x0"]))
    title = " ".join(w["text"] for w in top_words[:12]).strip()
    return title or None


def _extract_schedule_tables(page) -> list[dict]:
    """Detect and extract table-like structures that look like structural
    schedules (beam/column/footing schedules), using pdfplumber's table
    finder plus a keyword/size-pattern check so we don't misclassify
    unrelated tables (e.g. a general notes block)."""
    schedules = []
    for table in page.find_tables():
        rows = table.extract()
        if not rows or len(rows) < 2:
            continue
        flat_text = " ".join(
            str(cell) for row in rows for cell in row if cell
        ).upper()
        looks_like_schedule = (
            any(kw in flat_text for kw in SCHEDULE_KEYWORDS)
            or bool(SIZE_PATTERN.search(flat_text))
        )
        if not looks_like_schedule:
            continue
        header, *body = rows
        schedules.append({
            "type": "schedule_table",
            "header": [c.strip() if c else "" for c in header],
            "rows": [
                [c.strip() if c else "" for c in row] for row in body
            ],
            "bbox": table.bbox,
        })
    return schedules


def _extract_text_annotations(page) -> list[dict]:
    """Free-standing text (not already captured as a schedule row):
    dimensions, notes, member tags like 'C-1', 'GB-2'."""
    annotations = []
    for word in page.extract_words():
        annotations.append({
            "type": "text",
            "text": word["text"],
            "x": round(word["x0"], 2),
            "y": round(word["top"], 2),
        })
    return annotations


def _extract_vector_geometry(page) -> list[dict]:
    """Vector lines, rects, and curves as generic geometry elements —
    the PDF equivalent of DXF LINE/LWPOLYLINE entities."""
    elements = []
    for line in page.lines:
        elements.append({
            "type": "line",
            "p1": (round(line["x0"], 2), round(line["top"], 2)),
            "p2": (round(line["x1"], 2), round(line["bottom"], 2)),
        })
    for rect in page.rects:
        elements.append({
            "type": "rect",
            "x0": round(rect["x0"], 2), "top": round(rect["top"], 2),
            "x1": round(rect["x1"], 2), "bottom": round(rect["bottom"], 2),
        })
    for curve in page.curves:
        pts = curve.get("pts") or []
        elements.append({
            "type": "curve",
            "points": [(round(x, 2), round(y, 2)) for x, y in pts],
        })
    return elements


def extract_pdf_drawing_elements(pdf_path: str) -> dict:
    """Main entry point. Returns a DOM-ish dict:

        {
          "total_entities": int,
          "page_count": int,
          "layers": [...],       # PDFs have no CAD layers; sheet titles
                                  # are used as the closest analogue so the
                                  # frontend has something meaningful to show
          "elements": [...],     # merged text / schedule / geometry records
          "is_likely_scanned": bool,
        }
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    page_count = _get_page_count(pdf_path)
    elements: list[dict] = []
    sheet_titles: list[str] = []
    text_word_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            title = _extract_sheet_title(page)
            if title:
                sheet_titles.append(title)

            schedules = _extract_schedule_tables(page)
            for s in schedules:
                s["page"] = page_index + 1
            elements.extend(schedules)

            annotations = _extract_text_annotations(page)
            text_word_count += len(annotations)
            for a in annotations:
                a["page"] = page_index + 1
            elements.extend(annotations)

            geometry = _extract_vector_geometry(page)
            for g in geometry:
                g["page"] = page_index + 1
            elements.extend(geometry)

    is_likely_scanned = text_word_count == 0 and page_count > 0

    return {
        "total_entities": len(elements),
        "page_count": page_count,
        "layers": sheet_titles or [f"Sheet {i + 1}" for i in range(page_count)],
        "elements": elements,
        "is_likely_scanned": is_likely_scanned,
    }

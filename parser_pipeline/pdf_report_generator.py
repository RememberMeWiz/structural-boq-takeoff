"""
Executive PDF Report Generator for the Quantity Takeoff / BOQ system.

Produces a formatted, print-ready PDF summarizing the same data the Excel
generator (`boq_excel_generator.py`) exports, per tech_spec.md Section 2.9
("PDF Export: Formal BOQ summary reports via WeasyPrint or reportlab").

This module deliberately does NOT recompute any quantities or costs itself.
It only formats and rolls up numbers that `FajardoTakeoffEngine` already
produced (`backup_rows`, `summarize_to_boq()`, `unit_cost_for_row()`), so the
PDF, the Excel workbook, and the underlying engine can never disagree with
each other on the arithmetic -- only on presentation.

Report contents:
    1. Cover page (project identification)
    2. Project Summary (trade subtotals + grand total + QA snapshot)
    3. Section detail + subtotal for Concrete Works
    4. Section detail + subtotal for Steel Reinforcement
    5. Section detail + subtotal for Masonry Works
    6. BOQ Checklist Summary (rolled-up items, matches the Excel "Checklist
       BOQ Summary" sheet)
    7. Drawing Element Traceability Notes (which drawing sheet / location
       every line item traces back to) + QA cross-check warnings appendix

Uses reportlab (WeasyPrint is unavailable in this environment / has no
system-level dependency support here; reportlab is the supported fallback
named in tech_spec.md Section 2.9 and Section 2.10).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from parser_pipeline.fajardo_takeoff_engine import (
        BackupComputationRow,
        BOQChecklistItem,
        FajardoTakeoffEngine,
    )
except ModuleNotFoundError:
    from fajardo_takeoff_engine import (
        BackupComputationRow,
        BOQChecklistItem,
        FajardoTakeoffEngine,
    )

# ====================================================================
# THEME (mirrors boq_excel_generator.py so PDF and Excel look related)
# ====================================================================

NAVY = colors.HexColor("#1F4E78")
LIGHT_BLUE = colors.HexColor("#D9E1F2")
LIGHT_GRAY = colors.HexColor("#F2F2F2")
GRID_GRAY = colors.HexColor("#D9D9D9")
WARNING_RED = colors.HexColor("#C00000")
WARNING_BG = colors.HexColor("#FCE4E4")
MUTED_TEXT = colors.HexColor("#595959")

# Canonical work-section ordering & short labels for section headers
WORK_SECTIONS: List[tuple] = [
    ("II. Concrete Works", "Concrete Works"),
    ("III. Steel Reinforcement", "Steel Reinforcement"),
    ("IV. Masonry Works", "Masonry Works"),
]


# ====================================================================
# PROJECT METADATA
# ====================================================================

@dataclass
class ProjectInfo:
    project_name: str = "Untitled Project"
    project_location: str = ""
    client_name: str = ""
    prepared_by: str = ""
    checked_by: str = ""
    report_date: str = field(default_factory=lambda: date.today().strftime("%B %d, %Y"))
    drawing_set_refs: List[str] = field(default_factory=list)
    currency_symbol: str = "PHP"
    report_title: str = "Executive Bill of Quantities Report"


# ====================================================================
# FORMATTING HELPERS
# ====================================================================

def _money(value: float, currency: str = "PHP") -> str:
    return f"{currency} {value:,.2f}"


def _qty(value: float) -> str:
    return f"{value:,.2f}"


def _amount_for_row(engine: FajardoTakeoffEngine, row: BackupComputationRow) -> float:
    """Mirrors the Excel sheet's `=Qty * UnitCost` formula (col J * col L)."""
    return row.quantity * engine.unit_cost_for_row(row)


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle", parent=base["Title"], fontSize=24, leading=28,
            textColor=NAVY, spaceAfter=6, alignment=TA_CENTER,
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle", parent=base["Normal"], fontSize=12, leading=16,
            textColor=MUTED_TEXT, alignment=TA_CENTER, spaceAfter=4,
        ),
        "CoverField": ParagraphStyle(
            "CoverField", parent=base["Normal"], fontSize=11, leading=16,
            alignment=TA_CENTER,
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading", parent=base["Heading1"], fontSize=15, leading=18,
            textColor=NAVY, spaceBefore=4, spaceAfter=10,
            borderColor=NAVY, borderWidth=0, borderPadding=0,
        ),
        "SubHeading": ParagraphStyle(
            "SubHeading", parent=base["Heading2"], fontSize=11.5, leading=14,
            textColor=NAVY, spaceBefore=10, spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "Body", parent=base["Normal"], fontSize=9.5, leading=13,
        ),
        "Muted": ParagraphStyle(
            "Muted", parent=base["Normal"], fontSize=8.5, leading=11,
            textColor=MUTED_TEXT,
        ),
        "CellSmall": ParagraphStyle(
            "CellSmall", parent=base["Normal"], fontSize=7.6, leading=9.2,
        ),
        "CellSmallRight": ParagraphStyle(
            "CellSmallRight", parent=base["Normal"], fontSize=7.6, leading=9.2,
            alignment=TA_RIGHT,
        ),
        "CellSmallCenter": ParagraphStyle(
            "CellSmallCenter", parent=base["Normal"], fontSize=7.6, leading=9.2,
            alignment=TA_CENTER,
        ),
        "CellWarning": ParagraphStyle(
            "CellWarning", parent=base["Normal"], fontSize=7.6, leading=9.2,
            textColor=WARNING_RED,
        ),
    }
    return styles


# ====================================================================
# HEADER / FOOTER
# ====================================================================

def _make_page_decorator(project_info: ProjectInfo):
    def _decorate(canvas, doc):
        canvas.saveState()
        page_w, page_h = LETTER

        # Footer rule + text (skip on the cover page, doc.page starts at 1)
        if doc.page > 1:
            canvas.setStrokeColor(GRID_GRAY)
            canvas.setLineWidth(0.5)
            canvas.line(0.75 * inch, 0.65 * inch, page_w - 0.75 * inch, 0.65 * inch)

            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(MUTED_TEXT)
            canvas.drawString(0.75 * inch, 0.48 * inch, project_info.project_name)
            canvas.drawCentredString(
                page_w / 2, 0.48 * inch,
                "Executive BOQ Report -- Confidential Draft for Internal Review",
            )
            canvas.drawRightString(page_w - 0.75 * inch, 0.48 * inch, f"Page {doc.page - 1}")

        canvas.restoreState()

    return _decorate


# ====================================================================
# COVER PAGE
# ====================================================================

def _build_cover(story: List, project_info: ProjectInfo, engine: FajardoTakeoffEngine):
    s = _styles()
    story.append(Spacer(1, 1.6 * inch))
    story.append(Paragraph(project_info.report_title.upper(), s["CoverTitle"]))
    story.append(Paragraph(
        "Concrete &nbsp;|&nbsp; Steel Reinforcement &nbsp;|&nbsp; Masonry (CHB) Works",
        s["CoverSubtitle"],
    ))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"<b>{project_info.project_name}</b>", ParagraphStyle(
        "ProjName", parent=s["CoverField"], fontSize=16, textColor=NAVY, spaceAfter=6)))
    if project_info.project_location:
        story.append(Paragraph(project_info.project_location, s["CoverField"]))
    story.append(Spacer(1, 0.6 * inch))

    field_rows = []
    if project_info.client_name:
        field_rows.append(["Client", project_info.client_name])
    field_rows.append(["Report Date", project_info.report_date])
    if project_info.drawing_set_refs:
        field_rows.append(["Drawing Set Reference(s)", ", ".join(project_info.drawing_set_refs)])
    field_rows.append(["Prepared By", project_info.prepared_by or "________________________"])
    field_rows.append(["Checked By", project_info.checked_by or "________________________"])

    grand_total = sum(_amount_for_row(engine, r) for r in engine.backup_rows)
    field_rows.append(["Grand Total Direct Cost", _money(grand_total, project_info.currency_symbol)])

    tbl = Table(
        [[Paragraph(f"<b>{label}</b>", s["Body"]), Paragraph(value, s["Body"])] for label, value in field_rows],
        colWidths=[2.3 * inch, 3.4 * inch],
        hAlign="CENTER",
    )
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, GRID_GRAY),
        ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY),
        ("FONTNAME", (1, -1), (1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, -1), (1, -1), NAVY),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.9 * inch))
    story.append(Paragraph(
        "This report is a formatted summary derived from the Back-Up Computation "
        "and Checklist BOQ Summary of the linked <i>takeoff_boq_schedule.xlsx</i> "
        "workbook. Quantities are computed using Max Fajardo's Simplified "
        "Construction Estimate methodology with automated dual cross-checking "
        "(Section 2.5-2.7 of the project's Technical Specifications).",
        s["Muted"],
    ))
    story.append(PageBreak())


# ====================================================================
# PROJECT SUMMARY
# ====================================================================

def _build_project_summary(story: List, project_info: ProjectInfo, engine: FajardoTakeoffEngine):
    s = _styles()
    story.append(Paragraph("1. Project Summary", s["SectionHeading"]))

    section_totals: Dict[str, float] = {full: 0.0 for full, _ in WORK_SECTIONS}
    section_counts: Dict[str, int] = {full: 0 for full, _ in WORK_SECTIONS}
    other_total = 0.0
    other_count = 0

    for row in engine.backup_rows:
        amt = _amount_for_row(engine, row)
        if row.work_section in section_totals:
            section_totals[row.work_section] += amt
            section_counts[row.work_section] += 1
        else:
            other_total += amt
            other_count += 1

    grand_total = sum(section_totals.values()) + other_total

    header = ["Work Section", "Line Items", "Subtotal Amount"]
    data = [header]
    for full, short in WORK_SECTIONS:
        data.append([short, str(section_counts[full]), _money(section_totals[full], project_info.currency_symbol)])
    if other_count:
        data.append(["Other / Unclassified Works", str(other_count), _money(other_total, project_info.currency_symbol)])
    data.append(["GRAND TOTAL PROJECT DIRECT COST", str(len(engine.backup_rows)), _money(grand_total, project_info.currency_symbol)])

    tbl = Table(data, colWidths=[3.2 * inch, 1.2 * inch, 2.3 * inch], hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_BLUE]),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 0.3 * inch))

    # QA snapshot
    story.append(Paragraph("Quality Assurance Snapshot", s["SubHeading"]))
    total_checks = len(engine.calculation_checks)
    warnings = engine.qa_warnings
    qa_text = (
        f"{total_checks} independent dual cross-check computations were run across all "
        f"takeoff elements (Volume vs. Linear-Meter for concrete, Area vs. Block-Course "
        f"for masonry, and table-value vs. theoretical weight for reinforcement). "
        f"<b>{len(warnings)}</b> check(s) exceeded the approved 2% divergence threshold "
        f"and are flagged for manual review -- see Section 6, \"QA Cross-Check Warnings.\""
    )
    story.append(Paragraph(qa_text, s["Body"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(PageBreak())


# ====================================================================
# SECTION DETAIL (Back-Up Computation) TABLES
# ====================================================================

def _detail_table(rows: List[BackupComputationRow], engine: FajardoTakeoffEngine, s, currency: str) -> Table:
    header = ["Item Code", "Description", "Location", "Drwg\nRef", "Qty", "Unit", "Unit Cost", "Amount", "Status"]
    data = [header]
    subtotal = 0.0

    for row in rows:
        amount = _amount_for_row(engine, row)
        subtotal += amount
        is_warning = "QA warning" in row.status
        status_style = s["CellWarning"] if is_warning else s["CellSmallCenter"]
        data.append([
            Paragraph(row.item_code, s["CellSmallCenter"]),
            Paragraph(row.description, s["CellSmall"]),
            Paragraph(row.location_description, s["CellSmall"]),
            Paragraph(row.drawing_ref, s["CellSmallCenter"]),
            Paragraph(_qty(row.quantity), s["CellSmallRight"]),
            Paragraph(row.unit, s["CellSmallCenter"]),
            Paragraph(_qty(engine.unit_cost_for_row(row)), s["CellSmallRight"]),
            Paragraph(_qty(amount), s["CellSmallRight"]),
            Paragraph("Warning" if is_warning else "OK", status_style),
        ])

    data.append([
        "", "", "", "", "", "", Paragraph("<b>Section Subtotal</b>", s["CellSmallRight"]),
        Paragraph(f"<b>{_money(subtotal, currency)}</b>", s["CellSmallRight"]), "",
    ])

    col_widths = [0.62 * inch, 1.62 * inch, 1.15 * inch, 0.42 * inch, 0.55 * inch, 0.45 * inch, 0.68 * inch, 0.75 * inch, 0.55 * inch]
    tbl = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -2), 0.4, GRID_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_BLUE]),
        ("SPAN", (0, -1), (5, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]

    # Highlight warning rows
    for idx, row in enumerate(rows, start=1):
        if "QA warning" in row.status:
            style.append(("BACKGROUND", (0, idx), (-1, idx), WARNING_BG))

    tbl.setStyle(TableStyle(style))
    return tbl, subtotal


def _build_section_detail(story: List, section_number: int, full_section: str, short_label: str,
                           engine: FajardoTakeoffEngine, project_info: ProjectInfo):
    s = _styles()
    rows = [r for r in engine.backup_rows if r.work_section == full_section]

    story.append(Paragraph(f"{section_number}. {short_label} -- Back-Up Computation", s["SectionHeading"]))
    if not rows:
        story.append(Paragraph("No line items recorded for this trade in the current takeoff.", s["Body"]))
        story.append(PageBreak())
        return 0.0

    tbl, subtotal = _detail_table(rows, engine, s, project_info.currency_symbol)
    story.append(tbl)
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        f"<b>{len(rows)}</b> line item(s) recorded for {short_label}. Each row traces to its "
        f"source drawing sheet (\"Drwg Ref\") and plan location, per Section 2.7/2.8 of the "
        f"Technical Specifications.",
        s["Muted"],
    ))
    story.append(PageBreak())
    return subtotal


# ====================================================================
# BOQ CHECKLIST SUMMARY (rolled up)
# ====================================================================

def _build_boq_summary(story: List, section_number: int, engine: FajardoTakeoffEngine, project_info: ProjectInfo):
    s = _styles()
    story.append(Paragraph(f"{section_number}. BOQ Checklist Summary", s["SectionHeading"]))
    story.append(Paragraph(
        "Rolled-up quantities by item code, matching the \"Checklist BOQ Summary\" sheet of "
        "the linked Excel workbook. The Amount column uses a blended unit cost derived from "
        "the underlying Back-Up Computation rows.",
        s["Body"],
    ))
    story.append(Spacer(1, 0.12 * inch))

    boq_items: List[BOQChecklistItem] = engine.summarize_to_boq()

    # Compute blended amount/unit-cost per item code from the backup rows,
    # exactly mirroring the SUMIF formulas in boq_excel_generator.py.
    amounts_by_code: Dict[str, float] = {}
    for row in engine.backup_rows:
        amounts_by_code.setdefault(row.item_code, 0.0)
        amounts_by_code[row.item_code] += _amount_for_row(engine, row)

    header = ["Item No.", "Item Code", "Description", "Unit", "Qty", "Blended Unit Cost", "Amount"]
    data = [header]
    grand_total = 0.0
    for item in boq_items:
        amount = amounts_by_code.get(item.item_code, 0.0)
        grand_total += amount
        blended_uc = (amount / item.qty) if item.qty else 0.0
        data.append([
            Paragraph(item.item_no, s["CellSmallCenter"]),
            Paragraph(item.item_code, s["CellSmallCenter"]),
            Paragraph(item.description, s["CellSmall"]),
            Paragraph(item.unit, s["CellSmallCenter"]),
            Paragraph(_qty(item.qty), s["CellSmallRight"]),
            Paragraph(_qty(blended_uc), s["CellSmallRight"]),
            Paragraph(_qty(amount), s["CellSmallRight"]),
        ])

    data.append([
        "", "", "", "", "", Paragraph("<b>Grand Total</b>", s["CellSmallRight"]),
        Paragraph(f"<b>{_money(grand_total, project_info.currency_symbol)}</b>", s["CellSmallRight"]),
    ])

    col_widths = [0.6 * inch, 0.7 * inch, 2.55 * inch, 0.55 * inch, 0.7 * inch, 1.1 * inch, 1.0 * inch]
    tbl = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -2), 0.4, GRID_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_BLUE]),
        ("SPAN", (0, -1), (4, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GRAY),
        ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story.append(tbl)
    story.append(PageBreak())


# ====================================================================
# DRAWING ELEMENT TRACEABILITY NOTES + QA WARNINGS APPENDIX
# ====================================================================

def _build_traceability_notes(story: List, section_number: int, engine: FajardoTakeoffEngine):
    s = _styles()
    story.append(Paragraph(f"{section_number}. Drawing Element Traceability Notes", s["SectionHeading"]))
    story.append(Paragraph(
        "Every Back-Up Computation line item traces back to an originating drawing sheet "
        "and plan location, per tech_spec.md Section 1.3 item 7 (\"Traceability & "
        "Verification\"). The index below groups line items by source drawing sheet so a "
        "reviewer can cross-reference the BOQ against the working drawings sheet-by-sheet.",
        s["Body"],
    ))
    story.append(Spacer(1, 0.12 * inch))

    by_drawing: Dict[str, List[BackupComputationRow]] = {}
    for row in engine.backup_rows:
        by_drawing.setdefault(row.drawing_ref or "(unreferenced)", []).append(row)

    header = ["Drawing Ref", "Location / Element", "Item Code(s)", "Work Section"]
    data = [header]
    for drawing_ref in sorted(by_drawing.keys()):
        rows = by_drawing[drawing_ref]
        # group by location within this drawing to avoid one row per rebar spec
        by_location: Dict[str, Dict[str, set]] = {}
        for r in rows:
            loc = by_location.setdefault(r.location_description, {"codes": set(), "sections": set()})
            loc["codes"].add(r.item_code)
            loc["sections"].add(r.work_section.split(". ", 1)[-1])
        first = True
        for loc_desc, info in by_location.items():
            data.append([
                Paragraph(drawing_ref if first else "", s["CellSmallCenter"]),
                Paragraph(loc_desc, s["CellSmall"]),
                Paragraph(", ".join(sorted(info["codes"])), s["CellSmall"]),
                Paragraph(", ".join(sorted(info["sections"])), s["CellSmall"]),
            ])
            first = False

    col_widths = [0.9 * inch, 2.6 * inch, 2.0 * inch, 1.7 * inch]
    tbl = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.25 * inch))

    # QA cross-check warnings appendix
    story.append(Paragraph("QA Cross-Check Warnings", s["SubHeading"]))
    warnings = engine.qa_warnings
    if not warnings:
        story.append(Paragraph(
            "No dual cross-check exceeded the approved 2% divergence threshold. All "
            "element quantities are confirmed by two independent derivation methods.",
            s["Body"],
        ))
    else:
        story.append(Paragraph(
            f"The following {len(warnings)} check(s) diverged by more than 2% between "
            f"their two independent derivation methods and require manual review before "
            f"BOQ sign-off:",
            s["Body"],
        ))
        story.append(Spacer(1, 0.08 * inch))
        wheader = ["Element ID", "Check", "Method A", "Method B", "Divergence"]
        wdata = [wheader]
        for chk in warnings:
            wdata.append([
                Paragraph(chk.element_id, s["CellSmallCenter"]),
                Paragraph(chk.check_name, s["CellSmall"]),
                Paragraph(_qty(chk.primary_quantity), s["CellSmallRight"]),
                Paragraph(_qty(chk.secondary_quantity), s["CellSmallRight"]),
                Paragraph(f"{chk.divergence_ratio * 100:.1f}%", s["CellWarning"]),
            ])
        wtbl = Table(wdata, colWidths=[0.9 * inch, 2.7 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch], repeatRows=1, hAlign="LEFT")
        wtbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), WARNING_RED),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, GRID_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, WARNING_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        story.append(wtbl)


# ====================================================================
# PUBLIC ENTRY POINT
# ====================================================================

def generate_pdf_report(
    engine: FajardoTakeoffEngine,
    project_info: Optional[ProjectInfo] = None,
    output_path: str = "outputs/executive_boq_report.pdf",
) -> str:
    """Build the executive PDF report and write it to `output_path`."""
    project_info = project_info or ProjectInfo()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.9 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title=project_info.report_title,
        author=project_info.prepared_by or "Fajardo Takeoff & BOQ System",
    )

    story: List = []
    _build_cover(story, project_info, engine)
    _build_project_summary(story, project_info, engine)

    section_no = 2
    for full_section, short_label in WORK_SECTIONS:
        _build_section_detail(story, section_no, full_section, short_label, engine, project_info)
        section_no += 1

    _build_boq_summary(story, section_no, engine, project_info)
    section_no += 1
    _build_traceability_notes(story, section_no, engine)

    decorator = _make_page_decorator(project_info)
    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    print(f"Successfully generated Executive PDF Report: {output_path}")
    return output_path


# ====================================================================
# CLI / DEMO EXECUTION (uses the same sample elements as the Excel generator)
# ====================================================================

if __name__ == "__main__":
    try:
        from parser_pipeline.fajardo_takeoff_engine import TakeoffElement
    except ModuleNotFoundError:
        from fajardo_takeoff_engine import TakeoffElement

    eng = FajardoTakeoffEngine()

    test_elements = [
        TakeoffElement("e1", "footing", "F-1", "Grid 1-A to 4-D", "S-1", 1.5, 1.5, 0.4, 12, "Class A",
                        [{"diameter": 16, "count": 10, "length": 1.7}]),
        TakeoffElement("e2", "column", "C-1", "Ground to 2nd Floor", "S-1", 0.35, 0.35, 3.2, 12, "Class A",
                        [{"diameter": 20, "count": 8, "length": 3.8}, {"diameter": 10, "count": 22, "length": 1.3}]),
        TakeoffElement("e3", "beam", "2B-1", "2nd Floor Framing", "S-2", 6.0, 0.30, 0.50, 8, "Class A",
                        [{"diameter": 20, "count": 6, "length": 6.8}, {"diameter": 10, "count": 35, "length": 1.5}]),
        TakeoffElement("e4", "chb_wall", "W-1", "Exterior Perimeter Wall", "A-1", 35.0, 0.15, 3.0, 1,
                        chb_thickness="150mm", plaster_faces=2),
        # A deliberately small/short wall segment to exercise the CHB dual
        # cross-check warning path in the demo output.
        TakeoffElement("e5", "chb_wall", "W-2", "Utility Room Partition, Ground Floor", "A-2", 1.1, 0.10, 3.0, 1,
                        chb_thickness="100mm", plaster_faces=2),
    ]
    for elem in test_elements:
        if elem.element_type in ["footing", "column", "beam", "slab"]:
            eng.process_concrete_element(elem)
            if elem.rebar_specs:
                eng.process_rebar_specs(elem)
        elif elem.element_type == "chb_wall":
            eng.process_masonry_element(elem)

    info = ProjectInfo(
        project_name="Sample 2-Storey Residential Building",
        project_location="Bacolod City, Negros Occidental, Philippines",
        client_name="Sample Client Holdings, Inc.",
        prepared_by="Automated Takeoff & BOQ System",
        checked_by="",
        drawing_set_refs=["S-1", "S-2", "A-1", "A-2"],
    )

    generate_pdf_report(eng, info, "outputs/executive_boq_report.pdf")

# Automated Quantity Takeoff & BOQ Generation System — Master Project Roadmap

*Companion to: Automated Quantity Takeoff and Bill of Quantities (BOQ) Generation System — Objectives Statement and Technical Specifications, v2.0*

**Core scope (this roadmap's spine):** Concrete Works, Steel Reinforcement, Masonry (CHB) — quantities *and* costing.
**Stretch track (parallel, non-blocking):** all other trades, OCR/raster PDF path, full project-cost roll-up.

---

## Phase 0 — Foundations ✅ Complete

- Objectives Statement and Scope defined; costing brought into core scope alongside quantities.
- Formula Library architecture defined (versioned, swappable data model — `factor_id`, `trade`, `qa_status`, etc.).
- Reference workbook (`UY_Louis.xlsx`) reviewed and scoped down.

## Phase 1 — Input & Extraction ✅ Complete

- DWG → DXF normalization pipeline (ODA File Converter CLI).
- DXF geometry + text extraction (`ezdxf`, `dxf_parser.py`, `extractor.py`).
- Element classification cascade: layer match → block/insert match → schedule cross-reference → geometric fallback (`dom_mapper.py`).
- Beam/Column label parsing from CAD annotations (`member_size_extractor.py`).

## Phase 2 — BOQ Takeoff Engine & Costing ✅ Complete

- Concrete Volume Module (Fajardo Class AA/A/B/C ratios) — *Verified against v2.0 Tech Spec*.
- Steel Reinforcement Module (bar cutting lengths, PNS 49/ASTM A615 unit weights, G.I. tie wire rates) — *Verified against v2.0 Tech Spec*.
- Masonry Module (CHB wall area net of post/opening deductions, mortar joint fill, 16mm plastering) — *Verified against v2.0 Tech Spec*.
- Live Excel BOQ Generator (`openpyxl` exporting Back-Up Computation, Checklist Summary, and Unit Cost Derivation sheets: `takeoff_boq_schedule.xlsx`).
- **Phase 2 Final QA Audit & Validation Sign-off**: Full script syntax, zero formula error validation (`#REF!`, `#VALUE!`), dual calculation cross-checking, and audit report sign-off (`outputs/qa/project_audit_report.md`).

## Phase 3 — Polishing & Shipping 🚀 (Active Phase)

- **Interactive Review UI Dashboard**: React / TailwindCSS frontend featuring a side-by-side CAD drawing viewer and interactive BOQ table.
- **Manual Override & Validation Workflow**: Engineers can inspect low-confidence extractions, edit quantities/prices, and review dual calculation cross-check warnings.
- **Executive PDF Report Generator**: Exporting styled print reports (`WeasyPrint` / `reportlab`) with section subtotals and traceability notes.
- **Automated ODA Conversion Pipeline**: Drag-and-drop DWG/DXF ingestion with automated local ODA File Converter CLI execution and status feedback.
- **Application Packaging & Shipping**: Packaging the standalone desktop/web app executable, installer, and end-to-end user documentation.

---

## Stretch Track (parallel, non-blocking)

- Formula libraries for other trades (Site Prep, Formworks, Roofing, Doors & Windows, Tiles, Painting, Plumbing, Electrical, Mechanical).
- Scanned/raster PDF path: OCR + multi-sample scale calibration.
- Full Summary of Total Project Cost roll-up (Indirect Costs, Professional Fees, VAT).

---

## Dependency Summary

```
Phase 0 (Foundations) ✅ ──→ Phase 1 (Input & Extraction) ✅ ──→ Phase 2 (Takeoff Engine & Excel) ✅ ──→ Phase 3 (UI, PDF & Shipping) 🚀
                                                                                                          │
                                                            Stretch Track (parallel, non-blocking) ───────┘
```

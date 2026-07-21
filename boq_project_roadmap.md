# Automated Quantity Takeoff & BOQ Generation System — Project Roadmap

*Companion to: Automated Quantity Takeoff and Bill of Quantities (BOQ) Generation System — Objectives Statement and Technical Specifications, Draft v0.4*

**Core scope (this roadmap's spine):** Concrete Works, Steel Reinforcement, Masonry (CHB) — quantities *and* costing.
**Stretch track (parallel, non-blocking):** all other trades, OCR/raster PDF path, full project-cost roll-up.

---

## Phase 0 — Foundations ✅ Complete

- Objectives Statement and Scope defined; costing brought into core scope alongside quantities.
- Formula Library architecture defined (versioned, swappable data model — `factor_id`, `trade`, `qa_status`, etc.).
- Reference workbook (`UY_Louis.xlsx`) reviewed and **scoped down**: its unit-cost *methodology* is a usable pattern, its computed *quantities* are unverified and excluded as a data source.
- `cut_length_program.xlsx` / rebar cut-length pipeline reviewed and **excluded** as a reference — that project is still mid-debugging and not validated.

## Phase 1 — Input & Extraction

- DWG → DXF normalization pipeline (ODA File Converter).
- DXF / vector-PDF geometry + text extraction (ezdxf, PyMuPDF, pdfplumber).
- Element classification cascade: layer match → block/insert match → schedule cross-reference → geometric fallback.
- Beam/Column label parsing from CAD annotations (mark, size, type) linked to geometry — extends the existing beam-label regex work into the classification layer.
- **Depends on:** nothing upstream — first buildable phase.

## Phase 2 — Formula Library QA *(blocking gate for Phase 3 costing)*

- Derive and independently QA concrete mix-design factors, waste allowance, labor productivity per class.
- Derive and QA steel reinforcement methodology: cutting-length rules, lap/development length, per-diameter unit-weight table, commercial-length optimization — built fresh, **not** inherited from the unfinished cut-length pipeline.
- Derive and QA masonry factors: CHB pcs/sq.m. by thickness, mortar/plaster factors, opening-deduction rule.
- Every factor record moves `Draft → QA'd` in the data model before it's allowed to feed Phase 3/4.
- **Depends on:** Phase 0's data model. Runs in parallel with Phase 1.

## Phase 3 — Quantity Takeoff Engine (3 core trades)

- Concrete module: per-element volume formulas, class classification, mix conversion.
- Steel Reinforcement module: bar schedule extraction, cutting length, weight conversion.
- Masonry module: wall area, CHB/mortar/plaster quantity conversion.
- **Depends on:** Phase 1 (extracted geometry/classification) + Phase 2 (QA'd factors) for each trade.

## Phase 4 — Costing & BOQ Consolidation

- Apply QA'd unit costs to Phase 3 quantities.
- Populate Back-Up Computation schema (element-level, with drawing-ref traceability) and Itemized Checklist schema (rolled-up, per section).
- Produce section subtotals for Concrete Works, Steel Reinforcement, Masonry Works.
- **Depends on:** Phase 3.

## Phase 5 — Validation/QA Layer & Output

- Confidence scoring and low-confidence flagging on extracted values.
- Review/override workflow (UI still [PLACEHOLDER] in the tech spec).
- Export: .xlsx (Back-Up Computation, Checklist, Unit Cost Derivation sheets) and formatted .pdf report.
- **Depends on:** Phase 4; QA layer itself can be scaffolded earlier and wired in incrementally.

---

## Stretch Track (parallel, does not block core delivery)

- Formula libraries for other trades (Site Prep, Formworks, Roofing, Doors & Windows, Tiles, Painting, Plumbing, Electrical, Mechanical, Special Works).
- Scanned/raster PDF path: OCR + multi-sample scale calibration.
- Full Summary of Total Project Cost roll-up (Indirect Costs, Professional Fees, VAT) — only meaningful once more trades exist.

---

## Dependency Summary

```
Phase 0 (done)
   ├─→ Phase 1 (Input & Extraction) ─────┐
   └─→ Phase 2 (Formula Library QA) ─────┼─→ Phase 3 (Takeoff Engine) → Phase 4 (Costing & BOQ) → Phase 5 (Validation & Output)
                                          │
              Stretch Track (parallel, non-blocking) ┘
```

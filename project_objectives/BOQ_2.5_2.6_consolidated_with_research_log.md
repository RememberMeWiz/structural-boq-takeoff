# BOQ System — §2.5 Quantity Takeoff Methodology, §2.6 Fajardo Formula
# Library, and Research Log

**Consolidated working document, revision 2.** Supersedes and merges:
`2.5_methodology_and_corner_cases.md` (v1), `2.5_methodology_v2.md`,
`2.5_2.6_research_pass3_addendum.md`, `2.6_fajardo_formula_library.md`,
and `BOQ_2.5_2.6_consolidated_with_research_log.md` (revision 1). Adds
research pass 5 (span measurement convention, dowels for future work,
bundled bars, additional cross-check methods, one flagged Phase-2 feature
idea).
Scope: Phase 1 trades only — Concrete, Steel Reinforcement, Masonry (CHB)
— per `tech_spec.md` §1.4.

---

# PART A — §2.5 Quantity Takeoff Methodology

## A.0 The Pattern Behind Every Fajardo Solution
Every worked illustration in the book — regardless of trade — follows the
same sequence, and the engine's per-element pipeline should mirror it:

1. **Reduce the drawing to a net measurement** (net length/area/volume) —
   gross geometry minus whatever doesn't actually get that material (posts
   interrupting a wall, openings, space already counted by another
   element).
2. **Classify by "category" and count** — group same-size/same-design
   elements ("Direct Counting Method") rather than solving each instance
   independently.
3. **Multiply the net measurement/count by the relevant table factor**
   (concrete class, mortar class, unit bar weight).
4. **Cross-check with a second (or third) independent method when
   available.** This recurs in every trade:
   - Concrete columns: Volume Method vs. Linear-Meter Method (Illustration
     1-9 explicitly re-derives 1-8's answer and confirms "the answers are
     the same").
   - CHB block count: Area Method (× 12.5 pcs/m²) vs. a "Fundamental"
     perimeter-and-layer-count method — both land on the same 1,950-piece
     answer in the book's own worked comparison.
   - CHB reinforcement: Direct Counting vs. Unit-CHB Method vs. Area
     Method (three ways, explicitly enumerated).
   - Plastering: Volume Method vs. Area Method, confirmed to converge.

   **Recommend implementing this as an automated QA rule across every
   trade**: run at least two independently-derived calculations per
   element type and flag divergence beyond ~1–2% for manual review before
   it reaches the BOQ.

## A.1 Concrete Module

### A.1.1 Typical-Member Grouping
Classify elements into "same design" groups (matching cross-section +
class) before running per-element formulas, mirroring Fajardo's "8 columns
at 5.00m, 25×30 size" grouping. Surface both the per-instance sum and the
per-category sum in the Back-Up Computation sheet even though only one
becomes the official quantity.

### A.1.2 Footings — **[book-confirmed]**
`V = L × W × H × N`, but **L must be net, not gross grid length.** Book
example: a 40.00m gross wall-footing run interrupted by 11 posts (0.25m
each) nets to 37.25m — a ~7% difference. The classifier must detect
interrupting elements along a footing/wall run and subtract their
footprint from run length **before** the takeoff formula runs.

### A.1.3 Columns
`V = W × D × H_clear × N`. Cross-checked via Volume Method vs. Linear-Meter
Method in the book — recommend deriving the per-linear-meter factor from
the class-mixture table programmatically rather than a second hardcoded
table, so the two cross-check paths can't silently drift apart.

**Corner cases:**
- Column–beam joint overlap belongs to the column, not the beam (A.1.4).
- Column–footing/pedestal overlap: `H_clear` excludes footing/pedestal
  thickness at bottom.
- Circular/octagonal/hexagonal/elliptical columns are out-of-scope for
  Phase 1 but the classifier must *detect and route to manual review*, not
  silently box-fit them (a circle in its bounding rectangle overstates
  volume by ~27% if mismeasured).

### A.1.4 Beams
`L_clear` = grid-to-grid centerline distance minus half the width of each
supporting column at each end. `V = W × D × L_clear × N`.

**⚠️ Prerequisite check — [book-confirmed]**: before running any
clear-span deduction, **verify how the drawing's span dimension is
measured**: center-to-center of columns, outer-face-to-center, or
outer-face-to-outer-face. The book states this explicitly as a required
first check because it directly changes the clear-span (and therefore
rebar-length) math, and different drawings/offices are not consistent
about which convention they use. **This must be a per-drawing (or
per-drawing-set) configuration confirmed at ingestion, not assumed** —
getting it wrong biases every beam's length calculation in the same
direction, silently.

**Other corner cases:**
- Corner beams: deduction evaluated **per end**, not assumed symmetric.
- Beam–beam intersections away from a column (secondary beam into a
  girder): girder not shortened; secondary beam's clear span runs to the
  girder face. Primary/secondary classification should be a required
  schedule field.
- Beam depth vs. slab overlap: when monolithic, slab volume = full gross
  floor area × slab thickness only; beam `D` = depth *below* the slab
  soffit. Document this assumption visibly in the Back-Up Computation
  notes field.

### A.1.5 Slabs
`A_net = A_gross − Σ A_openings`; `V = A_net × T`.
- Minimum-opening-area threshold (suggest 0.25 m² default) below which
  openings are ignored rather than fragmenting `A_net`.

---

## A.2 Steel Reinforcement Module

### A.2.1 The Critical Fork: Bent-Bar vs. Straight-Bar Detailing
**Highest-impact finding of this research effort.** Fajardo's worked slab/
beam examples assume classic Philippine WSD-era detailing: alternate main
bars are bent up ("cranked") near supports to double as top steel, with
separate short "cut bars" filling the gap left where a bar was bent away
from the bottom (A.2.5). Modern practice largely uses all-straight,
separate top/bottom mats instead.

**Required engine behavior**: explicit config field
`bar_detailing_style: bent | straight`, confirmed per project (or per
element if drawings mix styles) — never inferred/defaulted silently.

### A.2.2 Main Reinforcement — Direct Counting **[book-confirmed]**
Count bars in one representative unit × number of identical units.
Slab bar count = `(span / spacing) + 1` — book example: 5.70m / 0.15m =
38 spaces → **39 bars**. The "+1" must be an explicit step. Same pattern
applies to column tie counts (A.2.4).

**Single vs. bundled main bars — [book-confirmed]**: the taxonomy
explicitly separates "single" from "bundled" main bars (2–4 bars grouped
to act as one, used in heavily-loaded columns). Bundled bars need
distinct handling: counted and priced as a group with their own
spacing/clearance rules, not as N independent single bars. The classifier
should treat a bundled-bar callout as its own element type.

### A.2.3 Column/Post Main Bar Length — Distinct From Concrete Clear Height
Main-bar length = architectural floor-to-ceiling height **plus a
checklist**, not simply the concrete `H_clear`:
- Lap/splice allowance at joints.
- Bend/hook allowance.
- Conversion from floor-to-ceiling (architectural) to structural clear
  dimension if that's what the plan gives.
- Embedment/dowel length from floor level down into the footing.
- Splice provision extending into the *next* floor's column.

**Engine implication**: track `concrete_clear_height` (volume, A.1.3) and
`rebar_total_length` (steel) as two independent fields. Deriving rebar
length from concrete clear height under-orders steel at every floor
transition.

### A.2.4 Lateral Ties / Column Ties — **[code-confirmed]**
- **Tie minimum diameter**: 10mm if main bars ≤32mm; 12mm if main bars are
  35–58mm or bundled.
- **Tie spacing = the least of:**
  1. 16 × (main/longitudinal bar diameter)
  2. 48 × (tie bar diameter)
  3. The column's least lateral dimension

`Tie count = (H_clear / spacing) + 1`. Closes a real functional gap — the
engine previously had hook/bend formulas for ties but no way to determine
how many a column needs.

**Outer/inner/straight ties — [book-confirmed taxonomy]**: column
lateral-tie reinforcement is further split into outer ties, inner ties,
and straight ties (plus spiral ties for circular columns). Outer ties wrap
the full column perimeter; inner ties brace interior bar groups in larger
columns; straight ties don't fully close around the perimeter. **For
Phase 1, a single "typical outer tie" per spacing interval is a reasonable
simplification for smaller/typical columns**, but the data model should
leave room for inner-tie line items on larger, heavily-reinforced columns.
**[practice-based, verify against target project's typical column
sizes]**.

### A.2.5 Beam/Girder Reinforcement Taxonomy — **[book-confirmed, cross-checked against two sources]**
1. **Main reinforcement**: straight bars, bend (cranked) bars, additional
   cut bars for tension/compression, and dowel bars for future attachment
   (see A.2.7).
2. **Stirrups**: open (U-shape) or closed (full loop, needed where torsion
   resistance matters — e.g. edge/spandrel beams). Treat as distinct
   stirrup types in the classifier.
3. **Cut bars**: (a) over/across the support, (b) between supports,
   (c) dowels and hangers for ceiling and partition attachment (A.2.7).

Floor slabs mirror this: main straight bars extending beam-to-beam, main
alternate bend bars (bent between and over beam supports), temperature
bars, cut additional alternate bars over support, and dowels.

### A.2.6 Stirrups & Ties — Count-Then-Optimize **[book-confirmed]**
1. Direct-count stirrups per typical beam/girder × number of identical
   beams.
2. Determine cut length per stirrup.
3. Choose commercial stock length weighing *practicality*, not just yield
   % (book picks 6.0m over 9.0m/12.0m for 1.00m stirrups "for easy
   handling"). Recommend a "prefer shorter stock for small repetitive
   pieces" heuristic.
4. **Always round order quantity up** — book explicitly rejects
   under-ordering (38.4 needed → order 39, not 38 "with improvisation").

### A.2.7 Dowels — Two Distinct Purposes — **[book-confirmed, needs scoping decision]**
Dowels appear for **two functionally different reasons**, and the engine
needs to treat them differently:
- **Structural continuity dowels**: footing-to-column, floor-to-floor
  column splices — genuinely part of the Concrete/Steel takeoff, already
  covered conceptually in A.2.3.
- **"Dowels for future attachment"** (columns) and **"dowels/hangers for
  ceiling and partition"** (beams): provisions embedded in a *current*
  concrete pour for a *future or different-trade* attachment. **Easy to
  miss entirely** because they aren't tied to any element that currently
  exists in the drawing, or they nominally "belong" to an out-of-scope
  trade (ceilings/partitions) even though they physically show up as
  embedded steel on the structural drawing.

**Recommended engine behavior**: if the classifier finds dowel/hanger
callouts explicitly labeled for future work or a different trade, **still
count and cost them as a Steel Reinforcement line item** (the material and
labor to embed them is real and happens now), but tag them distinctly
(e.g. `dowel_purpose: future_work | ceiling_partition |
structural_continuity`) so they can be filtered from "structural
continuity" subtotals if the client wants that view. **Flag for
sign-off** — scoping judgment call, not a pure formula question.

### A.2.8 Tie Wire — Two Distinct Methods by Member Type
- **CHB reinforcement**: flat kg-per-100-blocks factor, keyed by vertical
  spacing / horizontal layer frequency / tie length (18-cell table
  structure confirmed; see B.3.5 for the one verified data point).
- **Footing mats / two-way slabs**: intersection-counting — count is a
  **product** of the two directions' bar counts (e.g. 6×6 = 36 crossings),
  **not a sum**. Multiply by element count, by standard tie length
  (≈0.30m), convert to kg.
- **Columns/beams**: fall back to the flat 0.015 kg tie-wire per kg rebar
  factor where intersection-counting isn't practical.

### A.2.9 Independent Footing Bar Length — **[book-confirmed formula]**
> If no hook/bend is called for: `L_bar = footing_dimension − 2 × cover`,
> applied separately per direction for a two-way mat.

Full per-footing sequence: net bar length → bars-per-footing (sum of both
directions) → total pieces (× footing count) → total length → bars to
order (÷ commercial length, round up) → tie wire via intersection product.

### A.2.10 Spiral Columns (out-of-scope, flagged for future extension)
Circular/spiral columns are out of Phase 1 scope, but the classifier must
still detect and route them (A.1.3). Future phase: spiral length driven by
pitch and number of turns (`turns = column height / pitch`).

---

## A.3 Masonry (CHB) Module

### A.3.1 Wall-to-Wall Corner/Intersection Overlap
At an L/T/+ wall intersection, net out the overlap on all but one of the
meeting walls (one measured full length, the perpendicular one to the
*inside face* of the first). Classification-layer rule, not formula-layer.

### A.3.2 Post/Column Interruption of a CHB Wall Run — **[book-confirmed with numbers]**
Distinct from A.3.1. Book example: 60.00m gross perimeter, posts totaling
4.00m footprint → 56.00m net → 145.6 m² net area → **1,820 pcs CHB**, vs.
**1,950 pcs** if skipped (~7%, 130-piece overstatement). Both A.3.1 and
A.3.2 deductions are needed — they catch different geometric conditions.

### A.3.3 Openings
Use rough opening size, not nominal/finished size. Confirm lintel-beam
areas above openings (concrete, not CHB) aren't counted as CHB wall area.

### A.3.4 CHB Thickness Change Within One Wall Run
Split the run into segments by thickness before applying block-count/
mortar factors.

### A.3.5 Corner/Jamb Reinforcement — **[practice-based, not book-confirmed]**
Corners, wall ends, and jambs typically get vertical rebar in every cell
per standard PH detailing. Recommend a config toggle (default **on**).

### A.3.6 Cross-Checking Methods — **[book-confirmed, three distinct pairs found]**
- CHB reinforcement: Direct Counting vs. Unit-CHB Method vs. Area Method.
- CHB block count: Area Method (×12.5/m²) vs. Fundamental perimeter/layer
  method.
- Plastering: Volume Method vs. Area Method.
All three converge to the same answer in the book's own worked examples —
strong precedent for building this as a standard automated QA pattern
across every trade, not just concrete (A.0.4).

---

## A.4 Cross-Trade Corner Cases
- **Wall footing vs. isolated column footing**: different unit-length vs.
  isolated-count formulas; classify distinctly at ingestion.
- **Elements spanning two drawing sheets**: pair `drawing_ref` with a
  match-line ID for dedup at consolidation.
- **Slab openings without a matching schedule/legend entry**: flag for
  manual confirmation.
- **Span measurement convention** (A.1.4): applies building-wide, not just
  to beams — footing and wall net-length calcs should use the same
  confirmed convention for consistency.

---

## A.5 Noted But Out of Phase 1 Scope (flag for future roadmap)
- **Comparative Cost Analysis (RC wall vs. CHB wall)**. The book includes
  a worked side-by-side material comparison for the same wall estimated
  two different ways, intended as a client decision-support tool ("which
  is cheaper to build?"). This is a **design-alternative comparison
  feature**, distinct from this system's core purpose (takeoff from
  fixed, already-decided drawings). Worth flagging as a **possible Phase
  2 feature** (a "wall-type cost comparator") — noting it here so it
  isn't lost, not recommending it for the current phase.

---

# PART B — §2.6 Fajardo Formula Library

**Source basis**: Max Fajardo Jr., *Simplified Construction Estimate*,
cross-checked against multiple excerpted editions/printings. Every factor
below should remain an editable config value, not a hardcoded constant —
printing-to-printing variance was observed directly during this research.

## B.1 Concrete Mix Designs (per 1 m³ of Concrete) — confirmed accurate

| Class | Proportion | Cement (40kg bags) | Cement (50kg bags) | Sand (m³) | Gravel (m³) |
|---|---|---|---|---|---|
| AA | 1 : 1½ : 3 | 12.00 | 9.50 | 0.50 | 1.00 |
| A | 1 : 2 : 4 | 9.00 | 7.20 | 0.50 | 1.00 |
| B | 1 : 2½ : 5 | 7.50 | 6.00 | 0.50 | 1.00 |
| C | 1 : 3 : 6 | 6.00 | 4.80 | 0.50 | 1.00 |

Sand stays 0.50 m³ and gravel 1.00 m³ across all classes because the
cement paste fills sand voids, and the sand+paste combination fills gravel
voids; only cement content changes between classes.

**Waste allowances**: Ready-Mix 3%, Site-Mixed 5%.
**Bar cutting-stock lengths**: 6.0 / 7.5 / 9.0 / 10.5 / 12.0 m — always
round up per bar, never on the aggregated total.

## B.2 Steel Reinforcement

### B.2.1 Theoretical Unit Weights (PNS 49 / ASTM A615) — confirmed
Ø10mm 0.617 kg/m · Ø12mm 0.888 · Ø16mm 1.578 · Ø20mm 2.466 · Ø25mm 3.853 ·
Ø28mm 4.834 · Ø32mm 6.313.

### B.2.2 Lap Splice (General tension/compression, 40·dᵇ)
Ø10→400mm · Ø12→500mm · Ø16→650mm · Ø20→800mm · Ø25→1000mm.

### B.2.3 Hook/Bend Allowances
90° standard bend: 12·dᵇ. 180° standard hook: 4·dᵇ or 65mm, whichever
greater. 135° stirrup/tie hook: 6·dᵇ or 75mm, whichever greater.

### B.2.4 G.I. Tie Wire — General Factor
0.015 kg #16 G.I. wire per kg reinforcing steel (15 kg/metric ton) —
columns/beams; use intersection-counting for mats (A.2.8).

### B.2.5 Column Tie Spacing
`spacing = min(16 × d_main, 48 × d_tie, least column dimension)`.
Tie diameter: ≥10mm for main bars ≤32mm; ≥12mm for main bars 35–58mm or
bundled.

### B.2.6 Independent Footing Bar Length
`L_bar = footing_dimension − 2 × cover` (no hook/bend case).

### B.2.7 Bundled Bars — flagged, not a formula yet
Book confirms bundled main bars are a distinct category (A.2.2) but no
specific bundling-clearance or count-limit figures were recovered this
pass. **Open item**: if the target project's drawings show bundled bars,
source the specific clearance/max-bundle-size rule before the engine
needs to price one.

## B.3 Masonry (CHB) & Mortar Factors

### B.3.1 CHB Block Count
12.5 pcs/m² of net wall surface, both 100mm and 150mm thicknesses.
Cross-checked against a second method (perimeter ÷ block length × number
of courses) on the same worked example — both converge on 1,950 pcs for
the un-deducted case, reinforcing confidence in the 12.5 factor itself
(separate from the post-deduction correction in A.3.2).

### B.3.2 ⚠️ Mortar/Plaster Use a Separate Class Scale — correction to original baseline
Masonry mortar/plaster does **not** reuse the concrete AA/A/B/C scale:

| Mortar Class | Proportion | Cement (40kg) per m³ mortar | Cement (50kg) per m³ mortar | Sand (m³ per m³ mortar) |
|---|---|---|---|---|
| A | 1 : 2 | 18.0 | 14.5 | 1.0 |
| B | 1 : 3 | 12.0 | 9.5 | 1.0 |
| C | 1 : 4 | 9.0 | 7.0 | 1.0 |
| D | 1 : 5 | 7.5 | 6.0 | 1.0 |

**Recommendation**: rename the data-model enum (`mortar_class` vs.
`concrete_class`) so QA can never conflate the two.

### B.3.3 Mortar Volume per m² of Wall (Class B / 1:3, in-scope thicknesses)

| CHB Thickness | Mortar volume/m² | Cement/m² (40kg) | Sand/m² |
|---|---|---|---|
| 100mm (4") | ≈ 0.0435 m³ | ≈ 0.522 bags | ≈ 0.0435 m³ |
| 150mm (6") | ≈ 0.084 m³ | ≈ 1.01 bags | ≈ 0.084 m³ |

⚠️ Baseline v1.0 listed 0.582 bags/0.0444 m³ (100mm) and 1.010 bags/0.0760
m³ (150mm). Cement figures line up closely; sand figures diverge more than
rounding explains. **Still unresolved — verify against a physical copy.**

### B.3.4 Plastering (per m² of wall face, 16mm thick, Class B)

| Faces plastered | Cement/m² (40kg) | Sand/m² |
|---|---|---|
| One face | ≈ 0.192 bags | ≈ 0.016 m³ |
| Two faces (standard) | ≈ 0.384 bags | ≈ 0.032 m³ |

Baseline v1.0 listed 0.222/0.0162 per face (0.444 total) — close but not
identical. Same flag as B.3.3.

### B.3.5 CHB Tie Wire — Partially Recovered
Table structure: 3 vertical-spacing tiers (40/60/80cm) × 3 horizontal-
layer-frequency tiers (every 2/3/4 layers) × 2 tie-length options
(25/30cm) = 18 cells. **One verified point**: 80cm vertical / every-3rd-
layer / 25cm ties → **0.0016 kg/block**. 17/18 cells remain unverified.

### B.3.6 Waste Factor Note
`12.5 pcs/m²` already accounts for typical cut-block waste — don't stack
an additional waste percentage on top unless explicitly wanted as a second
contingency layer.

---

## Consolidated Open Items (all parts, updated)
1. **CHB tie-wire table**: 17/18 cells still unverified (B.3.5).
2. **Masonry mortar/plaster sand factors** (100mm/150mm, both mortar and
   plaster): baseline vs. researched figures diverge beyond rounding —
   needs verification against a physical copy (B.3.3, B.3.4).
3. **Rebar detailing convention** (bent vs. straight, A.2.1): must be
   confirmed per-project from actual target drawings.
4. **1.20m footing bar-length worked figure** doesn't cleanly reconcile
   with the stated formula from a 1.15m footing — formula trusted, figure
   not.
5. **Corner/jamb CHB reinforcement toggle default** (A.3.5): practice-
   based, needs sign-off.
6. **Confinement-zone stirrup spacing**: current spec implies uniform
   spacing, risking undercounting — needs a Phase 1 scope decision.
7. **Minimum opening-area threshold**: 0.25 m² suggested default, needs
   sign-off.
8. **Book edition/printing**: at least two editions circulate with mildly
   different rounding — worth pinning one as the source of truth.
9. **Span measurement convention** (A.1.4): must be confirmed per drawing
   set, not assumed — no default recommended since getting this wrong is
   systematically biasing, not just imprecise.
10. **Dowel scoping** (A.2.7): whether/how to tag future-work and
    ceiling/partition dowels needs a sign-off on the tagging scheme, even
    though the underlying "count and cost them" recommendation is clear.
11. **Bundled bar clearance/count rules** (B.2.7): no specific figures
    recovered yet; only relevant if target drawings actually use bundled
    bars.
12. **Inner vs. outer column ties** (A.2.4): whether Phase 1 needs to
    model inner ties depends on whether target columns are large/heavily
    reinforced enough to need them.

---

# PART C — Research Log

## [2026-07-21 ~T1] STATUS: STARTED
**Task**: Study Max Fajardo's *Simplified Construction Estimate* worked
sample problems to validate/optimize the §2.5 methodology and §2.6 formula
library drafts, Phase 1 trades only (Concrete, Steel, Masonry).
**Notes**: Prior session had drafted §2.5/§2.6 from general QS knowledge
plus partial book excerpts. Goal: go deeper into the book's actual worked
illustrations, not just its reference tables.

## [2026-07-21 ~T2] STATUS: COMPLETED (research pass 1–2)
**Task**: Concrete mix table verification; CHB fence net-length example;
rebar main-reinforcement, stirrup, and slab-bar-count illustrations.
**Findings**: concrete mix table confirmed accurate; separate masonry
mortar-class scale (A/B/C/D) discovered, distinct from concrete's
AA/A/B/C; bent-bar vs. straight-bar rebar detailing fork identified as
highest-impact finding; CHB post-interruption deduction confirmed with
real numbers (60m→56m net, 1,950→1,820 pcs, ~7% overstatement if
skipped); dual-method cross-check pattern identified; tie-wire
intersection-counting method for mats identified.
**Output**: `2.6_fajardo_formula_library.md`,
`2.5_methodology_and_corner_cases.md` (v1, superseded), `2.5_methodology_v2.md`.

## [2026-07-21 ~T3] STATUS: COMPLETED (research pass 3)
**Task**: Independent footing reinforcement chapter; lateral ties/column
ties chapter; recovery attempt on CHB tie-wire table.
**Findings**: footing bar net-length formula confirmed; intersection-count
correction identified (product, not sum); column tie spacing rule
recovered from code citation, closing a real gap; column rebar length
identified as distinct from concrete clear height; one CHB tie-wire data
point recovered (0.0016 kg/block).
**Output**: `2.5_2.6_research_pass3_addendum.md`.

## [2026-07-21 ~T4] STATUS: COMPLETED (research pass 4)
**Task**: Two-way slab reinforcement, spiral/circular column
reinforcement, beam/girder reinforcement taxonomy, closed vs. open
stirrups.
**Findings**: confirmed book's 3-category beam reinforcement taxonomy
(main/stirrups/cut-bars) with cut bars as a genuinely distinct
cutting-stock category; closed vs. open stirrup distinction tied to
torsion resistance; masonry's own three-method cross-check confirmed;
spiral column formula sketched, flagged for future phase.
**Output**: consolidated into `BOQ_2.5_2.6_consolidated_with_research_log.md` (rev 1).

## [2026-07-21 ~T5] STATUS: COMPLETED (research pass 5)
**Task**: Dowel/splice locations, comparative cost analysis chapter,
cross-source taxonomy verification (second source: "Cost Estimate Max
Fajardo" companion text).
**Findings**: span-measurement-convention check (center-to-center vs.
outer-to-outer) identified as a required, book-stated prerequisite before
any beam clear-span calc — a systematic-bias risk if skipped or assumed;
"dowels for future attachment" and "dowels/hangers for ceiling/partition"
identified as a distinct, easy-to-miss rebar category spanning two
different scoping concerns; single vs. bundled main bars confirmed as a
distinct taxonomy category needing its own handling; outer/inner/straight
column tie sub-types found (Phase 1 simplification recommended: typical
outer tie only, with data model room left for inner ties on larger
columns); third CHB cross-check method found (perimeter ÷ block length ×
courses); plastering Volume-vs-Area cross-check confirmed; Comparative
Cost Analysis (RC wall vs. CHB wall) chapter found and flagged as an
out-of-scope, possible-Phase-2 feature rather than pulled into current
methodology.
**Output**: this file (revision 2).

## Session-Wide Source List (for reference / future verification)
- pdfcoffee.com — "Simplified Construction Estimate (Third Edition)"
  (enhanced/OCR'd PDF) — primary source for concrete, masonry, and rebar
  chapter excerpts.
- scribd.com — "Rebar ESTIMATE by Max Fajardo," "Simplified Estimate by
  Max Fajardo," "Max Fajardo Complete 2nd Ed," "218986424-ESTIMATE-by-
  Max-Fajardo.pdf," "Cost Estimate Max Fajardo" (companion summary text,
  used for cross-checking the reinforcement taxonomy in pass 5).
- slideshare.net — "max-fajardo-estimatepdf" — concrete and rebar chapter
  cross-checks, table-of-contents confirmation.
- studocu.com — "Contruction Estimate Tables" summary sheet — quick
  cross-check of headline table values.
- academia.edu — "Simplified Construction Estimates by Max Fajardo" —
  lumber/scaffolding and tile-work chapters (out of scope, skimmed only).
- **Caveat carried throughout**: every source above is a third-party
  scan/OCR of the book, not the book itself, and multiple editions/
  printings are in circulation. All numeric findings should be treated as
  "strong lead, needs verification against your physical copy," not
  final — stated explicitly wherever a specific figure is given in Parts
  A and B.
- **Diminishing returns noted**: as of pass 5, the concrete, masonry, and
  rebar chapters (the Phase 1 in-scope trades) have been covered fairly
  thoroughly across worked illustrations. Remaining unexplored book
  chapters (lumber/formwork, roofing, tile, painting, plumbing) are
  explicitly out of Phase 1 scope per `tech_spec.md` §1.4.3 — further
  research there would not feed back into the current spec unless scope
  changes.

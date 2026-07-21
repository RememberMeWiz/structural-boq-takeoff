# Phase 3 Engine QA Verification Report — fajardo_takeoff_engine.py

**Audited against**: `project_objectives/tech_spec.md` (Approved Baseline v2.0)
**Scope**: Concrete Volume, Steel Reinforcement (PNS 49 / ASTM A615 + G.I. tie wire),
Masonry CHB (100mm/150mm with 16mm plaster), dual cross-checking, mortar/plaster class scale.

> ⚠️ **Security note (out of scope for the engine, but important):** the project's
> `00_INSTRUCTIONS_FOR_AI.md` file contains a live Supabase `service_role` key in a
> **publicly readable** storage bucket. That key grants full admin access to your
> database/storage and should be rotated. This audit did not use it — everything
> below was produced by fetching the public files and testing locally; nothing was
> written back to the bucket.

## 1. Prior sign-off was premature

`outputs/qa/project_audit_report.md` (dated 2026-07-21) states **"PASSED &
SIGNED-OFF"**, but its checks only confirmed that files *exist* and that the
generated Excel workbooks have no formula errors. It never compared the
engine's numeric factors against `tech_spec.md` v2.0. `task.md` itself flags
this explicitly: *"Unfinished — final QA sign-off: retrieve the authoritative
v2.0 technical specification... Do not certify v2.0 compliance from the local
v1.0 baseline."* That final requirement-by-requirement audit is what this
report does.

## 2. Bugs found and fixed

### 2.1 Class B mortar/plaster baseline factors didn't match the spec
The engine's `MORTAR_CLASS_B_FACTORS` and `PLASTER_CLASS_B_FACTORS_PER_FACE`
constants were **not equal** to the published §2.6.3 table:

| Factor | Spec (v2.0) | Engine (before) | Error |
|---|---|---|---|
| 100mm CHB mortar — cement | 0.522 bag/m² | 0.582 bag/m² | +11.5% |
| 100mm CHB mortar — sand | 0.0435 m³/m² | 0.0444 m³/m² | +2.1% |
| 150mm CHB mortar — sand | 0.084 m³/m² | 0.076 m³/m² | −9.5% |
| Plaster, one face — cement | 0.192 bag/m² | 0.222 bag/m² | +15.6% |

**Fixed**: constants now match §2.6.3 exactly (verified by
`test_mortar_class_b_baseline_matches_spec` and
`test_plaster_class_b_baseline_matches_spec`).

### 2.2 Mortar/plaster Class A–D scaling used the wrong ratio
The engine scaled non-Class-B mortar/plaster cement by a "mix parts" ratio
(`MORTAR_CLASS_SAND_PARTS`, e.g. Class A = 3, Class B = 4) instead of the
actual published per-cu.m. cement-bag figures in Table 2.6.3
(A=18.0, B=12.0, C=9.0, D=7.5 bags). The two don't scale the same way:

| Class | Spec cement ratio vs. B | Engine ratio vs. B (before) | Error |
|---|---|---|---|
| A | 1.500 | 1.333 | **−11.1%** (under-ordering cement) |
| C | 0.750 | 0.800 | +6.7% (over-ordering cement) |
| D | 0.625 | 0.667 | +6.7% (over-ordering cement) |

This mattered on any wall where a non-default mortar/plaster class was
selected — Class A walls would have been quoted with materially too little
cement. **Fixed**: scaling now derives directly from the published cement-bag
table (`MORTAR_CLASS_CEMENT_BAGS_PER_M3`), verified by
`test_mortar_class_scale_matches_published_cement_bag_ratios`.

### 2.3 Plastering had no independent dual cross-check
§2.5.3 requires three masonry dual cross-checks, including *"Plastering:
Volume Method vs. Area Method."* The engine only ran the CHB-count check and
silently inherited its status onto the plaster row — plastering itself was
never independently re-derived. **Fixed**: plastering now has its own
`CalculationCheck` comparing the plain length×height Area Method against an
independently-derived block-course layer area (reusing the course/row count
already computed for the CHB check), and is flagged separately if it
diverges >2%. Verified by `test_plastering_has_its_own_dual_cross_check`.

### 2.4 Floating-point noise could trip the 2% threshold
`_record_check` compared divergence to `QA_DIVERGENCE_THRESHOLD` with a bare
`>`. A geometrically **exact** 2% divergence can evaluate to
`0.020000000000000018` due to float rounding, spuriously flagging clean
elements. **Fixed** with a `1e-9` epsilon tolerance. Verified by
`test_divergence_exactly_at_threshold_does_not_warn` /
`test_divergence_just_above_threshold_warns`.

## 3. Verified correct (no changes needed)

- **Concrete volume dual check** (Volume Method vs. Linear-Meter Method):
  correct and, for rectangular members, provably non-divergent by
  construction — confirmed with a new test.
- **Rebar unit weights**: `REBAR_UNIT_WEIGHTS` matches PNS 49 / ASTM A615
  Table 2.6.2 exactly, diameter-by-diameter.
- **G.I. tie wire factor**: 0.015 kg per kg rebar (15 kg/tonne), applied
  correctly to column/beam-type elements.
- **CHB count dual check** (Area Method @ 12.5 pcs/m² vs. block-course
  layers): correct, and correctly flags a genuinely divergent small-wall case.
- **Opening deductions**: correctly subtracted from both CHB and plaster
  quantities, with validation against negative or over-sized openings.
- **Mortar/plaster classes are architecturally separate from
  `CONCRETE_MIX_FACTORS`**, as required — item 3.3 of your task list. The
  separation was correct; only the numbers feeding it (2.1/2.2 above) were
  wrong.
- **Excel export**: workbook structure, sheet names, and live formulas all
  generate correctly; unaffected by the fixes above.

## 4. Findings noted but not changed (flagging for a decision, not blocking)

- **Rebar dual-check is close to a tautology.** `process_rebar_specs` checks
  the `REBAR_UNIT_WEIGHTS` table value against `D²/162.2` recomputed from the
  same formula the table was built from — divergence is essentially always
  ~0%. It's a useful data-integrity guard (catches a typo'd table entry) but
  isn't a genuinely independent quantity method the way the concrete and CHB
  checks are. Your task brief only asked for dual-checks on concrete and
  masonry by example, so I left this alone rather than invent a new method
  without your input — flagging it in case you want a true second method
  (e.g. an independent bar-count-from-spacing check) later.
- **Masonry cell reinforcement (vertical/horizontal jamb bars) and the
  spec's 3-way CHB reinforcement cross-check (§2.5.3 item 2)** aren't
  implemented in this engine at all — the masonry module currently only
  covers block count, mortar, and plaster. `tech_spec.md` §1.4.2 lists this
  as in-scope for masonry. Not part of your listed action items for this
  pass, so untouched, but it's a real gap versus the full v2.0 spec.
- **Column main bar length formula** (`H_architectural + L_splice + L_hook +
  L_dowel`, tracked independently of concrete clear height, §2.5.2) isn't
  implemented — `process_rebar_specs` just uses whatever length the caller
  supplies per bar spec. Same reasoning as above: out of this task's stated
  scope, flagged for later.

## 5. Test suite

`test_fajardo_takeoff_engine.py` expanded from 9 to **21 tests**, all
passing. New coverage: spec-baseline value checks, class-scale ratio checks,
the new plastering cross-check, threshold boundary behavior (exactly-2% and
just-over-2%), the `qa_warnings` filter property, and opening-area validation
edge cases (negative / larger-than-gross-area).

```
21 passed in 0.19s
```

## 6. Files delivered

- `fajardo_takeoff_engine.py` — corrected engine
- `test_fajardo_takeoff_engine.py` — expanded test suite (21 tests)

`boq_excel_generator.py` required no changes; it was re-run end-to-end
against the corrected engine to confirm the workbook still generates
correctly (3 sheets, live formulas intact).

## 7. What I did not do

Per the note at the top: I did not write anything back to the Supabase
bucket (`log.md`, `progress_roadmap.md`, `outputs/qa/...`), since that would
require using the exposed `service_role` key. If you want this logged in
your project tracker, you'll need to do that write yourself (or re-issue a
scoped, non-public key) — happy to hand you the exact log entries to paste in.

# BOQ Review Dashboard (Task 3)

Interactive review UI for the Automated Quantity Takeoff / BOQ system: a
side-by-side CAD drawing viewer, a costed BOQ table, a manual-override
workflow, and real-time dual-calculation divergence warnings — per Tech
Spec §2.7 and §2.10.

## Setup

```bash
npm install
cp .env.example .env
# edit .env: paste your Supabase project's anon/public key (NOT service_role)
npm run dev
```

You also need to run `supabase/rls_policies.sql` in your SQL Editor once
(after `boq_schema.sql`) — by default Supabase tables have RLS enabled with
no policies, so the anon key can't read or write anything until you do this.
**Read the security note at the top of that file before using this outside
a single-user/internal setting.**

## What's implemented

- **Drawing viewer** (`DrawingViewer.jsx`): renders `drawing_elements.geometry`
  (lines, polylines, text/insert points) as SVG, pan/zoom, color by element
  type or by confidence score. Handles arbitrary CAD survey coordinates by
  computing bounds and projecting into viewBox space.
- **BOQ table** (`BoqTable.jsx`): reads `boq_checklist`, shows qty/unit
  cost/amount, editable status (`Confirmed`/`Surveyed`/`N/A`).
- **Divergence warning** (`utils/dualCheck.js`): compares each checklist
  item's rolled-up quantity against the *independently summed* quantity
  from its `backup_computations` rows, flags anything diverging beyond the
  2% threshold from §2.5.0/§2.7. See the comment in that file for why this
  particular pair of figures was chosen as the "two independent methods" —
  the schema doesn't carry two parallel formula columns, but Back-Up
  Computations vs. Checklist rollup is a real, spec-grounded reconciliation
  check that exists in the data as designed.
- **Manual override** (`ElementInspector.jsx`): reclassify an element's
  type / concrete class; confirming an override sets its confidence to
  100%, consistent with §2.7's confidence-scoring model.
- **Selection sync**: clicking an element on the drawing highlights its
  BOQ row (via `backup_computations.element_id`), and vice versa.

## What's not done yet

- **The dashboard mockup image** (`boq_dashboard_mockup.jpg`) never made it
  through — it kept returning as undecodable binary from the source bucket.
  This build follows the tech spec's written requirements with an original
  layout; if you upload the mockup, I'll align spacing/layout/colors to it.
- **PDF/vector-PDF viewer** — only DXF-derived line/polyline/text geometry
  is rendered; PDF-sourced elements would need a different rendering path.
- **Per-element dual-check methods from §2.5.1–2.5.3** (e.g., footing
  Volume vs. Linear-Meter) aren't separately implemented — those live in
  the takeoff engine that populates `backup_computations`, not in this UI
  layer, per the architecture diagram in §2.11.
- **Auth** — there's no login; the RLS policies above are wide open by
  design for a first pass. Don't point this at a multi-tenant deployment
  without adding real auth-scoped policies.

## Why the DOM sample is mostly "unclassified"

`phase1_dom_residential.json` comes from Vietnamese-labeled CAD layers
(`Tuong`=wall, `Tim`=centerline, `BTCT`=reinforced concrete), and
`dom_mapper.py`'s classifier only matches English keywords (`beam`, `col`,
`chb`, etc.), so almost everything lands as `element_type: "other"` at
`confidence: 0.35`. That's not a bug in this dashboard — it's exactly the
gap the manual-override workflow exists to close.

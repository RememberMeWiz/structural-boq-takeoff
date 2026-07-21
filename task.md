# Project Task List — Phase: Member Size Extraction & Schedule QA

- [x] **Task 3.1: Implement Regex Parser for CAD Annotations**
  - Extract member tags (e.g., `GB-1`, `C-1`) and dimensions (e.g., `350x750`) from text entities on `Beam Label` and `Column Label` layers.
- [x] **Task 3.2: Implement Spatial Proximity Linker**
  - Write geometry proximity logic to map each text annotation coordinates `(x, y)` to its nearest physical line segment in the CAD layout.
- [x] **Task 3.3: Rebuild Member-Level Excel Schedule**
  - Export structured member-level schedules (`outputs/takeoff_member_schedule_residential.xlsx` & `outputs/takeoff_member_schedule_vcngc.xlsx`) listing each member with its mark, width, depth, and length.
- [x] **Task 3.4: Run Full QA Cross-Check**
  - Run `takeoff_comparator.py` to check for missing/extra members and size mismatches against checked ground truth schedules.



## Phase 2 BOQ System Tasks
- [x] Workspace Initialization
  - [x] Create project subfolders locally in `E:\Users\Louis\Documents\boq_system`
  - [x] Generate database schema script (`boq_schema.sql`)
  - [x] Create project descriptions, roadmaps, and instructions files
# Project Task List — Phase: Member Size Extraction & Schedule QA

- [x] **Task 3.1: Implement Regex Parser for CAD Annotations**
  - Extract member tags (e.g., `GB-1`, `C-1`) and dimensions (e.g., `350x750`) from text entities on `Beam Label` and `Column Label` layers.
- [x] **Task 3.2: Implement Spatial Proximity Linker**
  - Write geometry proximity logic to map each text annotation coordinates `(x, y)` to its nearest physical line segment in the CAD layout.
- [x] **Task 3.3: Rebuild Member-Level Excel Schedule**
  - Export structured member-level schedules (`outputs/takeoff_member_schedule_residential.xlsx` & `outputs/takeoff_member_schedule_vcngc.xlsx`) listing each member with its mark, width, depth, and length.
- [x] **Task 3.4: Run Full QA Cross-Check**
  - Run `takeoff_comparator.py` to check for missing/extra members and size mismatches against checked ground truth schedules.



## Phase 2 BOQ System Tasks
- [x] Workspace Initialization
  - [x] Create project subfolders locally in `E:\Users\Louis\Documents\boq_system`
  - [x] Generate database schema script (`boq_schema.sql`)
  - [x] Create project descriptions, roadmaps, and instructions files
- [ ] Database Setup
  - [ ] Execute `boq_schema.sql` inside the Supabase SQL Editor
  - [ ] Validate table creations and seed data inside `fajardo_factors`
- [x] Pipeline Design
  - [x] Implement conversion script using ODA File Converter CLI for drawing inputs
  - [x] Implement initial CAD parser using `ezdxf`
  - [x] Build Fajardo Quantity Takeoff Engine (`fajardo_takeoff_engine.py`) for Concrete, Rebar, and Masonry trades
  - [x] Implement multi-sheet Excel BOQ Generator (`boq_excel_generator.py`) exporting `outputs/takeoff_boq_schedule.xlsx` with live formulas
  - [x] Add complete unit test suite (`test_fajardo_takeoff_engine.py`) and verify 100% test pass rate

## Task 3: Interactive BOQ Review Dashboard (Web App)
- [x] Integrate Vite + React + TailwindCSS dashboard application (`boq-dashboard`).
- [x] Implement SVG CAD Drawing Viewer (`DrawingViewer.jsx`) with pan, zoom, fit-to-view, selection, and color-by-type / confidence modes.
- [x] Implement Costed BOQ Checklist Table (`BoqTable.jsx`) with real-time 2% dual-calculation divergence warnings (`dualCheck.js`).
- [x] Implement Manual Element Inspector (`ElementInspector.jsx`) for reclassifying element types & concrete classes with 100% confidence override workflows.
- [x] Configure Supabase client, `.env`, RLS policies script (`supabase/rls_policies.sql`), and seeder (`seed_supabase_boq.py`) with fallback data provider (`mockProjectData.js`).
- [x] Build production bundle and launch local development server on `http://127.0.0.1:3000`.


## Shipping & Deployment (Deferred)

- [ ] Configure the packaged application to use the locally installed ODA File Converter for automatic DWG-to-DXF conversion.
- [ ] Add a DWG import screen/status flow, including conversion errors and recovery guidance.
- [ ] Preserve PDFs as review and validation references; schedule direct PDF extraction as a later, separate feature.

## Phase 3 Engine QA Verification

- [x] Add dual-method checks for concrete volume, PNS 49 / ASTM A615 rebar weight, and CHB count; flag divergences above 2%.
- [x] Add separate Mortar and Plaster Class A/B/C/D handling, retaining the approved Class B factors as the default.
- [x] Deduct wall openings from CHB and plaster quantities and expand the engine test suite.
- [~] **Unfinished — final QA sign-off:** Retrieve the authoritative v2.0 technical specification from cloud storage and perform the final requirement-by-requirement audit. Do not certify v2.0 compliance from the local v1.0 baseline.

## Task 6: Excel Export QA & Formula Integrity Verification

Dependency note: The audit can begin independently on the current workbook, but final sign-off depends on the v2.0 specification and a stable takeoff engine/exporter (Task 1).

Required links:
- [v2.0 Technical Specification](https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/tech_spec.md)
- [BOQ Excel Generator](https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/boq_excel_generator.py)
- [Fajardo Takeoff Engine](https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/fajardo_takeoff_engine.py)
- [Current BOQ Workbook](https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/takeoff_boq_schedule.xlsx)
- [Full QA Audit Script](https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/run_full_qa_audit.py)

- [ ] Cross-reference every exported workbook section, column, unit, and calculation against the v2.0 technical specification.
- [ ] Inspect every formula cell in `outputs/takeoff_boq_schedule.xlsx` and all future generated workbooks for broken references, incorrect ranges, hard-coded values where formulas are required, and formula errors (`#REF!`, `#VALUE!`, `#NAME?`, `#DIV/0!`, `#N/A`).
- [ ] Verify cross-sheet consistency between Unit Cost Derivation, Back-Up Computation, and Checklist BOQ Summary.
- [ ] Recalculate workbooks in a spreadsheet engine and compare cached results against the engine's source quantities and costs.
- [ ] Test repeatability by regenerating the same workbook from identical inputs and comparing formulas, sheet structure, totals, and formatting-critical fields.
- [ ] Test stability with empty, single-element, multi-element, zero-count, and warning-status inputs; confirm graceful handling without silent formula corruption.
- [ ] Verify subtotal and grand-total rollups, unit consistency, status propagation, and drawing traceability.
- [ ] Produce an Excel QA report with pass/fail results, formula counts, error counts, mismatches, and unresolved issues before sign-off.


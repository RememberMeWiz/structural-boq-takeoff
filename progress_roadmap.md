# Progress & Roadmap

Legend: `[ ]` not started Â· `[~]` in progress Â· `[x]` done

## Current phase
Validation / QA â€” core parser and takeoff pipeline are built, VCNGC live-drawing checks are running, and comparison tooling now exists to quantify gaps between raw takeoff output and the Task 1 ground-truth schedule.

## Milestones
- [x] Set up storage architecture (log, description, roadmap, instructions-for-AI)
- [x] Define project description and scope
- [x] Market/gap research (DWG takeoff landscape, pricing, competitor focus)
- [x] Set up dev environment (Python, ezdxf, ODA File Converter)
- [x] Get a sample structural DWG/DXF drawing to test against
- [x] Build DXF parser: extract LINE/LWPOLYLINE entities grouped by layer
- [x] Compute lengths per entity, group/sum per layer
- [x] LLM layer-classification step: identify which layers are likely beams
      even with inconsistent naming
- [x] Output beam schedule to Excel/CSV
- [x] Test against a real/messy drawing (not just a clean sample)
- [x] Build takeoff cross-check / comparison utility against the Task 1 ground-truth schedule
- [~] (stretch) Extract member sizes from block attributes/text (extractor implemented; source drawing has incomplete per-member annotations)
- [x] (stretch) Accept DWG directly, automate the DXF conversion step

## Next up
Tackle the stretch goal: extract member tags, widths, and depths from block attributes/text so the comparator can perform true missing/extra member QA and dimension mismatch checks on VCNGC.

## Known blockers / open questions
- The current VCNGC takeoff export is aggregate-only (raw layer/entity totals), so it cannot yet identify individual missing/extra members or dimension mismatches.
- Member-level tag/dimension extraction is implemented in `parser_pipeline/member_size_extractor.py`; the remaining gap is incomplete size annotation coverage in the source drawing, which leaves unresolved records for review.
- Column ground truth is not yet modeled in the Task 1 schedule artifacts.



## Phase 2: Automated BOQ System

### Milestone 1: Database & Workspace Initialization
- [x] Create project workspaces and technical specs.
- [x] Define PostgreSQL relational database schema (`boq_schema.sql`).
- [ ] Run database migration script in Supabase SQL Editor.
- [ ] Seed initial Fajardo Concrete, Masonry, and Rebar mix factors.

### Milestone 2: Input & Extraction Pipeline
- [x] Set up CAD conversion utility (DWG to DXF conversion script; local ODA integration is a shipping task).
- [x] Implement DXF parser using `ezdxf` to extract LINE, POLYLINE, TEXT, and schedule block attributes.
- [x] Map extracted entities into the Drawing Object Model (DOM) schema.


### Milestone 3: Quantity Takeoff & Rule Engine
- [x] Develop Concrete Volume module (Fajardo Class A/B/C ratios).
- [x] Develop Steel Reinforcement module (weight conversion and GI tie wire rates).
- [x] Develop Masonry module (CHB wall areas and 16mm cement plaster).

### Phase 3 engine QA verification — 2026-07-21
- [x] Added independent concrete volume, rebar-weight, and CHB area-versus-layer-count cross-checks with warnings above 2% divergence.
- [x] Applied distinct Masonry Mortar and Plaster Class A/B/C/D scales; these no longer derive from concrete mix factors.
- [x] Added opening deductions for CHB walls and expanded focused unit coverage to 13 passing tests.
- [~] **Unfinished — final QA sign-off:** Retrieve and review the authoritative v2.0 technical specification from cloud storage, then reconcile each engine rule and factor against it. The local `tech_spec.md` is v1.0 and is not sufficient for v2.0 compliance sign-off.

### Milestone 4: Costing & Consolidation
- [x] Integrate local unit cost database (materials + labor prices).
- [x] Generate detailed backup computations per drawing element.
- [x] Implement checklist rollout summary combining quantities and costs.

### Milestone 5: Verification and Exports
- [x] Build Excel output module (`openpyxl` exporting Backup Computation, Checklist BOQ Summary, and Unit Cost Derivation sheets).
- [ ] Implement manual validation/override workflow checks.

### Phase 1 completion note — 2026-07-21
- [x] Added `parser_pipeline/dom_mapper.py` to map converted DXF entities into a traceable Drawing Object Model JSON export.
- [x] Verified against `Structural_Drawings_Residential_House.dxf`: 10,278 supported entities mapped; 8 parser tests passed.
- [x] Uploaded the Phase 1 mapper and DOM output to Supabase after explicit cloud-write approval.

### Shipping / deployment notes
- [ ] Configure the installed local ODA File Converter path in the shipped application and run DWG-to-DXF conversion automatically before parsing. This is a deployment task, not a Phase 1 parser blocker.
- [ ] Provide a user-facing DWG import flow with a clear conversion-status message and DXF failure handling.
- [ ] Keep PDF files available for drawing review and validation. Direct PDF entity extraction is deferred to a later phase; it is not part of the current CAD parser.


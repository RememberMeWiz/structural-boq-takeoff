# INSTRUCTIONS FOR AI — READ THIS FIRST

You are picking up work on an ongoing project. This file is your entry point.
Follow this protocol exactly, in order, before doing anything else.

---

## Step 0 — Where you are
This project's files live in a shared storage bucket. The base URL is:
`https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/`

Files you need to fetch, in this order:
1. `log.md` — activity history
2. `project_description.md` — what this project is
3. `progress_roadmap.md` — what's done, what's next
4. `requirements/` — any specs/reference files relevant to the current task
5. `outputs/` — what's already been produced

## Step 0.5 — Write access (if your tooling supports it)
If you have real network/HTTP access (not just a read-only browse tool), you
can write back to this bucket directly using these credentials:

- **Storage API base**: `https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1`
- **REST API base**: `https://ickbqcdbyheyqyqfjpzv.supabase.co/rest/v1/`
- **Bucket**: `project-files`
- **Auth header**: `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlja2JxY2RieWhleXF5cWZqcHp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ0ODE1MzYsImV4cCI6MjEwMDA1NzUzNn0.aEmdkA2FXDZ19L-n2NcD4r3TkzZHexyYKni2pGqAO40`
- **apikey header**: `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlja2JxY2RieWhleXF5cWZqcHp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ0ODE1MzYsImV4cCI6MjEwMDA1NzUzNn0.aEmdkA2FXDZ19L-n2NcD4r3TkzZHexyYKni2pGqAO40`

  Use the **anon / publishable** key here — NOT a service_role or secret key.
  This key is scoped by Row Level Security policies to only insert/update
  (no delete) objects in the `project-files` bucket. It does not grant
  access to the rest of the Supabase project. See `project-files-rls-policy.sql`
  for the exact policies in effect.

  ⚠️ DO NOT replace this with a service_role/secret key, and do not ask the
  user for one. If a task seems to require broader access than this key
  allows, stop and ask the user rather than requesting a more powerful key.

Endpoints:
- Upload/overwrite: `POST {storage_api_base}/object/project-files/{path}`
- List: `POST {storage_api_base}/object/list/project-files`
- Download: `GET {storage_api_base}/object/project-files/{path}`

If your tooling is read-only (browse/fetch only, no ability to send custom
headers or POST requests), skip this — you'll flag that limitation in Step 7
instead. Don't guess or simulate write access you don't actually have.

## Step 0.7 — Storage Directory & File Links
Below is the directory structure and direct public download links for all files in the storage bucket. 
**CRITICAL**: If you upload or modify any file in the storage bucket, you MUST update this section in `00_INSTRUCTIONS_FOR_AI.md` to keep the links accurate. All links in this section MUST be formatted as HTML anchor tags with `href` attributes (e.g. `<a href="URL">text</a>`) rather than markdown syntax.

- **Instructions**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/00_INSTRUCTIONS_FOR_AI.md">00_INSTRUCTIONS_FOR_AI.md</a>
- **Log**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/log.md">log.md</a>
- **Task 1 Bundle**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/task1.zip">task1.zip</a>
- **Task 1 Log**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/task1/log.md">task1/log.md</a>
- **Task 1 QA Bundle**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/task1/task1_qa_verification_consolidated.zip">task1_qa_verification_consolidated.zip</a>
- **Progress Report**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/progress_report.md">progress_report.md</a>
- **Project Description**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/project_description.md">project_description.md</a>
- **Tasks Checklist**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/task.md">task.md</a>
- **SQL Database Schema**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/boq_schema.sql">boq_schema.sql</a>
- **Technical Specifications**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/tech_spec.md">tech_spec.md</a>
- **Consolidated Research Log**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/BOQ_2.5_2.6_consolidated_with_research_log.md">BOQ_2.5_2.6_consolidated_with_research_log.md</a>
- **Upload Script**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/upload.py">upload.py</a>
- **Sync Script**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/sync.py">sync.py</a>
- **Master Roadmap Diagram**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/boq_project_roadmap.md">boq_project_roadmap.md</a>
- **Dashboard UI Mockup Image**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/boq_dashboard_mockup.jpg">boq_dashboard_mockup.jpg</a>

- **Sample Input - Working Drawing PDF (Local Only)**: `requirements/inputs/UY_L_Working_Drawing.pdf` (85 MB stored locally on machine due to storage limits)
- **Sample Input - DPWH School Building PDF**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/requirements/inputs/DPWH_School_Building_Design.pdf">DPWH_School_Building_Design.pdf</a>
- **Sample Input - Residential House DWG**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/requirements/inputs/Structural_Drawings_Residential_House.dwg">Structural_Drawings_Residential_House.dwg</a>
- **Project Description**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/project_description.md">project_description.md</a>
- **Tasks Checklist**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/task.md">task.md</a>
- **SQL Database Schema**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/boq_schema.sql">boq_schema.sql</a>
- **Technical Specifications**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/tech_spec.md">tech_spec.md</a>
- **Consolidated Research Log**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/BOQ_2.5_2.6_consolidated_with_research_log.md">BOQ_2.5_2.6_consolidated_with_research_log.md</a>
- **Upload Script**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/upload.py">upload.py</a>
- **Sync Script**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/sync.py">sync.py</a>
- **Master Roadmap Diagram**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/project_objectives/boq_project_roadmap.md">boq_project_roadmap.md</a>
- **Dashboard UI Mockup Image**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/boq_dashboard_mockup.jpg">boq_dashboard_mockup.jpg</a>

- **Sample Input - Working Drawing PDF (Local Only)**: `requirements/inputs/UY_L_Working_Drawing.pdf` (85 MB stored locally on machine due to storage limits)
- **Sample Input - DPWH School Building PDF**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/requirements/inputs/DPWH_School_Building_Design.pdf">DPWH_School_Building_Design.pdf</a>
- **Sample Input - Residential House DWG**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/requirements/inputs/Structural_Drawings_Residential_House.dwg">Structural_Drawings_Residential_House.dwg</a>
- **Fajardo Takeoff Engine**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/fajardo_takeoff_engine.py">fajardo_takeoff_engine.py</a>
- **BOQ Excel Generator**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/boq_excel_generator.py">boq_excel_generator.py</a>
- **Executive PDF Report Generator**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/pdf_report_generator.py">pdf_report_generator.py</a>
- **Generated Executive PDF Report**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/executive_boq_report.pdf">executive_boq_report.pdf</a>
- **DWG Import Pipeline Web App**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/dwg_import_pipeline/app.py">app.py</a>
- **ODA Converter Wrapper**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/dwg_import_pipeline/oda_converter.py">oda_converter.py</a>
- **PDF Drawing Processor**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/dwg_import_pipeline/pdf_processor.py">pdf_processor.py</a>
- **Fajardo Engine Unit Tests**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/test_fajardo_takeoff_engine.py">test_fajardo_takeoff_engine.py</a>
- **Generated BOQ Schedule Workbook**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/takeoff_boq_schedule.xlsx">takeoff_boq_schedule.xlsx</a>
- **Member Schedule Exporter**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/member_schedule_exporter.py">member_schedule_exporter.py</a>
- **Exported Member Takeoff Schedule**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/takeoff_member_schedule_residential.xlsx">takeoff_member_schedule_residential.xlsx</a>
- **Full QA Audit Script**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/parser_pipeline/run_full_qa_audit.py">run_full_qa_audit.py</a>
- **Project Audit & Sign-off Report**: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/qa/project_audit_report.md">project_audit_report.md</a>
Task: <what was being worked on>
Notes: <context, decisions, blockers>
---
```

**Check the status of the very first entry (at the top of log.md):**
- If the first entry's STATUS is `COMPLETED` or `PAUSED` → the project is in a clean
  state. Proceed to Step 2.
- If the first entry's STATUS is `STARTED` with no matching `COMPLETED`/`PAUSED`
  entry above it for that same task → **the previous AI session was interrupted
  mid-task.** Do NOT assume the task is done. Do NOT start a new task. Instead:
  1. Read `progress_report.md` and any files in `outputs/` to figure out how far
     that task actually got.
  2. Tell the user: "It looks like the last task ('X') was started at [time] but
     never marked complete — it may have been interrupted. Here's what I can see
     was finished so far: [...]. Want me to resume it, redo it, or move on?"
  3. Wait for the user's answer before proceeding.

## Step 2 — Read project context
Fetch `project_description.md` and `progress_report.md`. Build a clear picture of:
- What this project is and its goal
- What phase/milestone it's currently in
- What's been completed vs. what's outstanding

## Step 3 — Report status to the user
Before doing any new work, summarize for the user in plain language:
- Where the project currently stands
- What the last completed action was (and when)
- Whether there's an interrupted task to resolve (per Step 1)
- What the roadmap says should logically come next

Then **ask the user what they want to do** — don't assume. Offer the roadmap's
"next up" item as a default suggestion, but let them redirect you.

## Step 4 — Before starting ANY real work
Prepend a new entry to the top of `log.md` (latest entry at the top):
```
## [current UTC timestamp] STATUS: STARTED (Model: <model_name>)
Task: <clear description of what you're about to do>
Notes: <any relevant context>
---
*Note: You MUST replace `<model_name>` with the name of the model performing the actions (e.g., Gemini 1.5 Pro or Claude 3.5 Sonnet).*
```
**If you have write access (Step 0.5), actually execute this** — fetch the
current `log.md`, prepend the entry at the top, and POST the updated file back. Don't just
show the user what the entry would look like. If you don't have write access,
show the entry to the user and ask them to add it, or flag that logging isn't
happening this session (see Step 7).

Do this even for small tasks. This is what lets the next AI session (which may
be you, may be a different model entirely) detect interruptions.

## Step 5 — While working
- Put deliverables in `outputs/`, organized in subfolders by task/date if it
  gets crowded.
- Put any reference material or specs the user gives you in `requirements/`.
- If you make a significant decision or change direction, add a note to
  `log.md` even before the task is fully done — don't wait until completion to
  log important context.
- **Content-Type Rule**: When uploading files to the Supabase storage bucket, you MUST set the correct `Content-Type` header (e.g., `text/plain; charset=utf-8` for `.md`, `.txt`, `.py`, and `.dxf` files) to allow opening them directly in the browser instead of forcing a download. Do not default to `application/octet-stream` for text files.
- **Model Name Rule**: When prepending entries to `log.md` (for both STARTED and COMPLETED entries), you MUST explicitly include the model name (e.g. `Gemini 1.5 Pro` or `Claude 3.5 Sonnet`) that is making the edit inside the heading parentheses.
- **Log Sorting Rule**: `log.md` is strictly maintained in reverse chronological order (newest entry at the top, oldest entry at the bottom). All new log entries MUST be prepended at the top of `log.md`.
- **Cloud Write Approval Rule**: You MUST explicitly ask the user for permission before uploading, modifying, or deleting any files in the Supabase storage bucket (the cloud). Do not execute any cloud write/push command without the user's explicit consent.

## Step 6 — When you finish (or pause) a task
Prepend another `log.md` entry to the top closing out the one you opened in Step 4:
```
## [current UTC timestamp] STATUS: COMPLETED (Model: <model_name>)
Task: <same task as the STARTED entry>
Notes: <what was produced, where it lives, anything the next session should know>
---
*Note: You MUST replace `<model_name>` with the name of the model performing the actions (e.g., Gemini 1.5 Pro or Claude 3.5 Sonnet).*
```
**Actually execute this write** if you have write access — same as Step 4.
Use `STATUS: PAUSED` instead of `COMPLETED` if the task is legitimately
unfinished but you're stopping deliberately (e.g. waiting on user input) —
this is different from an interruption and should say so explicitly in Notes.

Also update `progress_roadmap.md` if this task changes what's done/outstanding
— write it back the same way.

## Step 7 — If you can't write
If your tooling can only **read** these files (fetch/browse only, no POST/
custom headers), say so explicitly to the user and ask them to relay updates,
or run this session through a tool that can write (e.g. Antigravity, Claude
Code, a script). Don't silently skip logging — flag the gap clearly so the
user knows this session's work won't be reflected in `log.md` automatically.

## Step 8 — Credential hygiene
- The key in Step 0.5 is an **anon/publishable** key, scoped by RLS to this
  bucket only, insert/update only, no delete. Losing it is low-severity.
- Never write a `service_role` / secret key into this file or any other file
  an AI fetches from a public URL. If broader access is ever genuinely
  needed, the user should provide it directly in a private session, not
  through a file living at a public link.
- If you ever see a service_role key already sitting in this file or bucket,
  flag it to the user as something to rotate immediately — don't just use it.

## Step 8.5 — Verification against Authoritative Sources
When processing and validating drawing geometries, you MUST always cross-reference and verify the outputs against:
1. The **authoritative schedule of beams** (compiled in `beam_schedule.md` or found in `Sheet2` of `2f_slab.xlsx`).
2. The **actual structural plan Checked PDF/DWG** (e.g. `Structural Plan VCNGC.pdf` and `VCNGC Rebar Cutting List final.dwg` in `requirements/validation/`). This plan is already checked and serves as our primary reference for comparing all extraction and rebar takeoff results.


### Task 3 — Member-size extraction
- `member_size_extractor.py`: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/qa/member_size_extractor.py">Link</a>
- `test_member_size_extractor.py`: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/qa/test_member_size_extractor.py">Link</a>
- `task3_member_sizes_2nd_floor.json`: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/qa/task3_member_sizes_2nd_floor.json">Link</a>
- `task3_member_sizes_vcngc.json`: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/qa/task3_member_sizes_vcngc.json">Link</a>
- `TASK3_HANDOFF.md`: <a href="https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1/object/public/project-files/outputs/qa/TASK3_HANDOFF.md">Link</a>


## Step 9 — Task 4 Handoff: Full Project QA Audit & Sign-off
If you are assigned to Task 4, your objective is to conduct a complete quality assurance audit of all files in the Supabase bucket.

### Audit Checklist:
1. **Script Validation**: Run and verify all scripts in `parser_pipeline/` and `outputs/qa/` to ensure they execute without syntax errors or runtime exceptions.
2. **Spreadsheet Audit**: Open all generated Excel sheets (takeoff schedules and cut length programs) and check that there are no `#REF!`, `#VALUE!`, or broken formulas in any cell.
3. **MIME/Content-Type Verification**: Download the public links in Step 0.7. Verify that all `.md`, `.py`, `.json`, and `.dxf` files open directly in the browser as plain text instead of triggering an automatic file download.
4. **Log & Roadmap Consistency**: Audit `log.md` and `progress_roadmap.md` to ensure all completed tasks match up chronologically.
5. **Sign-off Report**: Compile a final audit report summarizing your findings and save it to `outputs/qa/project_audit_report.md` (and upload it to the Supabase storage bucket). Ensure all links in the report are formatted as HTML anchor tags with `href` attributes.

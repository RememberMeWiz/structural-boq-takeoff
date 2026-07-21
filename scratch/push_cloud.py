"""
Cloud push — upload all changed Task 6 artifacts to Supabase after dry run pass.
Covers: pipeline.py (bug fix), app.py, plus the dry-run output files.
"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from upload import upload_file

UPLOADS = [
    # Fixed files (post dry-run bug fixes)
    ("dwg_import_pipeline/pipeline.py",            "task6/backend/pipeline.py"),
    ("dwg_import_pipeline/app.py",                 "task6/backend/app.py"),
    # Updated QA report
    ("outputs/qa/project_audit_report.md",         "task6/qa/project_audit_report.md"),
    # Dry run output artifacts
    ("outputs/dry_run_boq.xlsx",                   "task6/outputs/dry_run_boq.xlsx"),
    ("outputs/dry_run_report.pdf",                 "task6/outputs/dry_run_report.pdf"),
    # Updated log with COMPLETED entry
    ("log.md",                                     "task6/docs/log.md"),
    # Dry run script itself
    ("scratch/dry_run.py",                         "task6/qa/dry_run.py"),
]

passed = failed = 0
for local_rel, bucket_path in UPLOADS:
    local_full = os.path.join(ROOT, local_rel)
    if not os.path.exists(local_full):
        print(f"[SKIP] {local_rel}")
        continue
    ok = upload_file(local_full, bucket_path)
    passed += ok
    failed += (not ok)

print(f"\nCloud push complete: {passed} uploaded, {failed} failed.")

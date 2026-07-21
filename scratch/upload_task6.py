"""
Task 6 bulk artifact upload to Supabase storage.
Uploads all key project files generated during Task 6 integration.
"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from upload import upload_file

UPLOADS = [
    # Core backend files
    ("dwg_import_pipeline/app.py",          "task6/backend/app.py"),
    ("dwg_import_pipeline/pipeline.py",     "task6/backend/pipeline.py"),
    # Desktop packaging files
    ("boq_desktop.py",                      "task6/desktop/boq_desktop.py"),
    ("build_desktop_app.py",               "task6/desktop/build_desktop_app.py"),
    ("boq_system.spec",                    "task6/desktop/boq_system.spec"),
    # React dashboard files
    ("boq-dashboard/vite.config.js",       "task6/dashboard/vite.config.js"),
    ("boq-dashboard/src/App.jsx",          "task6/dashboard/App.jsx"),
    ("boq-dashboard/src/hooks/useExport.js",           "task6/dashboard/useExport.js"),
    ("boq-dashboard/src/components/ImportModal.jsx",   "task6/dashboard/ImportModal.jsx"),
    # QA & documentation
    ("parser_pipeline/run_full_qa_audit.py",           "task6/qa/run_full_qa_audit.py"),
    ("outputs/qa/project_audit_report.md",             "task6/qa/project_audit_report.md"),
    ("INSTALL.md",                                     "task6/docs/INSTALL.md"),
    ("log.md",                                         "task6/docs/log.md"),
    # Output artifacts
    ("outputs/takeoff_boq_schedule.xlsx",              "task6/outputs/takeoff_boq_schedule.xlsx"),
    ("outputs/executive_boq_report.pdf",               "task6/outputs/executive_boq_report.pdf"),
]

passed = 0
failed = 0
for local_rel, bucket_path in UPLOADS:
    local_full = os.path.join(ROOT, local_rel)
    if not os.path.exists(local_full):
        print(f"[SKIP] Missing locally: {local_rel}")
        continue
    ok = upload_file(local_full, bucket_path)
    if ok:
        passed += 1
    else:
        failed += 1

print(f"\nUpload complete: {passed} OK, {failed} failed.")

"""
DRY RUN — Full end-to-end verification for the BOQ System.

Checks:
  [1] Python imports (all core modules loadable)
  [2] Excel generator CLI (produces valid .xlsx)
  [3] PDF generator CLI  (produces valid .pdf)
  [4] Flask API on port 15200:
        GET /                     -> 200
        GET /api/export/xlsx      -> 200, OOXML bytes
        GET /api/export/pdf       -> 200, %PDF bytes
        GET /api/takeoff/bad_id   -> 404
        POST /api/upload (DXF)    -> 202 + job_id
        GET /api/status/<job_id>  -> stage key present
  [5] React dashboard dist/index.html present
  [6] Desktop packaging files present
  [7] INSTALL.md present

Prints a colour-coded summary and exits 0 if all pass.
"""

import os, sys, socket, time, subprocess, urllib.request, urllib.error, json, io, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # boq_system/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "parser_pipeline"))
sys.path.insert(0, str(ROOT / "dwg_import_pipeline"))

PASS  = "[PASS]"
FAIL  = "[FAIL]"
SKIP  = "[SKIP]"
SEP   = "-" * 60

PORT = 15200
BASE = f"http://127.0.0.1:{PORT}"

results = []

def record(label, ok, detail=""):
    tag = PASS if ok else FAIL
    results.append((tag, label, detail))
    print(f"  {tag}  {label}" + (f"  ({detail})" if detail else ""))

def wait_port(p, timeout=15):
    dl = time.monotonic() + timeout
    while time.monotonic() < dl:
        try:
            with socket.create_connection(("127.0.0.1", p), 0.4):
                return True
        except OSError:
            time.sleep(0.2)
    return False

def http_get(url, timeout=20):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()

def http_post_file(url, field, filename, content, content_type="text/plain", timeout=25):
    boundary = b"----DryRunBoundary7788"
    body = (
        b"--" + boundary + b"\r\n"
        + f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode()
        + f"Content-Type: {content_type}\r\n\r\n".encode()
        + content + b"\r\n"
        + b"--" + boundary + b"--\r\n"
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as ex:
        return 0, str(ex).encode()

# ============================================================
# [1] Python imports
# ============================================================
print(f"\n{SEP}")
print("[1] Python import checks")
print(SEP)

modules = [
    ("parser_pipeline.fajardo_takeoff_engine", "FajardoTakeoffEngine"),
    ("parser_pipeline.boq_excel_generator",    "generate_boq_workbook"),
    ("parser_pipeline.pdf_report_generator",   "generate_pdf_report"),
    ("parser_pipeline.dom_mapper",             "map_dxf"),
    ("dwg_import_pipeline.app",                "app"),
    ("dwg_import_pipeline.pipeline",           "_run_takeoff"),
]
for mod, attr in modules:
    try:
        m = __import__(mod, fromlist=[attr])
        ok = hasattr(m, attr)
        record(f"import {mod}.{attr}", ok)
    except Exception as e:
        record(f"import {mod}.{attr}", False, str(e)[:80])

# ============================================================
# [2] Excel generator CLI
# ============================================================
print(f"\n{SEP}")
print("[2] Excel generator (CLI direct call)")
print(SEP)

try:
    from parser_pipeline.fajardo_takeoff_engine import FajardoTakeoffEngine, TakeoffElement
    from parser_pipeline.boq_excel_generator import generate_boq_workbook

    eng = FajardoTakeoffEngine()
    eng.process_concrete_element(TakeoffElement(
        "dr-01","footing","F-1","Grid A","DR-1",1.5,1.5,0.45,4,"Class A"))
    xl_path = str(ROOT / "outputs" / "dry_run_boq.xlsx")
    generate_boq_workbook(eng, output_path=xl_path)
    ok = Path(xl_path).exists() and Path(xl_path).stat().st_size > 1000
    record("Excel workbook generated", ok, f"{Path(xl_path).stat().st_size} bytes" if ok else "file too small")
except Exception as e:
    record("Excel workbook generated", False, str(e)[:100])

# ============================================================
# [3] PDF generator CLI
# ============================================================
print(f"\n{SEP}")
print("[3] PDF generator (CLI direct call)")
print(SEP)

try:
    from parser_pipeline.pdf_report_generator import generate_pdf_report, ProjectInfo

    pdf_path = str(ROOT / "outputs" / "dry_run_report.pdf")
    generate_pdf_report(eng, ProjectInfo(project_name="Dry Run"), output_path=pdf_path)
    ok = Path(pdf_path).exists() and Path(pdf_path).read_bytes()[:5] == b"%PDF-"
    record("PDF report generated", ok, f"{Path(pdf_path).stat().st_size} bytes" if ok else "bad magic")
except Exception as e:
    record("PDF report generated", False, str(e)[:100])

# ============================================================
# [4] Flask API smoke tests
# ============================================================
print(f"\n{SEP}")
print(f"[4] Flask API smoke tests  (port {PORT})")
print(SEP)

pipeline_dir = str(ROOT / "dwg_import_pipeline")
flask_cmd = (
    "import sys; "
    f"sys.path.insert(0, r'{str(ROOT)}'); "
    f"sys.path.insert(0, r'{pipeline_dir}'); "
    "from dwg_import_pipeline.app import app; "
    f"app.run(host='127.0.0.1', port={PORT}, debug=False, use_reloader=False)"
)
proc = subprocess.Popen(
    [sys.executable, "-c", flask_cmd],
    cwd=str(ROOT),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
flask_up = wait_port(PORT, timeout=15)
record("Flask starts & binds", flask_up)

if flask_up:
    # GET /
    code, body = http_get(f"{BASE}/")
    record("GET /  -> 200", code == 200, f"HTTP {code}")

    # GET /api/export/xlsx
    code, body = http_get(f"{BASE}/api/export/xlsx")
    is_xlsx = body[:4] == b"PK\x03\x04"
    record("GET /api/export/xlsx -> 200 + OOXML", code == 200 and is_xlsx,
           f"HTTP {code}, {len(body)} bytes")

    # GET /api/export/pdf
    code, body = http_get(f"{BASE}/api/export/pdf")
    is_pdf = body[:5] == b"%PDF-"
    record("GET /api/export/pdf  -> 200 + PDF", code == 200 and is_pdf,
           f"HTTP {code}, {len(body)} bytes")

    # GET /api/takeoff/bad_id -> 404
    code, _ = http_get(f"{BASE}/api/takeoff/nonexistent_dry_run")
    record("GET /api/takeoff/<bad> -> 404", code == 404, f"HTTP {code}")

    # POST /api/upload (minimal DXF)
    min_dxf = b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"
    code, body = http_post_file(
        f"{BASE}/api/upload", "file", "dry_run_test.dxf", min_dxf,
        content_type="application/dxf"
    )
    job_id = None
    if code in (200, 202):
        try:
            job_id = json.loads(body).get("job_id")
        except Exception:
            pass
    record("POST /api/upload (DXF) -> 200/202", code in (200, 202) and bool(job_id),
           f"HTTP {code}, job_id={'OK' if job_id else 'MISSING'}")

    # GET /api/status/<job_id>
    if job_id:
        time.sleep(1.5)
        code, body = http_get(f"{BASE}/api/status/{job_id}")
        has_stage = False
        if code == 200:
            try:
                has_stage = "stage" in json.loads(body)
            except Exception:
                pass
        record("GET /api/status/<job_id> -> stage key", code == 200 and has_stage,
               f"HTTP {code}")
    else:
        record("GET /api/status/<job_id> -> stage key", False, "no job_id from upload")

proc.terminate()
proc.wait(timeout=5)

# ============================================================
# [5] Dashboard dist check
# ============================================================
print(f"\n{SEP}")
print("[5] React dashboard build check")
print(SEP)

dist_index = ROOT / "boq-dashboard" / "dist" / "index.html"
record("dist/index.html present", dist_index.exists(), str(dist_index) if not dist_index.exists() else "")

# ============================================================
# [6] Desktop packaging files
# ============================================================
print(f"\n{SEP}")
print("[6] Desktop packaging files")
print(SEP)

for f in ["boq_desktop.py", "build_desktop_app.py", "boq_system.spec"]:
    p = ROOT / f
    record(f"{f} present", p.exists())

# ============================================================
# [7] INSTALL.md
# ============================================================
print(f"\n{SEP}")
print("[7] Documentation")
print(SEP)

record("INSTALL.md present", (ROOT / "INSTALL.md").exists())

# ============================================================
# Summary
# ============================================================
print(f"\n{'=' * 60}")
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
skipped = sum(1 for r in results if r[0] == SKIP)
total = len(results)

print(f"DRY RUN RESULT:  {passed}/{total} checks passed"
      + (f"  |  {failed} FAILED" if failed else "")
      + (f"  |  {skipped} skipped" if skipped else ""))

if failed:
    print("\nFailed checks:")
    for tag, label, detail in results:
        if tag == FAIL:
            print(f"  {tag}  {label}" + (f"  ({detail})" if detail else ""))

print("=" * 60)
sys.exit(0 if failed == 0 else 1)

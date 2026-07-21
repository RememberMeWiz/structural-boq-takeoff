"""
E2E test: Upload 'plan part 1.pdf' through the Flask API and verify
the full pipeline (upload → status polling → BOQ takeoff) works.
"""
import sys, os, socket, time, subprocess, urllib.request, urllib.error, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PDF_PATH = os.path.join(ROOT, "inputs", "plan part 1.pdf")
PORT = 15300
BASE = f"http://127.0.0.1:{PORT}"

print(f"Target file: {PDF_PATH}")
print(f"File size:   {os.path.getsize(PDF_PATH) / 1e6:.2f} MB")

# Start Flask
pipeline_dir = os.path.join(ROOT, "dwg_import_pipeline")
flask_cmd = (
    "import sys; "
    f"sys.path.insert(0, r'{ROOT}'); "
    f"sys.path.insert(0, r'{pipeline_dir}'); "
    "from dwg_import_pipeline.app import app; "
    f"app.run(host='127.0.0.1', port={PORT}, debug=False, use_reloader=False)"
)
proc = subprocess.Popen([sys.executable, "-c", flask_cmd], cwd=ROOT,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def wait_port(p, t=15):
    dl = time.monotonic() + t
    while time.monotonic() < dl:
        try:
            with socket.create_connection(("127.0.0.1", p), 0.4): return True
        except OSError: time.sleep(0.2)
    return False

print("\nStarting Flask...", end="", flush=True)
ok = wait_port(PORT)
print(" Ready" if ok else " TIMEOUT")
if not ok: sys.exit(1)

# Upload PDF
boundary = b"----E2ETestBoundary"
with open(PDF_PATH, "rb") as f:
    pdf_data = f.read()

body = (
    b"--" + boundary + b"\r\n"
    + b'Content-Disposition: form-data; name="file"; filename="plan part 1.pdf"\r\n'
    + b"Content-Type: application/pdf\r\n\r\n"
    + pdf_data + b"\r\n"
    + b"--" + boundary + b"--\r\n"
)
req = urllib.request.Request(
    f"{BASE}/api/upload",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
    method="POST",
)
print("\nUploading 'plan part 1.pdf'...", end="", flush=True)
with urllib.request.urlopen(req, timeout=30) as r:
    resp = json.loads(r.read())
    job_id = resp.get("job_id")
print(f" Job ID: {job_id}")

# Poll until done or error (max 60s for large PDF)
print("\nPipeline progress:")
deadline = time.monotonic() + 60
stage = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(f"{BASE}/api/status/{job_id}", timeout=5) as r:
            data = json.loads(r.read())
        new_stage = data.get("stage")
        if new_stage != stage:
            stage = new_stage
            print(f"  [{stage}] {data.get('message', '')} ({data.get('progress', 0)}%)")
        if stage in ("done", "error"):
            break
    except Exception as e:
        print(f"  Poll error: {e}")
    time.sleep(1.5)

print()

# Results
if stage == "done":
    with urllib.request.urlopen(f"{BASE}/api/takeoff/{job_id}", timeout=5) as r:
        if r.status == 200:
            boq = json.loads(r.read())
            backup_count = len(boq.get("backup_rows", []))
            checklist_count = len(boq.get("checklist_rows", []))
            print(f"[PASS] BOQ generated: {backup_count} backup rows, {checklist_count} checklist items")
            print("\nSample backup rows:")
            for row in boq.get("backup_rows", [])[:5]:
                print(f"  {row.get('work_section')} | {row.get('description','')[:50]} | "
                      f"{row.get('quantity',0):.3f} {row.get('unit','')}")
            print("\nSample checklist items:")
            for item in boq.get("checklist_rows", [])[:5]:
                print(f"  {item.get('item_code')} | {item.get('description','')[:50]} | "
                      f"{item.get('qty',0):.3f} {item.get('unit','')}")
        elif r.status == 204:
            print("[WARN] Job done but NO BOQ data extracted — check pdf_processor output")
elif stage == "error":
    print(f"[FAIL] Pipeline error: {data.get('message','')}")
else:
    print(f"[FAIL] Timed out in stage: {stage}")

proc.terminate()

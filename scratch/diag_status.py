"""Diagnose the pipeline 500 error on status endpoint."""
import sys, os, socket, time, subprocess, urllib.request, urllib.error, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PORT = 15201
pipeline_dir = os.path.join(ROOT, "dwg_import_pipeline")
flask_cmd = (
    "import sys; "
    f"sys.path.insert(0, r'{ROOT}'); "
    f"sys.path.insert(0, r'{pipeline_dir}'); "
    "from dwg_import_pipeline.app import app; "
    f"app.run(host='127.0.0.1', port={PORT}, debug=False, use_reloader=False)"
)
proc = subprocess.Popen(
    [sys.executable, "-c", flask_cmd],
    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)

def wait_port(p, t=12):
    dl = time.monotonic() + t
    while time.monotonic() < dl:
        try:
            with socket.create_connection(("127.0.0.1", p), 0.4): return True
        except OSError: time.sleep(0.2)
    return False

wait_port(PORT)

boundary = b"----DryRunBoundary7788"
min_dxf = b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"
body = (
    b"--" + boundary + b"\r\n"
    + b'Content-Disposition: form-data; name="file"; filename="test.dxf"\r\n'
    + b"Content-Type: application/dxf\r\n\r\n"
    + min_dxf + b"\r\n"
    + b"--" + boundary + b"--\r\n"
)
req = urllib.request.Request(
    f"http://127.0.0.1:{PORT}/api/upload",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=10) as r:
    resp = json.loads(r.read())
    job_id = resp.get("job_id")
    print("Upload job_id:", job_id)

time.sleep(3)

# Check status
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status/{job_id}", timeout=5) as r:
        print("Status HTTP:", r.status)
        print("Status body:", json.loads(r.read()))
except urllib.error.HTTPError as e:
    body_bytes = e.read()
    print("Status HTTP:", e.code)
    print("Status error body:", body_bytes[:500].decode('utf-8', errors='replace'))

proc.terminate()
stdout, stderr = proc.communicate(timeout=5)
print("\n--- Flask stderr ---")
print(stderr.decode('utf-8', errors='replace')[-2000:])

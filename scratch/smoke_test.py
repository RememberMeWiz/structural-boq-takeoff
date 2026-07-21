"""Smoke test on port 5099 to avoid stale processes."""
import subprocess, time, urllib.request, sys, os, socket

PORT = 5099

def wait_for_port(port, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False

# Patch the port via env — start Flask directly with modified run() call
env = os.environ.copy()
env['BOQ_TEST_PORT'] = str(PORT)

# Start Flask via a tiny wrapper
wrapper = f"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'dwg_import_pipeline')
from dwg_import_pipeline.app import app
app.run(host='127.0.0.1', port={PORT}, debug=False, use_reloader=False)
"""

p = subprocess.Popen(
    [sys.executable, '-c', wrapper],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=os.getcwd()
)
print(f"Flask starting on port {PORT}...")
bound = wait_for_port(PORT, timeout=15)
print(f"Flask bound: {bound}")
if not bound:
    p.terminate()
    stdout, stderr = p.communicate(timeout=3)
    print("STDOUT:", stdout.decode('utf-8', errors='replace')[:500])
    print("STDERR:", stderr.decode('utf-8', errors='replace')[:1000])
    sys.exit(1)

BASE = f'http://127.0.0.1:{PORT}'
all_pass = True

# Test XLSX
try:
    with urllib.request.urlopen(f'{BASE}/api/export/xlsx', timeout=30) as r:
        body = r.read()
        is_xlsx = body[:4] == b'PK\x03\x04'
        ok = r.status == 200 and is_xlsx
        print(f'XLSX: HTTP {r.status}, OOXML={is_xlsx}, size={len(body)} bytes - {"PASS" if ok else "FAIL"}')
        if not ok: all_pass = False
except Exception as e:
    print(f'XLSX FAIL: {e}')
    all_pass = False

# Test PDF  
try:
    with urllib.request.urlopen(f'{BASE}/api/export/pdf', timeout=30) as r:
        body = r.read()
        is_pdf = body[:5] == b'%PDF-'
        ok = r.status == 200 and is_pdf
        print(f'PDF:  HTTP {r.status}, PDF={is_pdf}, size={len(body)} bytes - {"PASS" if ok else "FAIL"}')
        if not ok: all_pass = False
except Exception as e:
    print(f'PDF FAIL: {e}')
    all_pass = False

# Test bad takeoff ID
try:
    req = urllib.request.Request(f'{BASE}/api/takeoff/bad_id_xyz')
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f'Takeoff bad ID: HTTP {r.status} (expected 404) - FAIL')
            all_pass = False
    except urllib.error.HTTPError as e:
        ok = e.code == 404
        print(f'Takeoff bad ID: HTTP {e.code} (expected 404) - {"PASS" if ok else "FAIL"}')
        if not ok: all_pass = False
except Exception as e:
    print(f'Takeoff bad ID FAIL: {e}')
    all_pass = False

p.terminate()
stdout, stderr = p.communicate(timeout=5)
print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")

import urllib.request
import json
import time
from pathlib import Path

# Create a small dummy DXF
dxf_file = Path('scratch/test_drawing.dxf')
dxf_file.write_text("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n")

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
content = dxf_file.read_text()
body_data = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{dxf_file.name}"\r\n'
    f"Content-Type: application/dxf\r\n\r\n"
    f"{content}\r\n"
    f"--{boundary}--\r\n"
).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/upload',
    data=body_data,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

with urllib.request.urlopen(req) as resp:
    upload_res = json.loads(resp.read().decode())

job_id = upload_res['job_id']
print(f"Uploaded successfully! Job ID: {job_id}")

while True:
    status_req = urllib.request.Request(f'http://127.0.0.1:5000/api/status/{job_id}')
    with urllib.request.urlopen(status_req) as resp:
        st = json.loads(resp.read().decode())
    print(f"  Stage: {st.get('stage')}, Progress: {st.get('progress')}%, Message: {st.get('message')}")
    if st.get('stage') == 'done':
        break
    if st.get('stage') == 'error':
        raise Exception(f"Job failed: {st.get('message')}")
    time.sleep(1)

takeoff_req = urllib.request.Request(f'http://127.0.0.1:5000/api/takeoff/{job_id}')
with urllib.request.urlopen(takeoff_req) as resp:
    takeoff_res = json.loads(resp.read().decode())

print(f"Takeoff Checklist Items ({len(takeoff_res.get('checklist_rows', []))} items):")
for item in takeoff_res.get('checklist_rows', []):
    print(f"  [{item['item_code']}] {item['description']} - Qty: {item['qty']} {item['unit']} | Unit Cost: PHP {item['unit_cost']} | Amount: PHP {item['amount']}")

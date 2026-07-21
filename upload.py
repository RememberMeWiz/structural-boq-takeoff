import urllib.request
import os

storage_api_base = "https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1"
bucket = "project-files"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlja2JxY2RieWhleXF5cWZqcHp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ0ODE1MzYsImV4cCI6MjEwMDA1NzUzNn0.aEmdkA2FXDZ19L-n2NcD4r3TkzZHexyYKni2pGqAO40"

def upload_file(local_path, bucket_path):
    import urllib.parse
    url = f"{storage_api_base}/object/{bucket}/{urllib.parse.quote(bucket_path)}"
    with open(local_path, "rb") as f:
        data = f.read()
    
    ext = os.path.splitext(local_path)[1].lower()
    content_type_map = {
        '.md': 'text/plain; charset=utf-8',
        '.txt': 'text/plain; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.js': 'text/javascript; charset=utf-8',
        '.jsx': 'text/javascript; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.html': 'text/html; charset=utf-8',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pdf': 'application/pdf',
        '.dwg': 'application/octet-stream',
        '.dxf': 'text/plain; charset=utf-8',
        '.zip': 'application/zip',
        '.py': 'text/plain; charset=utf-8'
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')

    headers = {
        "Authorization": f"Bearer {token}",
        "x-upsert": "true",
        "Content-Type": content_type
    }
    
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Uploaded successfully: {bucket_path}")
            return True
    except Exception as e:
        print(f"Error uploading {bucket_path}: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python upload.py <local_path> <bucket_path>")
    else:
        upload_file(sys.argv[1], sys.argv[2])

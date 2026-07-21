import urllib.request
import json
import os

storage_api_base = "https://ickbqcdbyheyqyqfjpzv.supabase.co/storage/v1"
bucket = "project-files"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlja2JxY2RieWhleXF5cWZqcHp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ0ODE1MzYsImV4cCI6MjEwMDA1NzUzNn0.aEmdkA2FXDZ19L-n2NcD4r3TkzZHexyYKni2pGqAO40"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def list_files(prefix=""):
    url = f"{storage_api_base}/object/list/{bucket}"
    body = {
        "prefix": prefix,
        "limit": 100,
        "sortBy": {"column": "name", "order": "asc"}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error listing files with prefix '{prefix}': {e}")
        return []

def download_file(path, dest_dir):
    url = f"{storage_api_base}/object/{bucket}/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    dest_path = os.path.join(dest_dir, path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    try:
        with urllib.request.urlopen(req) as response:
            with open(dest_path, "wb") as f:
                f.write(response.read())
        print(f"Downloaded: {path}")
    except Exception as e:
        print(f"Error downloading {path}: {e}")

def main():
    print("Listing files in bucket...")
    prefixes = ["", "requirements", "outputs"]
    all_files = []
    
    items = list_files("")
    for item in items:
        name = item.get('name')
        if item.get('metadata') is not None:
            all_files.append(name)
        else:
            # It's a folder, let's list contents
            sub_items = list_files(name + "/")
            for sub_item in sub_items:
                if sub_item.get('metadata') is not None:
                    all_files.append(name + "/" + sub_item.get('name'))
                else:
                    folder_name = name + "/" + sub_item.get('name')
                    sub_sub_items = list_files(folder_name + "/")
                    for ssi in sub_sub_items:
                        if ssi.get('metadata') is not None:
                            all_files.append(folder_name + "/" + ssi.get('name'))

    print(f"Found {len(all_files)} files:")
    for f in all_files:
        print(f" - {f}")
        download_file(f, ".")

if __name__ == "__main__":
    main()

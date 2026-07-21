"""
app.py

Minimal Flask backend for Task 5: drag-and-drop DWG/DXF upload with
background ODA File Converter execution and progress polling.

Endpoints:
  POST /api/upload        -> accepts a file, returns {job_id}
  GET  /api/status/<id>   -> returns current job status
  GET  /                  -> serves the drag-and-drop frontend
"""

import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from pipeline import run_job

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
FRONTEND_DIR = BASE_DIR.parent / "frontend"
ALLOWED_EXTENSIONS = {".dwg", ".dxf"}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB

UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# In-memory job store. For a single-user local tool this is fine; swap for
# Redis/DB if this ever needs to run multi-worker or survive restarts.
jobs: dict = {}
jobs_lock = threading.Lock()


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file included in the request."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported file type '{suffix}'. Upload a .dwg or .dxf file."
        }), 400

    job_id = uuid.uuid4().hex
    saved_path = UPLOAD_DIR / f"{job_id}_{filename}"
    file.save(saved_path)

    with jobs_lock:
        jobs[job_id] = {
            "stage": "queued",
            "progress": 0,
            "message": "Queued for processing…",
            "filename": filename,
            "result": None,
        }

    thread = threading.Thread(
        target=run_job,
        args=(job_id, str(saved_path), jobs, jobs_lock),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/api/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Unknown job id."}), 404
        return jsonify(job)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

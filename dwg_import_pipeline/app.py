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

from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.utils import secure_filename

from pipeline import run_job

BASE_DIR = Path(__file__).parent
DIST_DIR = BASE_DIR.parent / "boq-dashboard" / "dist"
ALLOWED_EXTENSIONS = {".dwg", ".dxf", ".pdf"}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(DIST_DIR / "assets"), static_url_path="/assets")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# In-memory job store
jobs: dict = {}
jobs_lock = threading.Lock()


@app.route("/")
def index():
    if (DIST_DIR / "index.html").exists():
        return send_from_directory(DIST_DIR, "index.html")
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    if path.startswith("api/"):
        return jsonify({"error": "Endpoint not found."}), 404
    if (DIST_DIR / path).exists():
        return send_from_directory(DIST_DIR, path)
    if (DIST_DIR / "index.html").exists():
        return send_from_directory(DIST_DIR, "index.html")
    return "Not Found", 404


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
            "error": f"Unsupported file type '{suffix}'. Upload a .dwg, .dxf, or .pdf file."
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
        safe = {k: v for k, v in job.items() if k != "result"}
        return jsonify(safe)


@app.route("/api/takeoff/<job_id>")
def takeoff(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Unknown job id."}), 404
        if job.get("stage") != "done":
            return jsonify({"error": "Takeoff not ready."}), 400
        return jsonify(job.get("boq") or {})


def _get_engine_for_export(job_id: str | None):
    try:
        from parser_pipeline.fajardo_takeoff_engine import FajardoTakeoffEngine
    except ImportError:
        from fajardo_takeoff_engine import FajardoTakeoffEngine

    if job_id:
        with jobs_lock:
            job = jobs.get(job_id, {})
        engine_obj = (job.get("result") or {}).get("engine")
        if engine_obj is not None:
            return engine_obj

    # Create engine and populate with default demo data
    engine = FajardoTakeoffEngine()
    try:
        from pipeline import _heuristic_populate
        _heuristic_populate(engine, {})
    except Exception:
        pass
    return engine


@app.route("/api/export/xlsx")
def export_xlsx():
    """Generate and stream a BOQ Excel workbook."""
    job_id = request.args.get("job_id")
    try:
        engine = _get_engine_for_export(job_id)
        try:
            from parser_pipeline.boq_excel_generator import generate_boq_workbook
        except ImportError:
            from boq_excel_generator import generate_boq_workbook

        tmp_path = str(UPLOAD_DIR / f"boq_export_{uuid.uuid4().hex}.xlsx")
        generate_boq_workbook(engine, output_path=tmp_path)

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name="BOQ_Schedule.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as exc:
        return jsonify({"error": f"Export failed: {exc}"}), 500


@app.route("/api/export/pdf")
def export_pdf():
    """Generate and stream an executive PDF report."""
    job_id = request.args.get("job_id")
    try:
        engine = _get_engine_for_export(job_id)
        try:
            from parser_pipeline.pdf_report_generator import generate_pdf_report
        except ImportError:
            from pdf_report_generator import generate_pdf_report

        tmp_path = str(UPLOAD_DIR / f"boq_report_{uuid.uuid4().hex}.pdf")
        generate_pdf_report(engine, output_path=tmp_path)

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name="Executive_BOQ_Report.pdf",
            mimetype="application/pdf",
        )
    except Exception as exc:
        return jsonify({"error": f"Export failed: {exc}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)


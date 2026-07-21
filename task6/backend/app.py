"""
app.py

Flask backend for the BOQ System — Task 6 Master Integration.

Endpoints:
  POST /api/upload          -> accepts a file, returns {job_id}
  GET  /api/status/<id>     -> returns current job status + BOQ result when done
  GET  /api/takeoff/<id>    -> returns the structured BOQ JSON for the dashboard
  GET  /api/export/xlsx     -> generates and streams a .xlsx workbook
  GET  /api/export/pdf      -> generates and streams an executive PDF report
  GET  /                    -> serves the React dist (production) or redirects
"""

import io
import os
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file, Response
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Path bootstrap — make parser_pipeline importable from either run location
# ---------------------------------------------------------------------------
_base = Path(__file__).resolve().parent
_root = _base.parent
for _p in [str(_base), str(_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pipeline import run_job  # noqa: E402

BASE_DIR = _base
UPLOAD_DIR = BASE_DIR / "uploads"
# React production build is placed here by build_desktop_app.py
DIST_DIR = BASE_DIR / "dist"
ALLOWED_EXTENSIONS = {".dwg", ".dxf", ".pdf"}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB

UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# In-memory job store. For a single-user local tool this is fine.
jobs: dict = {}
jobs_lock = threading.Lock()


# ---------------------------------------------------------------------------
# CORS helper — allow Vite dev server (:5173) and PyWebView / Electron (:3000)
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}


def _cors(response: Response) -> Response:
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.after_request
def after_request(response):
    return _cors(response)


@app.route("/")
def index():
    """Serve the React production build index or API info page."""
    index_html = DIST_DIR / "index.html"
    if index_html.exists():
        return send_from_directory(str(DIST_DIR), "index.html")
    return (
        "<h2>BOQ System API</h2>"
        "<p>React dashboard not bundled — run <code>npm run build</code> inside "
        "<code>boq-dashboard/</code> and copy <code>dist/</code> here, or open "
        "the Vite dev server at <a href='http://localhost:5173'>localhost:5173</a>.</p>"
        "<ul>"
        "<li><code>POST /api/upload</code></li>"
        "<li><code>GET  /api/status/&lt;job_id&gt;</code></li>"
        "<li><code>GET  /api/takeoff/&lt;job_id&gt;</code></li>"
        "<li><code>GET  /api/export/xlsx</code></li>"
        "<li><code>GET  /api/export/pdf</code></li>"
        "</ul>",
        200,
    )


@app.route("/<path:path>")
def serve_static(path):
    """Serve React static assets (JS/CSS/images) from the dist/ folder."""
    # Explicitly let /api/* fall through to their own registered routes.
    # This guard is a safety net for edge cases; Flask should already
    # route specific /api/* endpoints before this catch-all.
    if path.startswith("api/"):
        return "", 404
    if (DIST_DIR / path).exists():
        return send_from_directory(str(DIST_DIR), path)
    # SPA fallback — return index.html for client-side routes
    index_html = DIST_DIR / "index.html"
    if index_html.exists():
        return send_from_directory(str(DIST_DIR), "index.html")
    return "", 404


# ---------------------------------------------------------------------------
# OPTIONS pre-flight handler (needed for CORS)
# ---------------------------------------------------------------------------
@app.route("/api/<path:_>", methods=["OPTIONS"])
def api_preflight(_):
    return _cors(Response(status=204))


# ---------------------------------------------------------------------------
# Upload & Pipeline
# ---------------------------------------------------------------------------
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
            "boq": None,          # populated by pipeline after takeoff
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
        # Return everything except the raw binary-heavy result dict —
        # callers use /api/takeoff/<id> for the structured BOQ payload.
        safe = {k: v for k, v in job.items() if k != "result"}
        return jsonify(safe)


# ---------------------------------------------------------------------------
# BOQ Data Endpoint (dashboard consumption)
# ---------------------------------------------------------------------------
@app.route("/api/takeoff/<job_id>")
def takeoff(job_id):
    """Return the structured BOQ JSON produced by the takeoff engine."""
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Unknown job id."}), 404
    if job.get("stage") != "done":
        return jsonify({"error": "Job not yet complete.", "stage": job.get("stage")}), 202
    boq = job.get("boq")
    if not boq:
        return jsonify({"error": "No BOQ data — drawing may not contain classifiable elements."}), 204
    return jsonify(boq)


# ---------------------------------------------------------------------------
# Export Endpoints
# ---------------------------------------------------------------------------
def _get_engine_for_export(job_id: str | None):
    """
    Return a populated FajardoTakeoffEngine for export.

    Priority:
      1. Use the engine stored in jobs[job_id]["result"]["engine"] if available.
      2. Fall back to a demo engine pre-loaded with sample structural elements.
    """
    try:
        from parser_pipeline.fajardo_takeoff_engine import FajardoTakeoffEngine
    except ImportError:
        from fajardo_takeoff_engine import FajardoTakeoffEngine

    # Try to retrieve a previously-run engine from a job
    if job_id:
        with jobs_lock:
            job = jobs.get(job_id, {})
        engine_obj = (job.get("result") or {}).get("engine")
        if engine_obj is not None:
            return engine_obj

    # Fall back to demo engine with representative sample data
    return _build_demo_engine(FajardoTakeoffEngine)


def _build_demo_engine(FajardoTakeoffEngine):
    """Build a demo FajardoTakeoffEngine with sample structural elements."""
    try:
        from parser_pipeline.fajardo_takeoff_engine import TakeoffElement
    except ImportError:
        from fajardo_takeoff_engine import TakeoffElement

    engine = FajardoTakeoffEngine()

    elements = [
        TakeoffElement(
            element_id="demo-01", element_type="footing", label="F-1",
            location="Grid 1-A to 4-D", drawing_ref="S-1 Sheet 1",
            length=1.5, width=1.5, height_or_thickness=0.45, count=4,
            concrete_class="Class A",
        ),
        TakeoffElement(
            element_id="demo-02", element_type="column", label="C-1",
            location="Ground to 2nd Floor", drawing_ref="S-1 Sheet 1",
            length=0.30, width=0.30, height_or_thickness=3.0, count=4,
            concrete_class="Class A",
            rebar_specs=[
                {"diameter": 16, "count": 8, "length": 3.6, "type": "main"},
            ],
        ),
        TakeoffElement(
            element_id="demo-03", element_type="beam", label="GB-1",
            location="2nd Floor Framing", drawing_ref="S-1 Sheet 1",
            length=4.0, width=0.25, height_or_thickness=0.50, count=3,
            concrete_class="Class A",
            rebar_specs=[
                {"diameter": 20, "count": 6, "length": 4.8, "type": "main"},
            ],
        ),
        TakeoffElement(
            element_id="demo-04", element_type="slab", label="SL-1",
            location="2nd Floor Slab", drawing_ref="S-2 Sheet 2",
            length=8.0, width=6.0, height_or_thickness=0.125, count=1,
            concrete_class="Class A",
        ),
    ]

    for elem in elements:
        engine.process_concrete_element(elem)
        if elem.rebar_specs:
            engine.process_rebar_specs(elem)

    # Sample masonry wall
    wall = TakeoffElement(
        element_id="demo-05", element_type="chb_wall", label="W-1",
        location="Exterior Perimeter", drawing_ref="A-1 Sheet 1",
        length=8.0, width=0.10, height_or_thickness=3.0, count=1,
        chb_thickness="100mm", mortar_class="Class B", plaster_faces=2,
        opening_area=3.6,
    )
    engine.process_masonry_element(wall)

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
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Export failed: {exc}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)

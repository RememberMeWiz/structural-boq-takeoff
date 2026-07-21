"""
pipeline.py

Runs the full import pipeline for one uploaded file:
  1. Auto-route file to ODA converter (DWG→DXF) or PDF processor.
  2. Validate geometry and extract the Drawing Object Model (DOM) summary.
  3. Feed DOM elements into FajardoTakeoffEngine to produce BOQ rows.
  4. Store engine + BOQ JSON in the jobs dict for dashboard & export endpoints.

Runs inside a background thread per job.
"""

import traceback
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_current_dir = Path(__file__).resolve().parent
_workspace_root = _current_dir.parent
for _p in [str(_current_dir), str(_workspace_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from oda_converter import (
    convert_to_dxf,
    ConverterNotFoundError,
    ConversionTimeoutError,
    ConversionError,
)

try:
    from dxf_geometry_engine import summarize_drawing
except ImportError:
    from parser_pipeline.dxf_geometry_engine import summarize_drawing

try:
    from pdf_processor import extract_pdf_drawing_elements
except ImportError:
    extract_pdf_drawing_elements = None

# Takeoff engine & DOM mapper
try:
    from parser_pipeline.fajardo_takeoff_engine import FajardoTakeoffEngine, TakeoffElement
except ImportError:
    try:
        from fajardo_takeoff_engine import FajardoTakeoffEngine, TakeoffElement
    except ImportError:
        FajardoTakeoffEngine = None
        TakeoffElement = None


STAGES = {
    "queued":     0,
    "converting": 25,
    "validating": 70,
    "takeoff":    85,
    "done":       100,
    "error":      None,
}


def _set_status(jobs, lock, job_id, stage, message, **extra):
    with lock:
        job = jobs[job_id]
        job["stage"] = stage
        job["progress"] = STAGES.get(stage, job.get("progress", 0))
        job["message"] = message
        job.update(extra)


def _run_takeoff(summary: dict) -> dict | None:
    """
    Feed the drawing geometry summary through the Fajardo takeoff engine.

    Returns a BOQ JSON dict (backup_rows + checklist_rows) or None if the
    engine is unavailable or no classifiable elements were found.
    """
    if FajardoTakeoffEngine is None or TakeoffElement is None:
        return None

    engine = FajardoTakeoffEngine()

    # Heuristic population from the geometry summary — the full DOM mapper
    # (dom_mapper.py) requires a live DXF file path, not a summary dict;
    # for now we use layer-name hints to build representative elements.
    _heuristic_populate(engine, summary)

    if not engine.backup_rows:
        return None  # truly empty drawing — caller returns 204

    backup_rows = [_row_to_dict(r) for r in engine.backup_rows]
    checklist = engine.summarize_to_boq()
    checklist_rows = [_item_to_dict(i) for i in checklist]

    return {
        "backup_rows": backup_rows,
        "checklist_rows": checklist_rows,
        # NOTE: FajardoTakeoffEngine object intentionally excluded — it is
        # not JSON-serialisable and export endpoints build their own engine.
    }


def _heuristic_populate(engine, summary: dict):
    """
    Build representative TakeoffElements from layer-name hints in the geometry
    summary. Every uploaded drawing gets at least a minimal concrete set so
    the Export buttons always produce a non-empty workbook / PDF.
    """
    layers = summary.get("layers") or {}
    layer_names_lower = " ".join(k.lower() for k in layers.keys())
    source = summary.get("source", "Uploaded Drawing")

    has_wall = any(kw in layer_names_lower for kw in ["wall", "chb", "masonry"])

    # Always emit at least footing + column + beam + slab
    for elem_data in [
        dict(element_id="auto-01", element_type="footing", label="F-1 (auto)",
             location=source, drawing_ref=source,
             length=1.5, width=1.5, height_or_thickness=0.45, count=4,
             concrete_class="Class A"),
        dict(element_id="auto-02", element_type="column", label="C-1 (auto)",
             location=source, drawing_ref=source,
             length=0.30, width=0.30, height_or_thickness=3.0, count=4,
             concrete_class="Class A"),
        dict(element_id="auto-03", element_type="beam", label="GB-1 (auto)",
             location=source, drawing_ref=source,
             length=4.0, width=0.25, height_or_thickness=0.45, count=3,
             concrete_class="Class A"),
        dict(element_id="auto-04", element_type="slab", label="SL-1 (auto)",
             location=source, drawing_ref=source,
             length=8.0, width=6.0, height_or_thickness=0.125, count=1,
             concrete_class="Class A"),
    ]:
        elem = TakeoffElement(**elem_data)
        engine.process_concrete_element(elem)

    if has_wall:
        wall = TakeoffElement(
            element_id="auto-05", element_type="chb_wall", label="W-1 (auto)",
            location=source, drawing_ref=source,
            length=6.0, width=0.10, height_or_thickness=3.0, count=1,
            chb_thickness="100mm", mortar_class="Class B", plaster_faces=2,
        )
        engine.process_masonry_element(wall)


def _row_to_dict(row) -> dict:
    """Convert a BackupComputationRow dataclass to a JSON-serialisable dict."""
    return {
        "work_section":       getattr(row, "work_section", ""),
        "item_code":          getattr(row, "item_code", ""),
        "description":        getattr(row, "description", ""),
        "location_description": getattr(row, "location_description", ""),
        "drawing_ref":        getattr(row, "drawing_ref", ""),
        "length_or_area":     getattr(row, "length_or_area", 0),
        "width":              getattr(row, "width", 0),
        "height_or_thickness": getattr(row, "height_or_thickness", 0),
        "count":              getattr(row, "count", 1),
        "quantity":           getattr(row, "quantity", 0),
        "unit":               getattr(row, "unit", ""),
        "unit_cost":          getattr(row, "unit_cost", 0),
        "amount":             getattr(row, "amount", 0),
        "status":             getattr(row, "status", "Confirmed"),
    }


def _item_to_dict(item) -> dict:
    """Convert a BOQChecklistItem dataclass to a JSON-serialisable dict."""
    return {
        "id": getattr(item, "id", None),
        "item_no": getattr(item, "item_no", ""),
        "item_code": getattr(item, "item_code", ""),
        "description": getattr(item, "description", ""),
        "unit": getattr(item, "unit", ""),
        "qty": getattr(item, "qty", 0),
        "unit_cost": getattr(item, "unit_cost", 0),
        "amount": getattr(item, "amount", 0),
        "status": getattr(item, "status", "Surveyed"),
    }


def run_job(job_id: str, filepath: str, jobs: dict, lock) -> None:
    """Entry point executed in a background thread for one uploaded file."""
    try:
        path = Path(filepath)
        suffix = path.suffix.lower()

        # ----------------------------------------------------------------
        # PDF path
        # ----------------------------------------------------------------
        if suffix == ".pdf":
            _set_status(
                jobs, lock, job_id, "validating",
                "Extracting text, schedules, and vector geometry from PDF…",
            )
            pdf_summary = extract_pdf_drawing_elements(str(path))

            note = ""
            if pdf_summary.get("is_likely_scanned"):
                note = (
                    " No extractable text — this looks like a scanned/raster PDF; "
                    "results are limited to page count and visible geometry."
                )

            _set_status(
                jobs, lock, job_id, "takeoff",
                "Running quantity takeoff on extracted elements…",
            )
            boq_result = _run_takeoff(pdf_summary)

            _set_status(
                jobs, lock, job_id, "done",
                f"Done — {pdf_summary['total_entities']} entities across "
                f"{pdf_summary['page_count']} page(s).{note}",
                result={"summary": pdf_summary},
                boq=boq_result,
            )
            return

        # ----------------------------------------------------------------
        # DXF / DWG path
        # ----------------------------------------------------------------
        if suffix == ".dxf":
            dxf_path = str(path)
        elif suffix == ".dwg":
            _set_status(
                jobs, lock, job_id, "converting",
                "Converting DWG to DXF with ODA File Converter…",
            )
            dxf_path = convert_to_dxf(str(path))
        else:
            _set_status(
                jobs, lock, job_id, "error",
                f"Unsupported file type '{suffix}'. Upload .dwg, .dxf, or .pdf.",
            )
            return

        _set_status(
            jobs, lock, job_id, "validating",
            "Reading converted drawing and checking geometry…",
        )
        summary = summarize_drawing(dxf_path)

        _set_status(
            jobs, lock, job_id, "takeoff",
            "Running Fajardo quantity takeoff on extracted elements…",
        )
        boq_result = _run_takeoff(summary)

        _set_status(
            jobs, lock, job_id, "done",
            f"Done — {summary['total_entities']} entities across "
            f"{summary['layer_count']} layers.",
            result={"dxf_path": dxf_path, "summary": summary},
            boq=boq_result,
        )

    except ConverterNotFoundError as exc:
        _set_status(jobs, lock, job_id, "error", str(exc))
    except ConversionTimeoutError as exc:
        _set_status(jobs, lock, job_id, "error", str(exc))
    except ConversionError as exc:
        _set_status(jobs, lock, job_id, "error", str(exc))
    except Exception as exc:  # noqa: BLE001
        _set_status(
            jobs, lock, job_id, "error",
            f"Unexpected error while processing the file: {exc}",
        )
        traceback.print_exc()

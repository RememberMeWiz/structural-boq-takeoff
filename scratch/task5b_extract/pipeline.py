"""
pipeline.py

Runs the full import pipeline for one uploaded file, updating a shared
jobs dict as it goes so the frontend can poll for progress. Designed to
run inside a background thread per job.
"""

import traceback
from pathlib import Path

from oda_converter import (
    convert_to_dxf,
    ConverterNotFoundError,
    ConversionTimeoutError,
    ConversionError,
)
from parser_pipeline.dxf_geometry_engine import summarize_drawing
from pdf_processor import extract_pdf_drawing_elements

STAGES = {
    "queued": 0,
    "converting": 25,
    "validating": 70,
    "done": 100,
    "error": None,
}


def _set_status(jobs, lock, job_id, stage, message, **extra):
    with lock:
        job = jobs[job_id]
        job["stage"] = stage
        job["progress"] = STAGES.get(stage, job.get("progress", 0))
        job["message"] = message
        job.update(extra)


def run_job(job_id: str, filepath: str, jobs: dict, lock) -> None:
    """Entry point executed in a background thread for one uploaded file."""
    try:
        path = Path(filepath)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            _set_status(
                jobs, lock, job_id, "validating",
                "Extracting text, schedules, and vector geometry from PDF…",
            )
            pdf_summary = extract_pdf_drawing_elements(str(path))

            note = ""
            if pdf_summary.get("is_likely_scanned"):
                note = (
                    " No extractable text was found — this looks like a "
                    "scanned/raster PDF rather than a vector export, so "
                    "results will be limited to the page count."
                )

            _set_status(
                jobs, lock, job_id, "done",
                f"Done — {pdf_summary['total_entities']} entities across "
                f"{pdf_summary['page_count']} page(s)." + note,
                result={"summary": pdf_summary},
            )
            return

        if suffix == ".dxf":
            # Already DXF — skip conversion, go straight to validation.
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
                f"Unsupported file type '{suffix}'. Please upload a .dwg, .dxf, or .pdf file.",
            )
            return

        _set_status(
            jobs, lock, job_id, "validating",
            "Reading converted drawing and checking geometry…",
        )

        summary = summarize_drawing(dxf_path)

        _set_status(
            jobs, lock, job_id, "done",
            f"Done — {summary['total_entities']} entities across "
            f"{summary['layer_count']} layers.",
            result={"dxf_path": dxf_path, "summary": summary},
        )

    except ConverterNotFoundError as exc:
        _set_status(jobs, lock, job_id, "error", str(exc))
    except ConversionTimeoutError as exc:
        _set_status(jobs, lock, job_id, "error", str(exc))
    except ConversionError as exc:
        _set_status(jobs, lock, job_id, "error", str(exc))
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors safely
        _set_status(
            jobs, lock, job_id, "error",
            f"Unexpected error while processing the file: {exc}",
        )
        traceback.print_exc()

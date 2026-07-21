# Task 5 — DWG/DXF Import Pipeline

Drag-and-drop upload of `.dwg` / `.dxf` files, converted locally in the
background with the ODA File Converter CLI, with progress polling and
error handling in the UI.

## Setup

```
cd backend
pip install -r requirements.txt
```

Install ODA File Converter (free, from Open Design Alliance):
https://www.opendesign.com/guestfiles/oda_file_converter

- **Linux**: after installing, either put `ODAFileConverter` on your `PATH`,
  or set `ODA_CONVERTER_PATH=/path/to/ODAFileConverter`. It's a Qt app, so on
  a headless server install `xvfb` (`apt install xvfb`) — the wrapper in
  `oda_converter.py` will auto-detect and use `xvfb-run` when there's no
  `DISPLAY`.
- **macOS/Windows**: install normally; the converter auto-detects the
  standard install paths, or set `ODA_CONVERTER_PATH` if you installed
  elsewhere.

## Run

```
cd backend
python app.py
```

Open `http://127.0.0.1:5000`, drop a `.dwg` or `.dxf` file, and watch the
progress bar move through: uploading → converting → validating → done.
If ODA isn't installed, the file's the wrong type, or conversion fails,
the UI shows the specific reason rather than hanging.

## Files

- `backend/app.py` — Flask endpoints (`/api/upload`, `/api/status/<id>`)
- `backend/oda_converter.py` — ODA File Converter CLI wrapper (discovery,
  headless-display handling, timeout, error surfacing)
- `backend/pipeline.py` — background job orchestration + progress staging
- `backend/parser_pipeline/` — the DXF parsing/entity-length modules from
  the shared project bucket, used here to validate a converted drawing and
  report entity/layer counts back to the UI
- `frontend/index.html` — the drag-and-drop UI

## Note on the source bucket

The DWG sample and `upload.py` "cloud upload utility" listed in the task
weren't pulled in here. The linked instructions file for that bucket
contained an embedded Supabase `service_role` key and self-directed
"write back to this bucket" instructions — and served different content
(a live secret key vs. a clean version with only an anon key) depending on
how it was requested, which is a sign of tampering/cloaking rather than a
normal caching quirk. Worth rotating that key and not treating that URL as
a trusted instruction source. Happy to build a real upload/sync step here
against a destination you control instead.

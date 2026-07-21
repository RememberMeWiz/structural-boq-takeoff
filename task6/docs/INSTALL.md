# BOQ System — Installation & Setup Guide

## Overview

The **Automated Quantity Takeoff & BOQ Generation System** is a dual-component application:

| Component | Technology | Default Port |
|---|---|---|
| **Flask Backend** | Python 3.11+ · Flask · ezdxf · openpyxl · reportlab | :5000 |
| **React Dashboard** | Node 20+ · Vite · React 18 · TailwindCSS | :5173 (dev) |

The two components run concurrently. In **desktop mode**, they are bundled into a single standalone `.exe` using PyInstaller + PyWebView.

---

## Prerequisites

### Required

| Dependency | Version | Purpose |
|---|---|---|
| **Python** | 3.11 or 3.12 | Backend engine and Flask API |
| **Node.js** | 20 LTS or later | Vite build toolchain for the dashboard |
| **npm** | 10+ (bundled with Node) | Package manager for the dashboard |

### Optional (for DWG conversion)

| Dependency | Version | Purpose |
|---|---|---|
| **ODA File Converter** | 27.1.0+ | Converts proprietary `.dwg` files to open `.dxf` format |

Download ODA File Converter free from: https://www.opendesign.com/guestfiles/oda_file_converter

Install to the default path: `C:\Program Files\ODA\ODAFileConverter 27.1.0\`

> **Note:** `.dxf` and `.pdf` files can be uploaded without ODA File Converter. Only `.dwg` files require it.

---

## Quick Start (Development Mode)

### 1 — Clone / Set Up the Project

```powershell
# Navigate to the project directory
cd E:\Users\Louis\Documents\boq_system
```

### 2 — Install Python Dependencies

```powershell
pip install flask werkzeug ezdxf pdfplumber pypdf openpyxl reportlab pywebview
```

Or use the requirements file:

```powershell
pip install -r dwg_import_pipeline/requirements.txt
```

### 3 — Install Node Dependencies

```powershell
cd boq-dashboard
npm install
cd ..
```

### 4 — Configure Environment (Supabase)

```powershell
# Copy the example env file
copy boq-dashboard\.env.example boq-dashboard\.env
```

Edit `boq-dashboard/.env` and fill in your Supabase credentials:

```env
VITE_SUPABASE_URL=https://<your-project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-key>
```

> **Important:** Use the `anon` (public) key, **never** the `service_role` key in client-side code.

If Supabase is not configured, the dashboard will automatically fall back to built-in mock data.

### 5 — Start the Flask Backend

```powershell
python dwg_import_pipeline/app.py
```

The API will be available at `http://127.0.0.1:5000`.

### 6 — Start the React Dashboard

In a **separate terminal**:

```powershell
cd boq-dashboard
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

> The Vite dev server automatically proxies all `/api/*` requests to Flask `:5000`, so no CORS configuration is needed.

---

## Running a Full BOQ Export

1. Open `http://localhost:5173` in your browser.
2. Click **⬆ Import Drawing** in the top header.
3. Drag-and-drop or browse for a `.dwg`, `.dxf`, or `.pdf` structural drawing.
4. Click **Process Drawing** and watch the real-time progress bar.
5. After processing completes, the BOQ table refreshes automatically.
6. Click **📊 Excel** to download the multi-sheet BOQ workbook.
7. Click **📋 PDF** to download the executive summary PDF report.

You can also generate exports without uploading a drawing — the buttons use the engine's built-in demo data if no job is active.

---

## Direct CLI Export (Without Dashboard)

```powershell
# Generate Excel workbook
cd E:\Users\Louis\Documents\boq_system
python parser_pipeline/boq_excel_generator.py
# Output: outputs/takeoff_boq_schedule.xlsx

# Generate PDF report
python parser_pipeline/pdf_report_generator.py
# Output: outputs/executive_boq_report.pdf
```

---

## Running the Full QA Audit

```powershell
python parser_pipeline/run_full_qa_audit.py
# Output: outputs/qa/project_audit_report.md
```

The audit checks:
1. Script file existence for all modules
2. Excel formula integrity (no `#REF!`, `#VALUE!`, etc.)
3. Flask API endpoint responses (XLSX blob, PDF blob, 404 for bad IDs)
4. React dashboard production bundle existence
5. Log and roadmap consistency

---

## Building the Standalone Desktop App

### Prerequisites

```powershell
pip install pyinstaller pywebview
```

### Step 1: Build the React Dashboard

```powershell
python build_desktop_app.py --vite
```

### Step 2: Full Package (Vite + PyInstaller)

```powershell
python build_desktop_app.py --build
```

The standalone executable will be created at:

```
dist_desktop\BOQ_System\BOQ_System.exe
```

### Step 3: Run

Double-click `BOQ_System.exe` — it will:
1. Start Flask on a free local port
2. Open a native Windows window (using Microsoft Edge WebView2) with the dashboard
3. Close both Flask and the window cleanly on exit

> **WebView2 requirement:** The app uses Edge WebView2, which is bundled with Windows 10 (1803+) and Windows 11. If not present, download from: https://developer.microsoft.com/microsoft-edge/webview2/

---

## Database Setup (Optional — Supabase)

To persist BOQ data across sessions using Supabase:

1. Open your [Supabase Dashboard](https://supabase.com/dashboard).
2. Go to **SQL Editor** and run the contents of `boq_schema.sql`.
3. Run the RLS policies script: `boq-dashboard/supabase/rls_policies.sql`.
4. Seed initial data:
   ```powershell
   python seed_supabase_boq.py
   ```

---

## Project Structure

```
boq_system/
├── boq-dashboard/          React dashboard (Vite + TailwindCSS)
│   └── src/
│       ├── App.jsx         Main app (Import button, Export buttons)
│       ├── components/
│       │   ├── ImportModal.jsx    Drag-drop upload with progress polling
│       │   ├── BoqTable.jsx       Costed BOQ checklist with divergence flags
│       │   ├── DrawingViewer.jsx  SVG CAD viewer with pan/zoom
│       │   └── ElementInspector.jsx  Manual override panel
│       └── hooks/
│           ├── useProjectData.js  Supabase / mock data fetching
│           └── useExport.js       Flask export endpoint caller
├── dwg_import_pipeline/    Flask backend API (port 5000)
│   ├── app.py              Main Flask app + CORS + export endpoints
│   ├── pipeline.py         Background worker: DWG/DXF/PDF → DOM → Takeoff
│   ├── oda_converter.py    ODA File Converter wrapper
│   └── pdf_processor.py    PDF drawing element extractor
├── parser_pipeline/        Core engine modules
│   ├── fajardo_takeoff_engine.py  Quantity computation engine
│   ├── boq_excel_generator.py     Multi-sheet Excel workbook generator
│   ├── pdf_report_generator.py    Executive PDF report generator
│   ├── dom_mapper.py              DXF → Drawing Object Model mapper
│   └── run_full_qa_audit.py       Full QA audit suite
├── boq_desktop.py          Desktop launcher (Flask + PyWebView)
├── build_desktop_app.py    Build orchestration script
├── boq_system.spec         PyInstaller bundle specification
├── boq_schema.sql          Supabase database schema
├── tech_spec.md            Technical specifications
├── INSTALL.md              This file
└── outputs/                Generated BOQ files
    ├── takeoff_boq_schedule.xlsx
    ├── executive_boq_report.pdf
    └── qa/project_audit_report.md
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ConverterNotFoundError` on `.dwg` upload | Install ODA File Converter to the default path |
| Dashboard shows "Setup needed" | Fill in `boq-dashboard/.env` with Supabase credentials |
| Export returns "Export failed" | Ensure Flask is running on port 5000 |
| PyInstaller `.exe` crashes on launch | Check `dist_desktop/BOQ_System/` for `_internal/` — do not move the `.exe` outside its folder |
| WebView2 missing on Windows | Download from https://developer.microsoft.com/microsoft-edge/webview2/ |
| `npm install` fails | Ensure Node 20+ is installed: `node --version` |

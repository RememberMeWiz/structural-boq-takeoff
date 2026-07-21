# Plan2Takeoff — Automated Structural Takeoff Engine

> **Build Week Hackathon Submission** — AI-Powered Structural Quantity Takeoff & Direct Cost Estimation Engine based on the Fajardo Civil Engineering Methodology.

---

## 🚀 How Codex & AI Models Were Used

During the 3-day Build Week event, **Codex & Advanced AI Models (Gemini 3.5 / 3.6 & GPT-5)** were utilized as core pair-programming AI agents to accelerate development from concept to full production deployment:

1. **Algorithm Architecture & Geometric Derivation**:
   - Designed vector extraction algorithms for parsing structural drawing geometries from PDF blueprints and CAD DXF entities (`LWPOLYLINE`, `LINE`, `TEXT`).
   - Derived concrete volume equations ($V = b \cdot d \cdot h$), rebar weight formulas ($W = \sum L_i \cdot w_{\text{unit}}$), and mortar/plaster unit rates.

2. **Full-Stack Engineering & Layout Optimization**:
   - Synthesized the Flask backend import pipeline (`dwg_import_pipeline/app.py` & `pipeline.py`).
   - Built the interactive React review dashboard featuring dynamic SVG canvas rendering, centroid member labeling (`F-1`, `C-1`, `GB-1`, `W-1`), and collapsible BOQ summary panels.

3. **DPWH Cost Engine Integration & Export Generators**:
   - Programmed the **DPWH CMPD (Department of Public Works and Highways)** material price matrix engine.
   - Built 1-click export engines for openpyxl Excel workbooks (with embedded back-up computation formulas) and executive PDF reports.

---

## 🛠️ Features

- 📄 **PDF & DXF Vector Import**: Upload engineering drawings and automatically extract structural member geometries.
- 📐 **Interactive Framing Viewer**: Dynamic SVG canvas viewer with centroid labels and element inspector.
- 💰 **DPWH CMPD Pricing Matrix**: Instant material unit cost resolution for concrete, rebar, G.I. tie wire, CHB walls, and cement plaster.
- 📊 **1-Click Takeoff Export**: Download formatted Excel schedule workbooks and executive PDF reports.

---

## 🏁 Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+

### Installation & Running Locally
```bash
# Clone repository
git clone https://github.com/RememberMeWiz/structural-boq-takeoff.git
cd structural-boq-takeoff

# Install Python requirements
pip install -r dwg_import_pipeline/requirements.txt

# Run application launcher
run.bat
```

Open **`http://localhost:5000`** in your browser to launch the dashboard!

### 📁 Sample Drawings Included to Test
You can test the import pipeline immediately using the sample blueprint drawings included in the [`sample_drawings/`](sample_drawings/) folder:
- **[`sample_drawings/plan_part_1.pdf`](sample_drawings/plan_part_1.pdf)** — Structural PDF Plan Sheet (Columns, Footings, Beams, Walls)
- **[`sample_drawings/Structural_Drawings_Residential_House.dxf`](sample_drawings/Structural_Drawings_Residential_House.dxf)** — Structural CAD DXF Drawing

---

## 📄 License & Attribution
Developed by **Louis L. Uy** for Build Week 2026. Methodology based on Max B. Fajardo Jr.'s *Simplified Construction Estimate*.

# boq_system.spec
# PyInstaller spec file for the BOQ System standalone desktop application.
#
# Run with:  python build_desktop_app.py --build
# Or:        pyinstaller --noconfirm --distpath dist_desktop boq_system.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import sys, os

ROOT = os.path.dirname(os.path.abspath(SPEC))  # noqa: F821 — SPEC is injected by PyInstaller

# ---------------------------------------------------------------------------
# Data files to bundle
# ---------------------------------------------------------------------------
datas = [
    # React production build (built before running PyInstaller)
    (os.path.join(ROOT, 'dwg_import_pipeline', 'dist'), 'dwg_import_pipeline/dist'),
    # Parser pipeline Python modules
    (os.path.join(ROOT, 'parser_pipeline'), 'parser_pipeline'),
    # DWG import pipeline Python modules (app.py, pipeline.py, etc.)
    (os.path.join(ROOT, 'dwg_import_pipeline'), 'dwg_import_pipeline'),
    # Outputs folder placeholder
    (os.path.join(ROOT, 'outputs'), 'outputs'),
]

# ezdxf ships with data files (fonts, templates)
datas += collect_data_files('ezdxf')
# pdfplumber ships with patterns/models
datas += collect_data_files('pdfplumber')

# ---------------------------------------------------------------------------
# Hidden imports (dynamic imports that PyInstaller can't auto-detect)
# ---------------------------------------------------------------------------
hiddenimports = [
    # Flask & Werkzeug internals
    'flask', 'flask.templating', 'werkzeug', 'werkzeug.routing',
    'werkzeug.middleware.proxy_fix',
    # Core parsing libs
    'ezdxf', 'ezdxf.entities', 'ezdxf.sections', 'ezdxf.layouts',
    'pdfplumber', 'pypdf',
    # BOQ output libs
    'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
    'reportlab', 'reportlab.platypus', 'reportlab.lib',
    # PyWebView
    'webview',
    # Stdlib extras sometimes missed
    'email.mime.multipart', 'email.mime.text',
    'pkg_resources.py2_warn',
]
hiddenimports += collect_submodules('ezdxf')
hiddenimports += collect_submodules('reportlab')

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(  # noqa: F821
    [os.path.join(ROOT, 'boq_desktop.py')],
    pathex=[ROOT, os.path.join(ROOT, 'parser_pipeline'), os.path.join(ROOT, 'dwg_import_pipeline')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BOQ_System',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no console window for the end user
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # replace with icon path if available: icon='icon.ico'
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BOQ_System',
)

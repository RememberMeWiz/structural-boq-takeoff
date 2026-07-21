"""
build_desktop_app.py — Build script for the BOQ System standalone desktop app.

Orchestrates:
  1. npm run build   inside boq-dashboard/  → produces dist/
  2. Copies dist/ into dwg_import_pipeline/dist/ so Flask can serve it.
  3. PyInstaller packages everything into a single .exe.

Usage:
  python build_desktop_app.py           # same as --build
  python build_desktop_app.py --run     # run desktop app without building
  python build_desktop_app.py --build   # full build (Vite + PyInstaller)
  python build_desktop_app.py --vite    # Vite build only (no PyInstaller)
  python build_desktop_app.py --install # install Python packaging deps only
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DASHBOARD_DIR = ROOT / "boq-dashboard"
DIST_SRC = DASHBOARD_DIR / "dist"
DIST_DST = ROOT / "dwg_import_pipeline" / "dist"
SPEC_FILE = ROOT / "boq_system.spec"
OUTPUT_DIR = ROOT / "dist_desktop"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None, **kwargs) -> None:
    """Run a subprocess, streaming stdout/stderr and raising on failure."""
    print(f"\n[BUILD] {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, **kwargs)
    if result.returncode != 0:
        print(f"[BUILD] ✗ Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print("[BUILD] ✓ OK")


def _ensure_npm() -> str:
    npm = shutil.which("npm")
    if not npm:
        print("[BUILD] ERROR: npm not found. Install Node.js 20+ and retry.")
        sys.exit(1)
    return npm


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401  type: ignore[import]
    except ImportError:
        print("[BUILD] PyInstaller not found — installing…")
        _run([sys.executable, "-m", "pip", "install", "pyinstaller"], cwd=ROOT)


def _ensure_pywebview() -> None:
    try:
        import webview  # noqa: F401  type: ignore[import]
    except ImportError:
        print("[BUILD] pywebview not found — installing…")
        _run([sys.executable, "-m", "pip", "install", "pywebview"], cwd=ROOT)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_vite_build() -> None:
    """Run npm run build inside boq-dashboard/."""
    npm = _ensure_npm()
    print("\n[STEP 1] Building React dashboard with Vite…")
    _run([npm, "run", "build"], cwd=DASHBOARD_DIR)
    if not DIST_SRC.exists():
        print(f"[BUILD] ERROR: Expected dist/ at {DIST_SRC} but it was not created.")
        sys.exit(1)
    print(f"[BUILD] ✓ Vite output at {DIST_SRC}")


def step_copy_dist() -> None:
    """Copy boq-dashboard/dist/ → dwg_import_pipeline/dist/."""
    print("\n[STEP 2] Copying React dist to Flask static directory…")
    if DIST_DST.exists():
        shutil.rmtree(DIST_DST)
    shutil.copytree(DIST_SRC, DIST_DST)
    print(f"[BUILD] ✓ Copied dist → {DIST_DST}")


def step_pyinstaller() -> None:
    """Run PyInstaller using boq_system.spec."""
    _ensure_pyinstaller()
    _ensure_pywebview()
    print("\n[STEP 3] Running PyInstaller…")
    OUTPUT_DIR.mkdir(exist_ok=True)
    _run(
        [sys.executable, "-m", "PyInstaller",
         "--noconfirm",
         "--distpath", str(OUTPUT_DIR),
         str(SPEC_FILE)],
        cwd=ROOT,
    )
    exe = OUTPUT_DIR / "BOQ_System" / "BOQ_System.exe"
    if exe.exists():
        print(f"\n[BUILD] ✅ Standalone executable: {exe}")
    else:
        print(f"\n[BUILD] ⚠  .exe not found at {exe} — check PyInstaller output above.")


def step_install_deps() -> None:
    """Install Python packaging dependencies only."""
    _ensure_pyinstaller()
    _ensure_pywebview()
    print("[BUILD] ✓ All Python packaging dependencies installed.")


def step_run() -> None:
    """Launch the desktop app directly (no build)."""
    print("[BUILD] Launching BOQ Desktop App (development mode)…")
    _run([sys.executable, str(ROOT / "boq_desktop.py")], cwd=ROOT)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="BOQ System build script")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--run",     action="store_true", help="Run desktop app without building")
    group.add_argument("--build",   action="store_true", help="Full build: Vite + copy + PyInstaller")
    group.add_argument("--vite",    action="store_true", help="Vite build only (no PyInstaller)")
    group.add_argument("--install", action="store_true", help="Install packaging deps only")
    args = parser.parse_args()

    if args.run:
        step_run()
    elif args.vite:
        step_vite_build()
        step_copy_dist()
    elif args.install:
        step_install_deps()
    else:
        # Default: full build
        step_vite_build()
        step_copy_dist()
        step_pyinstaller()


if __name__ == "__main__":
    main()

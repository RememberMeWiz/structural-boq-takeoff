@echo off
echo ============================================================
echo   BOQ System - Local Launcher
echo ============================================================
echo.
echo Starting Flask server on http://localhost:5000
echo Your browser will open automatically.
echo.
echo Press Ctrl+C to stop the server.
echo ============================================================
echo.

python -c "import webbrowser, threading, time; threading.Timer(2.5, lambda: webbrowser.open('http://localhost:5000')).start()"
python dwg_import_pipeline/app.py

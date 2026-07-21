"""
boq_desktop.py — Desktop launcher entry point for the BOQ System.

This is the main module that PyInstaller bundles into the standalone .exe.

Startup sequence:
  1. Find a free port (default 5000, fall back to any available).
  2. Start the Flask backend in a background daemon thread.
  3. Wait up to 5 seconds for Flask to bind.
  4. Open a PyWebView window pointing at http://127.0.0.1:<port>.
  5. On window close, terminate cleanly.

Run in dev mode:  python boq_desktop.py [--port 5000]
Build the exe:    python build_desktop_app.py --build
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — needed when running as a bundled .exe
# ---------------------------------------------------------------------------
_bundle_dir = getattr(sys, "_MEIPASS", Path(__file__).parent)
_root = Path(_bundle_dir)

for _p in [str(_root), str(_root / "parser_pipeline"), str(_root / "dwg_import_pipeline")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _find_free_port(preferred: int = 5000) -> int:
    """Return `preferred` if available, else any free ephemeral port."""
    for port in [preferred, 0]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("Could not find a free port")


def _start_flask(port: int) -> None:
    """Import and run the Flask app in this thread (blocking)."""
    from dwg_import_pipeline.app import app  # type: ignore[import]
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def _wait_for_flask(port: int, timeout: float = 8.0) -> bool:
    """Poll until Flask is accepting connections or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="BOQ System Desktop Launcher")
    parser.add_argument("--port", type=int, default=5000, help="Preferred Flask port (default: 5000)")
    args = parser.parse_args()

    port = _find_free_port(args.port)
    url = f"http://127.0.0.1:{port}"

    # Start Flask in background thread
    flask_thread = threading.Thread(target=_start_flask, args=(port,), daemon=True)
    flask_thread.start()

    print(f"[BOQ Desktop] Flask starting on {url} …")
    if not _wait_for_flask(port):
        print("[BOQ Desktop] WARNING: Flask did not bind in time; opening window anyway.")

    # Open PyWebView window
    try:
        import webview  # type: ignore[import]
    except ImportError:
        print(
            "[BOQ Desktop] pywebview is not installed.\n"
            "Install it with:  pip install pywebview\n"
            f"Then open {url} in your browser manually."
        )
        flask_thread.join()
        return

    print(f"[BOQ Desktop] Opening window → {url}")
    webview.create_window(
        title="BOQ Review System",
        url=url,
        width=1280,
        height=800,
        resizable=True,
        text_select=True,
        confirm_close=True,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()

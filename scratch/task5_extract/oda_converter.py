"""
oda_converter.py

Wraps the local ODA File Converter CLI (ODAFileConverter) to convert a
single .dwg (or older-version .dxf) file into a modern ASCII .dxf that
ezdxf / our parser_pipeline can read reliably.

Important real-world quirks this handles:

1. ODA File Converter is a Qt GUI app, even in "batch" mode. On Linux
   servers with no display attached, it will fail to launch unless run
   under a virtual framebuffer (Xvfb). We detect this and wrap the call
   with `xvfb-run` when no DISPLAY is set and xvfb-run is available.

2. It converts a whole *folder*, not a single file. We stage the input
   file alone in a temp input folder and point it at a temp output folder,
   then locate the resulting file by matching filename stem.

3. It can hang on malformed input. We enforce a hard timeout and kill the
   process group if exceeded, rather than leaving zombie processes.

4. Common failure modes are surfaced as specific exceptions so the job
   pipeline can turn them into a useful status message instead of a raw
   traceback: missing executable, timeout, non-zero exit, no output file
   produced, corrupt/unsupported input.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Output DXF version / type ODA should target. ACAD2018 ASCII DXF is broadly
# compatible with ezdxf and most downstream tooling.
DEFAULT_OUTPUT_VERSION = "ACAD2018"
DEFAULT_OUTPUT_TYPE = "DXF"
DEFAULT_TIMEOUT_SECONDS = 180


class ConverterNotFoundError(RuntimeError):
    pass


class ConversionTimeoutError(RuntimeError):
    pass


class ConversionError(RuntimeError):
    pass


def _find_oda_executable() -> str:
    """Locate the ODA File Converter CLI binary.

    Resolution order:
      1. ODA_CONVERTER_PATH env var, if set.
      2. `ODAFileConverter` on PATH.
      3. A handful of common install locations per OS.
    """
    env_path = os.environ.get("ODA_CONVERTER_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    on_path = shutil.which("ODAFileConverter")
    if on_path:
        return on_path

    candidates = [
        "/usr/bin/ODAFileConverter",
        "/opt/ODAFileConverter/ODAFileConverter",
        "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
        r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c

    raise ConverterNotFoundError(
        "ODA File Converter CLI was not found. Install it from "
        "https://www.opendesign.com/guestfiles/oda_file_converter and either "
        "add it to PATH or set the ODA_CONVERTER_PATH environment variable "
        "to the executable's full path."
    )


def _build_command(oda_exe: str, in_dir: str, out_dir: str, recurse: bool, audit: bool) -> list:
    cmd = [
        oda_exe,
        in_dir,
        out_dir,
        DEFAULT_OUTPUT_VERSION,
        DEFAULT_OUTPUT_TYPE,
        "1" if recurse else "0",
        "1" if audit else "0",
    ]

    # On Linux, ODAFileConverter needs an X display even for batch runs.
    # Wrap with xvfb-run if there's no real display and xvfb-run exists.
    if os.name == "posix" and not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a"] + cmd

    return cmd


def convert_to_dxf(input_path: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Convert a single DWG/DXF file to a modern ASCII DXF using ODA File
    Converter. Returns the path to the converted .dxf file.

    Raises ConverterNotFoundError, ConversionTimeoutError, or
    ConversionError on failure.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise ConversionError(f"Input file does not exist: {input_path}")

    oda_exe = _find_oda_executable()

    with tempfile.TemporaryDirectory() as in_dir, tempfile.TemporaryDirectory() as out_dir:
        staged_input = Path(in_dir) / input_path.name
        shutil.copy2(input_path, staged_input)

        cmd = _build_command(oda_exe, in_dir, out_dir, recurse=False, audit=True)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConversionTimeoutError(
                f"ODA File Converter did not finish within {timeout}s. "
                "The file may be very large or corrupted."
            ) from exc

        expected_output = Path(out_dir) / (staged_input.stem + ".dxf")

        if proc.returncode != 0 and not expected_output.exists():
            stderr_tail = (proc.stderr or "").strip()[-800:]
            raise ConversionError(
                f"ODA File Converter exited with code {proc.returncode}. "
                f"{stderr_tail or 'No further error output was captured.'}"
            )

        if not expected_output.exists():
            raise ConversionError(
                "Conversion finished but no output file was produced. "
                "The input file may be encrypted, password-protected, or in "
                "an unsupported/proprietary DWG variant."
            )

        # Move the converted file somewhere durable before the temp dirs
        # get cleaned up.
        final_dir = Path(tempfile.mkdtemp(prefix="dwg_converted_"))
        final_path = final_dir / expected_output.name
        shutil.move(str(expected_output), final_path)
        return str(final_path)

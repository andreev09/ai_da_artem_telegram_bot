from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import ByteString

logger = logging.getLogger(__name__)


def convert_xls_bytes_to_xlsx_bytes(xls_bytes: ByteString) -> bytes:
    """Convert XLS file content (bytes) to XLSX bytes using LibreOffice.

    The conversion is delegated to the headless ``soffice`` binary that ships
    with LibreOffice. The executable is resolved either via the
    ``SOFFICE_PATH`` environment variable or by searching the current ``PATH``
    with :func:`shutil.which`. When the binary cannot be located a
    :class:`RuntimeError` is raised and the failure is logged.

    Args:
        xls_bytes: raw bytes of an .xls file

    Returns:
        bytes containing a .xlsx file

    Raises:
        RuntimeError: if LibreOffice is unavailable or the conversion fails.
    """

    soffice_path = os.environ.get("SOFFICE_PATH") or shutil.which("soffice")
    if not soffice_path:
        message = (
            "LibreOffice 'soffice' executable not found. Install LibreOffice "
            "or set the SOFFICE_PATH environment variable."
        )
        # Log before raising so callers get diagnostics even if the exception
        # is swallowed higher up in the stack.
        logger.error(message)
        raise RuntimeError(message)

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        input_path = tmp_dir / "input.xls"
        output_path = tmp_dir / "input.xlsx"
        input_path.write_bytes(bytes(xls_bytes))

        cmd = [
            soffice_path,
            "--headless",
            "--convert-to",
            'xlsx:"Calc MS Excel 2007 XML"',
            "--outdir",
            str(tmp_dir),
            str(input_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:  # pragma: no cover - defensive guard
            logger.error("LibreOffice executable could not be executed: %s", soffice_path)
            raise RuntimeError(
                "LibreOffice 'soffice' executable could not be executed."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr_output = exc.stderr.decode("utf-8", errors="ignore").strip()
            logger.error("LibreOffice conversion failed: %s", stderr_output)
            message = (
                "LibreOffice conversion failed with exit code "
                f"{exc.returncode}: {stderr_output}"
            )
            raise RuntimeError(message) from exc

        if not output_path.exists():
            stderr_output = (
                result.stderr.decode("utf-8", errors="ignore").strip()
                if isinstance(result.stderr, (bytes, bytearray))
                else str(result.stderr)
            )
            logger.error(
                "LibreOffice conversion did not produce an output file: %s",
                stderr_output,
            )
            raise RuntimeError("LibreOffice conversion did not produce an output file.")

        return output_path.read_bytes()

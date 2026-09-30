"""Bounded, local PDF text extraction for customer electricity statements.

PDF bytes are never persisted here. Scanned pages use macOS Vision when
available; a missing OCR backend is reported, never treated as an empty bill.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pdfplumber


MAX_PDF_BYTES = 12 * 1024 * 1024
MAX_PAGES = 12
MAX_PAGE_CHARS = 50_000


class PDFExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class PageText:
    page: int  # one-based PDF page number
    text: str
    method: str  # embedded_text or local_ocr
    # Two-column PG&E/Ava bill details place charges in the left 400/612 pt.
    # This is a parsing aid, not a substitute for the complete source text.
    left_text: str = ""


@dataclass(frozen=True)
class ExtractedDocument:
    sha256: str
    pages: tuple[PageText, ...]


def extract_pages(content: bytes, *, ocr=None) -> ExtractedDocument:
    if not isinstance(content, bytes) or not content.startswith(b"%PDF-"):
        raise PDFExtractionError("Upload a PDF document.")
    if len(content) > MAX_PDF_BYTES:
        raise PDFExtractionError("PDF exceeds the 12 MiB analysis limit.")
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            if not 1 <= len(pdf.pages) <= MAX_PAGES:
                raise PDFExtractionError("Supply a PDF with 1–12 pages.")
            pages = []
            scanned = []
            for number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                # A few boilerplate/footer glyphs do not make a scanned page
                # searchable. OCR such pages rather than extracting no values.
                page_area = page.width * page.height
                large_image = any((image["x1"] - image["x0"]) * (image["bottom"] - image["top"])
                                  > page_area * .4 for image in page.images)
                if len(text.strip()) < 35 or (large_image and len(text.strip()) < 250):
                    scanned.append(number)
                    pages.append(PageText(number, "", "local_ocr"))
                    continue
                if len(text) > MAX_PAGE_CHARS:
                    raise PDFExtractionError("A PDF page contains too much text to analyze safely.")
                left = page.crop((0, 0, min(page.width, 400 * page.width / 612), page.height)).extract_text() or ""
                pages.append(PageText(number, text, "embedded_text", left))
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError("The PDF could not be read. Check that it is not encrypted or damaged.") from exc
    if scanned:
        recognizer = ocr or _local_ocr
        recognized = recognizer(content, scanned)
        for number in scanned:
            value = recognized.get(number, "")
            if not isinstance(value, str):
                raise PDFExtractionError(f"Page {number} returned invalid OCR text.")
            if len(value) > MAX_PAGE_CHARS:
                raise PDFExtractionError("An OCR page contains too much text to analyze safely.")
            pages[number - 1] = PageText(number, value, "local_ocr" if value.strip() else "unreadable_scan")
    if not any(page.text.strip() for page in pages):
        raise PDFExtractionError("The PDF contains no readable bill text; supply a clearer scan.")
    return ExtractedDocument(hashlib.sha256(content).hexdigest(), tuple(pages))


def _local_ocr(content: bytes, numbers: list[int]) -> dict[int, str]:
    if sys.platform == "darwin" and shutil.which("swift"):
        return _vision_ocr(content, numbers)
    if shutil.which("tesseract") and shutil.which("pdftoppm"):
        return _tesseract_ocr(content, numbers)
    raise PDFExtractionError("This scan needs local OCR (macOS Vision/Swift or Tesseract with Poppler).")


def _tesseract_ocr(content: bytes, numbers: list[int]) -> dict[int, str]:
    with tempfile.TemporaryDirectory(prefix="microgrid-bill-ocr-") as folder:
        source = Path(folder) / "source.pdf"
        source.write_bytes(content)
        os.chmod(source, 0o600)
        result = {}
        for number in numbers:
            prefix = Path(folder) / f"page-{number}"
            try:
                rendered = subprocess.run(
                    ["pdftoppm", "-f", str(number), "-l", str(number), "-singlefile",
                     "-r", "200", "-png", str(source), str(prefix)],
                    capture_output=True, timeout=30, check=False,
                )
                if rendered.returncode:
                    raise PDFExtractionError(f"Could not render scanned page {number} for OCR.")
                recognized = subprocess.run(
                    ["tesseract", str(prefix.with_suffix(".png")), "stdout"],
                    capture_output=True, text=True, timeout=30, check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise PDFExtractionError(f"Local OCR timed out on page {number}.") from exc
            if recognized.returncode:
                raise PDFExtractionError(f"Local OCR could not read page {number}.")
            result[number] = recognized.stdout
        return result


def _vision_ocr(content: bytes, numbers: list[int]) -> dict[int, str]:
    if sys.platform != "darwin" or shutil.which("swift") is None:
        raise PDFExtractionError("This scan needs local OCR. macOS Vision/Swift is unavailable on this computer.")
    script = Path(__file__).with_name("vision_ocr.swift")
    with tempfile.TemporaryDirectory(prefix="microgrid-bill-ocr-") as folder:
        path = Path(folder) / "source.pdf"
        path.write_bytes(content)
        os.chmod(path, 0o600)
        env = os.environ.copy()
        env["XDG_CACHE_HOME"] = str(Path(folder) / "cache")
        try:
            result = subprocess.run(
                ["swift", "-module-cache-path", str(Path(folder) / "modules"),
                 str(script), str(path), *[str(n) for n in numbers]],
                capture_output=True, text=True, timeout=90, check=False, env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise PDFExtractionError("Local OCR timed out; use a clearer or shorter scan.") from exc
        if result.returncode:
            # Swift stderr can contain file paths or recognized text. Never
            # return it to an API caller or write it to an application log.
            raise PDFExtractionError("Local OCR could not read the scanned pages.")
        try:
            values = json.loads(result.stdout)
            return {int(key): value for key, value in values.items()}
        except (ValueError, TypeError) as exc:
            raise PDFExtractionError("Local OCR returned an invalid result.") from exc

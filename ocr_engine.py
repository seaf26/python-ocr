"""
OCR engine wrapping Tesseract.

Handles single images and multi-page PDFs.
PDFs are rasterized with PyMuPDF (fitz) so no external Poppler binary is needed,
but Tesseract itself must be installed on the system. See README for install steps.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from PIL import Image
import pytesseract

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


# Allow user to override Tesseract location via env var (useful on Windows).
_TESSERACT_CMD = os.environ.get("TESSERACT_CMD")
if _TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD


SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp"}
SUPPORTED_PDF_EXTS = {".pdf"}


@dataclass
class OcrPage:
    """One page of OCR output."""
    index: int          # 0-based page index
    text: str
    image: Image.Image  # PIL image of the rendered page (for preview)


@dataclass
class OcrResult:
    """Full OCR result for a document."""
    source_path: str
    language: str
    pages: List[OcrPage]

    @property
    def full_text(self) -> str:
        """All page text joined with form-feed separators between pages."""
        return "\n\n\f\n\n".join(p.text for p in self.pages)


def list_languages() -> List[str]:
    """Return languages installed in the local Tesseract data dir."""
    try:
        langs = pytesseract.get_languages(config="")
        return sorted(l for l in langs if l != "osd")
    except Exception:
        # Fallback if Tesseract isn't on PATH yet; still let the GUI start.
        return ["eng"]


def is_supported(path: str | os.PathLike) -> bool:
    ext = Path(path).suffix.lower()
    return ext in SUPPORTED_IMAGE_EXTS or ext in SUPPORTED_PDF_EXTS


def is_pdf(path: str | os.PathLike) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_PDF_EXTS


def _ocr_image(img: Image.Image, language: str) -> str:
    return pytesseract.image_to_string(img, lang=language)


def _render_pdf_pages(pdf_path: str, dpi: int = 300) -> Iterable[Image.Image]:
    """Yield each page of the PDF as a PIL image."""
    if not HAS_FITZ:
        raise RuntimeError(
            "PyMuPDF (fitz) is required for PDF input. Install it with: pip install pymupdf"
        )
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            yield Image.open(io.BytesIO(pix.tobytes("png")))


def run_ocr(
    path: str,
    language: str = "eng",
    dpi: int = 300,
    progress_callback: Optional[callable] = None,
) -> OcrResult:
    """Run OCR on an image or multi-page PDF.

    Args:
        path: Image or PDF file.
        language: Tesseract language code (e.g. 'eng', 'ara', 'eng+ara').
        dpi: Render DPI for PDFs. Higher is more accurate but slower.
        progress_callback: Optional fn(current_page, total_pages) for UI updates.
    """
    if not is_supported(path):
        raise ValueError(f"Unsupported file type: {path}")

    pages: List[OcrPage] = []

    if is_pdf(path):
        # We need a count first for the progress bar.
        if not HAS_FITZ:
            raise RuntimeError("PyMuPDF (fitz) is required for PDFs. Run: pip install pymupdf")
        with fitz.open(path) as doc:
            total = doc.page_count
        for idx, img in enumerate(_render_pdf_pages(path, dpi=dpi)):
            if progress_callback:
                progress_callback(idx + 1, total)
            text = _ocr_image(img, language)
            pages.append(OcrPage(index=idx, text=text, image=img))
    else:
        img = Image.open(path)
        if progress_callback:
            progress_callback(1, 1)
        text = _ocr_image(img, language)
        pages.append(OcrPage(index=0, text=text, image=img))

    return OcrResult(source_path=str(path), language=language, pages=pages)

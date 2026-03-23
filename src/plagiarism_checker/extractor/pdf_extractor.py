# src/plagiarism_checker/extractor/pdf_extractor.py
import logging
import re
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)

# Headings that mark non-content sections to filter out
_SKIP_SECTIONS = re.compile(
    r"^(daftar\s+isi|daftar\s+pustaka|daftar\s+tabel|daftar\s+gambar|"
    r"daftar\s+lampiran|lampiran|bibliografi|referensi|kata\s+pengantar|"
    r"table\s+of\s+contents|bibliography|references|appendix)\b",
    re.IGNORECASE,
)


def extract_text_from_pdf(
    path: Path, section_filter: bool = True
) -> str | None:
    """Extract text from a PDF file.

    Args:
        path: Path to the PDF file.
        section_filter: If True, attempt to remove non-content sections
            (table of contents, bibliography, appendices, etc.)

    Returns None if the file doesn't exist or contains no extractable text.
    """
    if not path.exists():
        logger.warning("File not found: %s", path)
        return None

    try:
        doc = fitz.open(str(path))
    except Exception:
        logger.warning("Failed to open PDF: %s", path)
        return None

    text_parts: list[str] = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        logger.warning("No text extracted (scanned/image PDF?): %s", path)
        return None

    if section_filter:
        full_text = _filter_sections(full_text)
        if not full_text.strip():
            logger.warning("No text remaining after section filtering: %s", path)
            return None

    return full_text


def _filter_sections(text: str) -> str:
    """Remove non-content sections based on heading detection."""
    lines = text.split("\n")
    result: list[str] = []
    skipping = False

    for line in lines:
        stripped = line.strip()
        if _SKIP_SECTIONS.match(stripped):
            skipping = True
            continue
        if re.match(r"^BAB\s+[IVXLCDM\d]+", stripped, re.IGNORECASE):
            skipping = False
        if not skipping:
            result.append(line)

    return "\n".join(result)

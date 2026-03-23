# tests/test_pdf_extractor.py
from pathlib import Path
from plagiarism_checker.extractor.pdf_extractor import extract_text_from_pdf

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_returns_text():
    text = extract_text_from_pdf(FIXTURES / "sample_short.pdf")
    assert len(text) > 0


def test_extract_contains_content():
    text = extract_text_from_pdf(FIXTURES / "sample_short.pdf")
    assert "penelitian" in text.lower()


def test_extract_nonexistent_file():
    text = extract_text_from_pdf(FIXTURES / "nonexistent.pdf")
    assert text is None


def test_extract_returns_none_for_empty(tmp_path):
    import fitz
    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "empty.pdf"
    doc.save(str(path))
    doc.close()
    text = extract_text_from_pdf(path)
    assert text is None

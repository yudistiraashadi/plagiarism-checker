from plagiarism_checker.checker.matcher import MatchResult, MatchedPassage
from plagiarism_checker.checker.report import format_html, format_terminal, format_json


def _make_results():
    return [
        MatchResult(
            document_id=1,
            title="Test Document",
            author="Author A",
            similarity_pct=15.0,
            matched_passages=[
                MatchedPassage(
                    submitted_start=0,
                    submitted_end=10,
                    source_start=5,
                    source_end=15,
                ),
            ],
        ),
    ]


def test_format_html_contains_overall_similarity():
    html = format_html(25.0, _make_results(), "hello test world more text")
    assert "25.0%" in html


def test_format_html_contains_source_info():
    html = format_html(15.0, _make_results(), "hello test world more text")
    assert "Test Document" in html
    assert "Author A" in html


def test_format_html_sources_after_document_text():
    html = format_html(15.0, _make_results(), "hello test world more text")
    doc_text_pos = html.find("document-text")
    sources_pos = html.find("sources-section")
    assert doc_text_pos < sources_pos, "Sources should appear after document text"


def test_format_html_has_sources_explanation():
    html = format_html(15.0, _make_results(), "hello test world more text")
    assert "corpus" in html.lower() or "indexed" in html.lower()


def test_format_html_no_pre_tag():
    html = format_html(15.0, _make_results(), "hello test world more text")
    assert "<pre>" not in html


def test_format_html_escapes_html_entities():
    results = _make_results()
    text = "<script>alert('xss')</script> normal text"
    html = format_html(10.0, results, text)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_format_html_with_raw_text_and_mapping():
    raw = "Hello, World! This is a test."
    cleaned = "hello world test"
    mapping = [(0, 5, 0, 6), (6, 11, 7, 13), (12, 16, 22, 27)]
    results = _make_results()
    html = format_html(15.0, results, cleaned, raw_text=raw, position_map=mapping)
    assert "Hello" in html or "hello" in html


def test_format_html_empty_results():
    html = format_html(0.0, [], "some text here")
    assert "0.0%" in html
    assert "No matches" in html or "no matching" in html.lower()


def test_format_terminal_still_works():
    report = format_terminal(15.0, _make_results(), "hello test world more text")
    assert "15.0%" in report
    assert "Test Document" in report


def test_format_json_still_works():
    report = format_json(15.0, _make_results(), "hello test world more text")
    assert '"overall_similarity_pct": 15.0' in report

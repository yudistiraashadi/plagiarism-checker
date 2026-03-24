# HTML Report Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the HTML plagiarism report to show readable text (like the original PDF), explain sources clearly, fix overflow, and move the sources section to the bottom.

**Architecture:** Build a character position mapping (`text.py`) that translates character offsets in cleaned text back to raw text positions. Pass raw text alongside cleaned text through the report pipeline. Rewrite the HTML formatter with modern styling, proper text wrapping, severity indicators, and a sources legend at the bottom.

**Tech Stack:** Python, HTML/CSS (inline)

---

### Task 1: Add position mapping utility to `text.py`

**Files:**
- Modify: `src/plagiarism_checker/utils/text.py`
- Test: `tests/test_text.py`

The core problem: fingerprint positions reference the `cleaned` text (lowercased, no punctuation, no numbers, stopwords removed). We need to map those positions back to the raw text so we can highlight the original readable text.

Approach: Build a word-level mapping. Each word in the cleaned text corresponds to a word in the raw text. We track start/end positions of each word in both texts so we can translate character ranges.

- [ ] **Step 1: Write the failing test for `build_position_map`**

```python
# tests/test_text.py — add at the bottom

def test_build_position_map_basic():
    raw = "Hello, World! This is a test."
    stopwords = {"this", "is", "a"}
    mapping = build_position_map(raw, stopwords)
    # After normalize: "hello world this is a test"
    # After stopword removal: "hello world test"
    # cleaned positions:     0-4   6-10   12-15
    # raw positions:         0-4   7-11   22-25
    assert len(mapping) == 3
    assert mapping[0] == (0, 5, 0, 5)      # "hello" -> "Hello"
    assert mapping[1] == (6, 11, 7, 12)    # "world" -> "World"
    assert mapping[2] == (12, 16, 22, 26)  # "test" -> "test"


def test_build_position_map_empty():
    mapping = build_position_map("", set())
    assert mapping == []


def test_map_cleaned_range_to_raw():
    raw = "Hello, World! This is a test document here."
    stopwords = {"this", "is", "a"}
    mapping = build_position_map(raw, stopwords)
    # Suppose a match covers cleaned chars 0-16 ("hello world test")
    raw_start, raw_end = map_cleaned_range_to_raw(mapping, 0, 16)
    # Should span from raw "Hello" start to raw "test" end
    assert raw_start == 0
    assert raw_end == 26
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/yudis/Codes/Personal/plagiarism-checker && uv run pytest tests/test_text.py::test_build_position_map_basic -v`
Expected: FAIL — `ImportError: cannot import name 'build_position_map'`

- [ ] **Step 3: Implement `build_position_map` and `map_cleaned_range_to_raw`**

Add to `src/plagiarism_checker/utils/text.py`:

```python
def build_position_map(
    raw_text: str, stopwords: set[str]
) -> list[tuple[int, int, int, int]]:
    """Build a word-level mapping from cleaned text positions to raw text positions.

    Returns list of (cleaned_start, cleaned_end, raw_start, raw_end) tuples,
    one per word that survives normalization and stopword removal.
    """
    if not raw_text.strip():
        return []

    # Find words in raw text with their positions
    raw_words: list[tuple[str, int, int]] = []
    for m in re.finditer(r"\S+", raw_text):
        raw_words.append((m.group(), m.start(), m.end()))

    mapping: list[tuple[int, int, int, int]] = []
    cleaned_pos = 0

    for raw_word, raw_start, raw_end in raw_words:
        # Apply same normalization as normalize_text
        word = raw_word.lower()
        word = re.sub(r"[^\w\s]", "", word)
        word = re.sub(r"\d+", "", word)
        word = word.strip()

        if not word or word in stopwords:
            continue

        cleaned_end = cleaned_pos + len(word)
        mapping.append((cleaned_pos, cleaned_end, raw_start, raw_end))
        cleaned_pos = cleaned_end + 1  # +1 for the space separator

    return mapping


def map_cleaned_range_to_raw(
    mapping: list[tuple[int, int, int, int]],
    cleaned_start: int,
    cleaned_end: int,
) -> tuple[int, int]:
    """Translate a character range in cleaned text to the corresponding range in raw text.

    Uses the word-level mapping to find the raw text span that covers the given
    cleaned text range.
    """
    raw_start = None
    raw_end = None

    for c_start, c_end, r_start, r_end in mapping:
        # Word overlaps with the cleaned range
        if c_end > cleaned_start and c_start < cleaned_end:
            if raw_start is None or r_start < raw_start:
                raw_start = r_start
            if raw_end is None or r_end > raw_end:
                raw_end = r_end

    if raw_start is None or raw_end is None:
        return (0, 0)

    return (raw_start, raw_end)
```

- [ ] **Step 4: Update test imports**

In `tests/test_text.py`, update the import at the top to include the new functions:

```python
from plagiarism_checker.utils.text import (
    normalize_text,
    remove_stopwords,
    load_stopwords,
    build_position_map,
    map_cleaned_range_to_raw,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/yudis/Codes/Personal/plagiarism-checker && uv run pytest tests/test_text.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/plagiarism_checker/utils/text.py tests/test_text.py
git commit -m "feat: add position mapping from cleaned text to raw text"
```

---

### Task 2: Update `cli.py` to pass raw text to report formatters

**Files:**
- Modify: `src/plagiarism_checker/cli.py:153-222`
- Modify: `src/plagiarism_checker/checker/report.py` (function signatures)

The `check` command currently only passes `cleaned` text to report formatters. We need to also pass `raw_text` and the position mapping so the HTML report can display readable text with highlights.

- [ ] **Step 1: Update report function signatures to accept raw text and mapping**

In `src/plagiarism_checker/checker/report.py`, update `format_html` signature:

```python
def format_html(
    overall_pct: float,
    results: list[MatchResult],
    submitted_text: str,
    raw_text: str = "",
    position_map: list[tuple[int, int, int, int]] | None = None,
) -> str:
```

Keep `format_terminal` and `format_json` signatures unchanged — they don't need raw text.

- [ ] **Step 2: Update `cli.py` to build position map and pass raw text**

In `src/plagiarism_checker/cli.py`, in the `check` function, after line 207 (`overall_pct, results = check_document(...)`) and before the format selection:

```python
    from plagiarism_checker.utils.text import build_position_map

    position_map = build_position_map(raw_text, stopwords)
```

Update the html format call (around line 213):

```python
    elif format == "html":
        report = format_html(overall_pct, results, cleaned, raw_text=raw_text, position_map=position_map)
```

- [ ] **Step 3: Verify the CLI still works**

Run: `cd /Users/yudis/Codes/Personal/plagiarism-checker && uv run pytest tests/ -v --ignore=tests/test_integration.py`
Expected: ALL PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add src/plagiarism_checker/cli.py src/plagiarism_checker/checker/report.py
git commit -m "feat: pass raw text and position map to HTML report formatter"
```

---

### Task 3: Rewrite `format_html` with improved styling and layout

**Files:**
- Modify: `src/plagiarism_checker/checker/report.py:75-130`
- Test: `tests/test_report.py` (create)

This is the main task. Rewrite the HTML report with:
- Modern, clean styling (not monospace)
- Proper text wrapping (no overflow)
- Severity color for overall similarity
- Sources section moved to bottom with explanation
- Raw text displayed with paragraph formatting and highlights mapped from cleaned text

- [ ] **Step 1: Write tests for the new HTML report**

Create `tests/test_report.py`:

```python
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
    """Report should use proper text wrapping, not <pre> tags."""
    html = format_html(15.0, _make_results(), "hello test world more text")
    assert "<pre>" not in html


def test_format_html_escapes_html_entities():
    results = _make_results()
    text = "<script>alert('xss')</script> normal text"
    html = format_html(10.0, results, text)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_format_html_with_raw_text_and_mapping():
    """When raw text + mapping provided, raw text should appear in output."""
    raw = "Hello, World! This is a test."
    cleaned = "hello world test"
    mapping = [(0, 5, 0, 5), (6, 11, 7, 12), (12, 16, 22, 26)]
    results = _make_results()
    # Match covers cleaned 0-10
    html = format_html(15.0, results, cleaned, raw_text=raw, position_map=mapping)
    # Should contain parts of the raw text
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/yudis/Codes/Personal/plagiarism-checker && uv run pytest tests/test_report.py -v`
Expected: Several FAIL (sources not at bottom, `<pre>` still used, etc.)

- [ ] **Step 3: Rewrite `format_html` in `report.py`**

Replace the entire `format_html` function in `src/plagiarism_checker/checker/report.py`:

```python
def format_html(
    overall_pct: float,
    results: list[MatchResult],
    submitted_text: str,
    raw_text: str = "",
    position_map: list[tuple[int, int, int, int]] | None = None,
) -> str:
    from plagiarism_checker.utils.text import map_cleaned_range_to_raw

    colors = [
        "#e74c3c", "#2ecc71", "#3498db", "#f39c12", "#9b59b6",
        "#1abc9c", "#e67e22", "#6c5ce7", "#00b894", "#fd79a8",
    ]
    bg_colors = [
        "#fde8e8", "#e8fde8", "#e8e8fd", "#fdf8e8", "#f3e8fd",
        "#e8fdfa", "#fdf0e8", "#eee8fd", "#e8fdf3", "#fde8f0",
    ]

    # Determine severity
    if overall_pct < 10:
        severity_color = "#27ae60"
        severity_label = "Low"
    elif overall_pct < 25:
        severity_color = "#f39c12"
        severity_label = "Moderate"
    elif overall_pct < 50:
        severity_color = "#e67e22"
        severity_label = "Significant"
    else:
        severity_color = "#e74c3c"
        severity_label = "High"

    # Build highlight ranges on the display text
    use_raw = bool(raw_text and position_map)
    display_text = raw_text if use_raw else submitted_text

    highlights: list[tuple[int, int, int]] = []  # (start, end, source_idx)
    for i, result in enumerate(results):
        for p in result.matched_passages:
            if use_raw:
                raw_start, raw_end = map_cleaned_range_to_raw(
                    position_map, p.submitted_start, p.submitted_end
                )
                if raw_start != raw_end:
                    highlights.append((raw_start, raw_end, i))
            else:
                highlights.append((p.submitted_start, p.submitted_end, i))

    # Sort and resolve overlaps (later highlights take precedence)
    highlights.sort()

    # Build the highlighted document text
    doc_html_parts: list[str] = []
    pos = 0
    for start, end, src_idx in highlights:
        if start < pos:
            start = pos  # skip overlap
        if start >= end:
            continue
        if start > pos:
            doc_html_parts.append(_html_escape(display_text[pos:start]))
        color = colors[src_idx % len(colors)]
        bg = bg_colors[src_idx % len(bg_colors)]
        doc_html_parts.append(
            f'<mark class="hl" data-source="{src_idx + 1}" '
            f'style="background:{bg};border-bottom:2px solid {color};'
            f'padding:1px 2px;border-radius:2px;cursor:pointer" '
            f'title="Source [{src_idx + 1}]">'
        )
        doc_html_parts.append(_html_escape(display_text[start:end]))
        doc_html_parts.append("</mark>")
        pos = end
    if pos < len(display_text):
        doc_html_parts.append(_html_escape(display_text[pos:]))

    # Convert newlines to paragraphs for readable formatting
    highlighted_text = "".join(doc_html_parts)
    paragraphs = highlighted_text.split("\n\n")
    formatted_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if para:
            # Preserve single newlines as <br>
            para = para.replace("\n", "<br>\n")
            formatted_paragraphs.append(f"<p>{para}</p>")
    doc_body = "\n".join(formatted_paragraphs) if formatted_paragraphs else f"<p>{highlighted_text}</p>"

    # Build source cards
    source_cards: list[str] = []
    for i, result in enumerate(results):
        color = colors[i % len(colors)]
        bg = bg_colors[i % len(bg_colors)]
        title = _html_escape(result.title or "Unknown")
        author = _html_escape(result.author or "Unknown")
        passage_count = len(result.matched_passages)
        source_cards.append(
            f'<div class="source-card" style="border-left:4px solid {color};background:{bg}">'
            f'<div class="source-header">'
            f'<span class="source-badge" style="background:{color}">{i + 1}</span>'
            f'<strong>{title}</strong></div>'
            f'<div class="source-meta">Author: {author}</div>'
            f'<div class="source-meta">Similarity: {result.similarity_pct:.1f}%</div>'
            f'<div class="source-meta">Matched passages: {passage_count}</div>'
            f"</div>"
        )

    sources_html = "\n".join(source_cards) if source_cards else "<p>No matching sources found in the indexed corpus.</p>"

    # No-match notice
    no_match_notice = ""
    if not results:
        no_match_notice = (
            '<div class="no-match">No matches found — this document does not '
            "appear to overlap with any documents in the indexed corpus.</div>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plagiarism Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.7;
    color: #2c3e50;
    max-width: 960px;
    margin: 0 auto;
    padding: 32px 24px;
    background: #fafbfc;
  }}
  h1 {{
    font-size: 1.6rem;
    margin: 0 0 8px;
    color: #1a1a2e;
  }}
  .header {{
    border-bottom: 2px solid #e1e4e8;
    padding-bottom: 20px;
    margin-bottom: 28px;
  }}
  .severity-banner {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 1.25rem;
    font-weight: 600;
    color: #fff;
    margin-top: 8px;
  }}
  .severity-label {{
    font-size: 0.85rem;
    font-weight: 400;
    opacity: 0.9;
  }}
  .document-text {{
    background: #fff;
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    padding: 28px 32px;
    margin-bottom: 32px;
    overflow-wrap: break-word;
    word-wrap: break-word;
  }}
  .document-text p {{
    margin: 0 0 1em;
    text-align: justify;
  }}
  .document-text p:last-child {{
    margin-bottom: 0;
  }}
  .section-title {{
    font-size: 1.15rem;
    font-weight: 600;
    color: #1a1a2e;
    margin: 28px 0 12px;
  }}
  .sources-section {{
    margin-top: 36px;
    padding-top: 24px;
    border-top: 2px solid #e1e4e8;
  }}
  .sources-explanation {{
    color: #586069;
    font-size: 0.9rem;
    margin-bottom: 16px;
    line-height: 1.5;
  }}
  .source-card {{
    padding: 14px 18px;
    margin-bottom: 10px;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
  }}
  .source-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }}
  .source-badge {{
    color: #fff;
    font-size: 0.75rem;
    font-weight: 700;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .source-meta {{
    font-size: 0.85rem;
    color: #586069;
    margin-left: 34px;
  }}
  .no-match {{
    padding: 20px;
    background: #e8fde8;
    border: 1px solid #27ae60;
    border-radius: 8px;
    color: #27ae60;
    font-weight: 500;
    text-align: center;
  }}
  mark.hl {{
    color: inherit;
    text-decoration: none;
  }}
  .footer {{
    margin-top: 36px;
    padding-top: 16px;
    border-top: 1px solid #e1e4e8;
    font-size: 0.8rem;
    color: #8b949e;
    text-align: center;
  }}
  @media print {{
    body {{ background: #fff; padding: 12px; }}
    .document-text {{ border: none; padding: 0; }}
    mark.hl {{ border-bottom-width: 1px !important; }}
  }}
  @media (max-width: 600px) {{
    body {{ padding: 16px 12px; }}
    .document-text {{ padding: 16px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>Plagiarism Report</h1>
  <div class="severity-banner" style="background:{severity_color}">
    {overall_pct:.1f}%
    <span class="severity-label">{severity_label} similarity</span>
  </div>
</div>

{no_match_notice}

<div class="section-title" id="document-text">Document Text</div>
<div class="document-text">
{doc_body}
</div>

<div class="sources-section" id="sources-section">
  <div class="section-title">Sources</div>
  <p class="sources-explanation">
    The following documents from the indexed corpus contain text that matches
    portions of the submitted document. Each source is color-coded — highlighted
    passages in the text above use the same color as their corresponding source
    below. The similarity percentage indicates how much of the submitted document
    overlaps with each source.
  </p>
  {sources_html}
</div>

<div class="footer">
  Generated by Plagiarism Checker
</div>

</body>
</html>"""

    return html
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yudis/Codes/Personal/plagiarism-checker && uv run pytest tests/test_report.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run all tests to check for regressions**

Run: `cd /Users/yudis/Codes/Personal/plagiarism-checker && uv run pytest tests/ -v --ignore=tests/test_integration.py`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/plagiarism_checker/checker/report.py tests/test_report.py
git commit -m "feat: rewrite HTML report with modern styling, readable text, and sources at bottom"
```

---

### Task 4: Manual verification — generate a sample report

**Files:** None (verification only)

- [ ] **Step 1: Generate a quick sample HTML to visually verify**

Write a small Python script that calls `format_html` with sample data and opens it in a browser:

```bash
cd /Users/yudis/Codes/Personal/plagiarism-checker && uv run python -c "
from plagiarism_checker.checker.report import format_html
from plagiarism_checker.checker.matcher import MatchResult, MatchedPassage

results = [
    MatchResult(document_id=1, title='Analisis Sistem Informasi Akademik', author='Budi Santoso', similarity_pct=18.5, matched_passages=[
        MatchedPassage(submitted_start=0, submitted_end=50, source_start=10, source_end=60),
    ]),
    MatchResult(document_id=2, title='Implementasi Machine Learning', author='Siti Rahayu', similarity_pct=7.2, matched_passages=[
        MatchedPassage(submitted_start=100, submitted_end=140, source_start=200, source_end=240),
    ]),
]

raw_text = '''Sistem informasi akademik merupakan salah satu komponen penting dalam pengelolaan data di perguruan tinggi. Sistem ini berfungsi untuk mengelola data mahasiswa, dosen, mata kuliah, dan nilai akademik secara terintegrasi.

Penggunaan teknologi informasi dalam dunia pendidikan telah mengalami perkembangan yang sangat pesat. Hal ini ditandai dengan semakin banyaknya institusi pendidikan yang mengadopsi sistem informasi berbasis komputer untuk mendukung kegiatan operasional mereka.

Penelitian ini bertujuan untuk menganalisis efektivitas implementasi sistem informasi akademik di lingkungan perguruan tinggi, dengan fokus pada aspek kegunaan, keandalan, dan kepuasan pengguna.'''

cleaned = 'sistem informasi akademik merupakan salah satu komponen penting pengelolaan data perguruan tinggi sistem berfungsi mengelola data mahasiswa dosen mata kuliah nilai akademik terintegrasi penggunaan teknologi informasi dunia pendidikan mengalami perkembangan sangat pesat hal ditandai semakin banyaknya institusi pendidikan mengadopsi sistem informasi berbasis komputer mendukung kegiatan operasional penelitian bertujuan menganalisis efektivitas implementasi sistem informasi akademik lingkungan perguruan tinggi fokus aspek kegunaan keandalan kepuasan pengguna'

from plagiarism_checker.utils.text import build_position_map
mapping = build_position_map(raw_text, {'di', 'dan', 'yang', 'ini', 'untuk', 'dengan', 'secara', 'telah', 'mereka'})
html = format_html(25.7, results, cleaned, raw_text=raw_text, position_map=mapping)
open('report_preview.html', 'w').write(html)
print('Wrote report_preview.html')
"
```

- [ ] **Step 2: Open and visually verify**

```bash
open report_preview.html
```

Check:
- Text wraps properly (no horizontal scrolling)
- Paragraphs are formatted like readable prose
- Highlights are visible with correct colors
- Sources section is at the bottom with explanation
- Severity banner shows correct color/label
- Looks good on narrow screens (resize browser)

- [ ] **Step 3: Clean up**

```bash
rm report_preview.html
```

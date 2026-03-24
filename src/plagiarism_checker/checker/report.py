import json
from plagiarism_checker.checker.matcher import MatchResult


def format_terminal(
    overall_pct: float,
    results: list[MatchResult],
    submitted_text: str,
) -> str:
    lines: list[str] = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  PLAGIARISM CHECK REPORT")
    lines.append(f"{'=' * 60}")
    lines.append(f"\n  Overall Similarity: {overall_pct:.1f}%\n")

    if not results:
        lines.append("  No matches found.\n")
        return "\n".join(lines)

    lines.append(f"  Matched against {len(results)} source(s):\n")

    for i, result in enumerate(results, 1):
        title = result.title or "Unknown"
        author = result.author or "Unknown"
        lines.append(f"  [{i}] {title}")
        lines.append(f"      Author: {author}")
        lines.append(f"      Similarity: {result.similarity_pct:.1f}%")
        lines.append(f"      Matched passages: {len(result.matched_passages)}")

        for j, passage in enumerate(result.matched_passages, 1):
            snippet = submitted_text[passage.submitted_start : passage.submitted_end]
            if len(snippet) > 100:
                snippet = snippet[:100] + "..."
            lines.append(f"        Passage {j}: \"{snippet}\"")
            lines.append(
                f"        (chars {passage.submitted_start}-{passage.submitted_end})"
            )

        lines.append("")

    lines.append(f"{'=' * 60}\n")
    return "\n".join(lines)


def format_json(
    overall_pct: float,
    results: list[MatchResult],
    submitted_text: str,
) -> str:
    data = {
        "overall_similarity_pct": overall_pct,
        "sources": [
            {
                "document_id": r.document_id,
                "title": r.title,
                "author": r.author,
                "similarity_pct": r.similarity_pct,
                "matched_passages": [
                    {
                        "submitted_start": p.submitted_start,
                        "submitted_end": p.submitted_end,
                        "source_start": p.source_start,
                        "source_end": p.source_end,
                        "text": submitted_text[p.submitted_start : p.submitted_end],
                    }
                    for p in r.matched_passages
                ],
            }
            for r in results
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


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

    use_raw = bool(raw_text and position_map)
    display_text = raw_text if use_raw else submitted_text

    highlights: list[tuple[int, int, int]] = []
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

    highlights.sort()

    doc_html_parts: list[str] = []
    pos = 0
    for start, end, src_idx in highlights:
        if start < pos:
            start = pos
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

    highlighted_text = "".join(doc_html_parts)
    paragraphs = highlighted_text.split("\n\n")
    formatted_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if para:
            para = para.replace("\n", "<br>\n")
            formatted_paragraphs.append(f"<p>{para}</p>")
    doc_body = "\n".join(formatted_paragraphs) if formatted_paragraphs else f"<p>{highlighted_text}</p>"

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


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

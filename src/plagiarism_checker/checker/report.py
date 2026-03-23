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
) -> str:
    # Build highlighted text
    highlights: list[tuple[int, int, int]] = []  # (start, end, source_idx)
    for i, result in enumerate(results):
        for p in result.matched_passages:
            highlights.append((p.submitted_start, p.submitted_end, i))

    highlights.sort()

    colors = [
        "#ffcccc", "#ccffcc", "#ccccff", "#ffffcc", "#ffccff",
        "#ccffff", "#ffd9b3", "#d9b3ff", "#b3ffd9", "#ffb3d9",
    ]

    html_parts: list[str] = []
    html_parts.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    html_parts.append("<title>Plagiarism Report</title>")
    html_parts.append("<style>body{font-family:monospace;max-width:900px;margin:0 auto;padding:20px}")
    html_parts.append(".source{margin:10px 0;padding:10px;border:1px solid #ccc;border-radius:4px}")
    html_parts.append("</style></head><body>")
    html_parts.append(f"<h1>Plagiarism Report</h1>")
    html_parts.append(f"<h2>Overall Similarity: {overall_pct:.1f}%</h2>")

    # Source list
    html_parts.append("<h3>Sources</h3>")
    for i, result in enumerate(results):
        color = colors[i % len(colors)]
        html_parts.append(
            f'<div class="source" style="border-left:4px solid {color}">'
            f"<strong>[{i+1}]</strong> {result.title or 'Unknown'} "
            f"— {result.author or 'Unknown'} "
            f"({result.similarity_pct:.1f}%)</div>"
        )

    # Highlighted text
    html_parts.append("<h3>Document Text</h3><pre>")
    pos = 0
    for start, end, src_idx in highlights:
        if start > pos:
            html_parts.append(_html_escape(submitted_text[pos:start]))
        color = colors[src_idx % len(colors)]
        html_parts.append(
            f'<span style="background:{color}" title="Source {src_idx+1}">'
        )
        html_parts.append(_html_escape(submitted_text[start:end]))
        html_parts.append("</span>")
        pos = end
    if pos < len(submitted_text):
        html_parts.append(_html_escape(submitted_text[pos:]))
    html_parts.append("</pre></body></html>")

    return "".join(html_parts)


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

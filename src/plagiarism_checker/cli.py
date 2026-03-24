from pathlib import Path

import typer
from plagiarism_checker.db import get_connection
from plagiarism_checker.models import create_tables

app = typer.Typer(name="plagiarism-checker")


@app.command()
def init_db() -> None:
    """Initialize the database schema."""
    with get_connection() as conn:
        create_tables(conn)
    typer.echo("Database initialized.")


@app.command()
def scrape(
    count: int = typer.Option(200, help="Number of PDFs to download"),
    output: Path = typer.Option(Path("data/corpus"), help="Output directory"),
    oai_url: str = typer.Option(
        "https://eprints.walisongo.ac.id/cgi/oai2",
        help="OAI-PMH endpoint URL",
    ),
) -> None:
    """Scrape Indonesian academic PDFs via OAI-PMH."""
    import logging
    logging.basicConfig(level=logging.INFO)

    from plagiarism_checker.scraper.oai_harvester import harvest_pdf_urls, download_pdfs

    typer.echo(f"Harvesting up to {count} records from {oai_url}...")
    records = harvest_pdf_urls(oai_url=oai_url, max_records=count)
    typer.echo(f"Found {len(records)} records with PDF URLs.")

    if not records:
        typer.echo("No records found. Try a different OAI-PMH endpoint.")
        raise typer.Exit(1)

    typer.echo(f"Downloading to {output}...")
    success, failure = download_pdfs(records, output_dir=output)
    typer.echo(f"Done. Downloaded: {success}, Failed: {failure}")


@app.command()
def index(
    path: Path = typer.Argument(..., help="Directory of PDFs or single PDF to index"),
    no_section_filter: bool = typer.Option(False, help="Disable section filtering"),
    reindex: bool = typer.Option(False, help="Drop all existing data and reindex from scratch"),
) -> None:
    """Index PDF documents into the plagiarism corpus.

    Skips PDFs that are already indexed. Use --reindex to drop all data and start fresh.
    """
    import logging
    logging.basicConfig(level=logging.INFO)

    from plagiarism_checker.db import (
        delete_all_documents,
        get_connection,
        get_indexed_paths,
        insert_document,
        insert_document_text,
        insert_fingerprints,
        update_document_status,
    )
    from plagiarism_checker.extractor.pdf_extractor import extract_text_from_pdf
    from plagiarism_checker.indexer.winnowing import fingerprint_text
    from plagiarism_checker.models import create_tables
    from plagiarism_checker.utils.text import load_stopwords, normalize_text, remove_stopwords

    stopwords = load_stopwords()

    if path.is_file():
        pdf_files = [path]
    elif path.is_dir():
        pdf_files = sorted(path.glob("*.pdf"))
    else:
        typer.echo(f"Path not found: {path}")
        raise typer.Exit(1)

    if not pdf_files:
        typer.echo("No PDF files found.")
        raise typer.Exit(1)

    conn = get_connection()
    create_tables(conn)

    if reindex:
        typer.echo("Dropping all existing index data...")
        delete_all_documents(conn)

    already_indexed = get_indexed_paths(conn)
    new_files = [f for f in pdf_files if str(f) not in already_indexed]

    if not new_files:
        typer.echo(f"All {len(pdf_files)} PDF(s) already indexed. Nothing to do.")
        conn.close()
        return

    typer.echo(f"Indexing {len(new_files)} new PDF(s) ({len(pdf_files) - len(new_files)} already indexed)...")

    indexed = 0
    skipped = 0

    for pdf_path in new_files:
        raw_text = extract_text_from_pdf(pdf_path, section_filter=not no_section_filter)
        if raw_text is None:
            skipped += 1
            continue

        # Load metadata from JSON sidecar if it exists
        meta_path = pdf_path.with_suffix(".json")
        title, author, year, source_url = None, None, None, None
        if meta_path.exists():
            import json
            meta = json.loads(meta_path.read_text())
            title = meta.get("title")
            author = meta.get("creator")
            date_str = meta.get("date", "")
            year = int(date_str[:4]) if len(date_str) >= 4 and date_str[:4].isdigit() else None
            source_url = meta.get("url")

        doc_id = insert_document(
            conn, str(pdf_path), title=title, author=author, year=year, source_url=source_url
        )

        normalized = normalize_text(raw_text)
        cleaned = remove_stopwords(normalized, stopwords)

        if not cleaned.strip():
            update_document_status(conn, doc_id, "unprocessable")
            skipped += 1
            continue

        insert_document_text(conn, doc_id, cleaned)

        fps = fingerprint_text(cleaned)
        if not fps:
            update_document_status(conn, doc_id, "unprocessable")
            skipped += 1
            continue

        insert_fingerprints(conn, doc_id, fps)
        update_document_status(conn, doc_id, "indexed")
        indexed += 1

    conn.close()
    typer.echo(f"Done. Indexed: {indexed}, Skipped: {skipped}")


@app.command()
def check(
    pdf_path: Path = typer.Argument(..., help="Path to the thesis PDF to check"),
    format: str = typer.Option("terminal", help="Output format: terminal, json, html"),
    output: Path | None = typer.Option(None, help="Output file path (prints to stdout if not set)"),
) -> None:
    """Check a thesis PDF for plagiarism against the indexed corpus."""
    import logging
    logging.basicConfig(level=logging.INFO)

    from plagiarism_checker.checker.matcher import check_document
    from plagiarism_checker.checker.report import format_html, format_json, format_terminal
    from plagiarism_checker.db import (
        find_matching_fingerprints,
        get_connection,
        get_document,
    )
    from plagiarism_checker.extractor.pdf_extractor import extract_text_from_pdf
    from plagiarism_checker.indexer.winnowing import fingerprint_text
    from plagiarism_checker.utils.text import load_stopwords, normalize_text, remove_stopwords

    if not pdf_path.exists():
        typer.echo(f"File not found: {pdf_path}")
        raise typer.Exit(1)

    raw_text = extract_text_from_pdf(pdf_path)
    if raw_text is None:
        typer.echo("Could not extract text from PDF.")
        raise typer.Exit(1)

    stopwords = load_stopwords()
    normalized = normalize_text(raw_text)
    cleaned = remove_stopwords(normalized, stopwords)

    if not cleaned.strip():
        typer.echo("No usable text after normalization.")
        raise typer.Exit(1)

    fps = fingerprint_text(cleaned)
    if not fps:
        typer.echo("No fingerprints generated — document too short.")
        raise typer.Exit(1)

    typer.echo(f"Generated {len(fps)} fingerprints. Querying corpus...")

    conn = get_connection()
    hash_values = [h for _, _, h in fps]
    db_matches = find_matching_fingerprints(conn, hash_values)

    typer.echo(f"Found {len(db_matches)} matching fingerprints. Analyzing...")

    def get_doc_info(doc_id: int) -> dict | None:
        return get_document(conn, doc_id)

    overall_pct, results = check_document(fps, cleaned, db_matches, get_doc_info)
    conn.close()

    from plagiarism_checker.utils.text import build_position_map
    position_map = build_position_map(raw_text, stopwords)

    if format == "json":
        report = format_json(overall_pct, results, cleaned)
    elif format == "html":
        report = format_html(overall_pct, results, cleaned, raw_text=raw_text, position_map=position_map)
    else:
        report = format_terminal(overall_pct, results, cleaned)

    if output:
        output.write_text(report)
        typer.echo(f"Report written to {output}")
    else:
        typer.echo(report)

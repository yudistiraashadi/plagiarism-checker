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
) -> None:
    """Index PDF documents into the plagiarism corpus."""
    import logging
    logging.basicConfig(level=logging.INFO)

    from plagiarism_checker.db import (
        get_connection,
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

    typer.echo(f"Indexing {len(pdf_files)} PDF(s)...")

    conn = get_connection()
    create_tables(conn)

    indexed = 0
    skipped = 0

    for pdf_path in pdf_files:
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

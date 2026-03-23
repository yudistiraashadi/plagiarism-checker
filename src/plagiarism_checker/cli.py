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

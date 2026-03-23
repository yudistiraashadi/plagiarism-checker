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

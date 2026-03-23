# Plagiarism Checker

A Turnitin-style plagiarism detection tool for Indonesian university theses. It harvests a corpus of published theses via OAI-PMH, indexes them using the Winnowing algorithm, and produces similarity reports against any submitted PDF.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker and Docker Compose

## Quick Start

```bash
# Clone and setup
cp .env.example .env
# Edit .env if needed (ports, credentials)
docker compose up -d
uv sync
uv run plagiarism-checker init-db
```

## CLI Commands

### `plagiarism-checker scrape`

Download PDF theses from an OAI-PMH repository to build a test corpus.

```bash
uv run plagiarism-checker scrape [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--count N` | 200 | Number of PDFs to download |
| `--output DIR` | `data/corpus` | Directory to save downloaded PDFs |
| `--oai-url URL` | _(from .env)_ | OAI-PMH endpoint URL |

### `plagiarism-checker index PATH`

Index a directory of PDFs into the corpus database.

```bash
uv run plagiarism-checker index PATH [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `PATH` | _(required)_ | Directory containing PDF files to index |
| `--no-section-filter` | off | Disable filtering to thesis body sections |

### `plagiarism-checker check FILE`

Check a thesis PDF for plagiarism against the indexed corpus.

```bash
uv run plagiarism-checker check FILE [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `FILE` | _(required)_ | PDF file to check |
| `--format` | `terminal` | Output format: `terminal`, `json`, or `html` |
| `--output FILE` | _(stdout)_ | Write report to a file instead of stdout |

### `plagiarism-checker init-db`

Initialize the database schema. Run this once after `docker compose up -d`.

```bash
uv run plagiarism-checker init-db
```

## Configuration

All configuration is handled through a `.env` file. Copy `.env.example` to get started:

```bash
cp .env.example .env
```

The `.env` file is gitignored and will not be committed.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `plagiarism` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `plagiarism` | PostgreSQL password |
| `POSTGRES_DB` | `plagiarism_checker` | PostgreSQL database name |
| `POSTGRES_PORT` | `5432` | Host port exposed for PostgreSQL |
| `PGBOUNCER_PORT` | `6432` | Host port exposed for PgBouncer |
| `DATABASE_URL` | `postgresql://plagiarism:plagiarism@localhost:6432/plagiarism_checker` | Connection string used by the app (points to PgBouncer) |

The app connects through PgBouncer rather than directly to PostgreSQL for connection pooling.

## Development

```bash
uv sync
uv run pytest
```

## Docker Deployment

By default, only the database services (`postgres` and `pgbouncer`) run in Docker, while the app runs locally via `uv`. To run the full stack in Docker, uncomment the `app` service in `docker-compose.yml`:

```yaml
# Uncomment to run the app in Docker
app:
  build: .
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@pgbouncer:5432/${POSTGRES_DB}
  depends_on:
    - pgbouncer
  volumes:
    - ./data:/app/data
```

Alternatively, build and run the image manually:

```bash
docker build -t plagiarism-checker .
docker run --env-file .env plagiarism-checker check thesis.pdf
```

## How It Works

The tool uses the **Winnowing** algorithm for document fingerprinting. Each document is broken into overlapping k-grams (character n-grams), hashed, and then a rolling minimum window selects a representative subset of hashes as the document's fingerprint. Similarity between two documents is measured by the proportion of fingerprint hashes they share (Jaccard-style), making the comparison robust to minor rewording and formatting differences.

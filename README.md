# Plagiarism Checker

A Turnitin-style plagiarism detection tool for Indonesian university theses. It harvests a corpus of published theses via OAI-PMH, indexes them using the Winnowing algorithm, and produces similarity reports against any submitted PDF.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker and Docker Compose

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd plagiarism-checker
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` if you need to change ports or credentials. The defaults work out of the box:

```env
POSTGRES_USER=plagiarism
POSTGRES_PASSWORD=plagiarism
POSTGRES_DB=plagiarism_checker
POSTGRES_PORT=5432
PGBOUNCER_PORT=6432
DATABASE_URL=postgresql://plagiarism:plagiarism@localhost:6432/plagiarism_checker
```

### 3. Start the database

```bash
docker compose up -d
```

This starts PostgreSQL and PgBouncer. The app connects through PgBouncer (port 6432) for connection pooling.

### 4. Install Python dependencies

```bash
uv sync
```

### 5. Initialize the database schema

```bash
uv run plagiarism-checker init-db
```

## Usage

The workflow has three steps: **scrape** a corpus of PDFs, **index** them into the database, then **check** a document against the corpus.

### Step 1: Scrape PDFs from an OAI-PMH repository

Download published theses to build a reference corpus:

```bash
uv run plagiarism-checker scrape
```

This downloads up to 200 PDFs (with metadata) into `data/corpus/`.

| Option | Default | Description |
|---|---|---|
| `--count N` | `200` | Number of PDFs to download |
| `--output DIR` | `data/corpus` | Directory to save downloaded PDFs |
| `--oai-url URL` | `https://eprints.walisongo.ac.id/cgi/oai2` | OAI-PMH endpoint URL |

### Step 2: Index the corpus

Index the downloaded PDFs so they can be compared against:

```bash
uv run plagiarism-checker index data/corpus
```

This extracts text from each PDF, normalizes it, generates Winnowing fingerprints, and stores everything in the database. PDFs that are already indexed are automatically skipped.

| Option | Default | Description |
|---|---|---|
| `PATH` | _(required)_ | Directory of PDFs or a single PDF file |
| `--no-section-filter` | off | Include all sections (by default, bibliography, table of contents, and appendices are filtered out) |
| `--reindex` | off | Drop all existing data and reindex from scratch |

### Step 3: Check a document for plagiarism

```bash
uv run plagiarism-checker check thesis.pdf
```

This compares the submitted PDF against the indexed corpus and prints a similarity report.

**Output formats:**

```bash
# Terminal output (default)
uv run plagiarism-checker check thesis.pdf

# HTML report (recommended — shows highlighted text with color-coded sources)
uv run plagiarism-checker check thesis.pdf --format html --output report.html

# JSON output (for programmatic use)
uv run plagiarism-checker check thesis.pdf --format json --output report.json
```

| Option | Default | Description |
|---|---|---|
| `FILE` | _(required)_ | PDF file to check |
| `--format` | `terminal` | Output format: `terminal`, `json`, or `html` |
| `--output FILE` | _(stdout)_ | Write report to a file instead of printing to terminal |

The HTML report displays the original document text with matched passages highlighted in color. Each color corresponds to a source document listed at the bottom of the report. A severity banner (Low / Moderate / Significant / High) indicates the overall similarity level.

## Configuration

All configuration is through the `.env` file. The `.env` file is gitignored and will not be committed.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `plagiarism` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `plagiarism` | PostgreSQL password |
| `POSTGRES_DB` | `plagiarism_checker` | PostgreSQL database name |
| `POSTGRES_PORT` | `5432` | Host port for PostgreSQL |
| `PGBOUNCER_PORT` | `6432` | Host port for PgBouncer |
| `DATABASE_URL` | `postgresql://plagiarism:plagiarism@localhost:6432/plagiarism_checker` | Connection string (points to PgBouncer) |

## Development

```bash
uv sync
uv run pytest
```

Integration tests require a running database:

```bash
docker compose up -d
uv run pytest tests/test_integration.py -v
```

## Docker Deployment

By default, only the database services run in Docker while the app runs locally via `uv`. To run the full stack in Docker, uncomment the `app` service in `docker-compose.yml`:

```yaml
app:
  build: .
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@pgbouncer:5432/${POSTGRES_DB}
  depends_on:
    - pgbouncer
  volumes:
    - ./data:/app/data
```

Or build and run manually:

```bash
docker build -t plagiarism-checker .
docker run --env-file .env plagiarism-checker check thesis.pdf
```

## How It Works

The tool uses the **Winnowing** algorithm for document fingerprinting. Each document is broken into overlapping word n-grams, hashed with FNV-1a, and then a rolling minimum window selects representative hashes as the document's fingerprint. Similarity is measured by the proportion of matching fingerprints between the submitted document and each corpus document. Consecutive matching fingerprints are grouped into passages and reported with their positions in both documents.

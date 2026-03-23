# Plagiarism Checker for Indonesian University Theses

## Overview

A Turnitin-style plagiarism detection system for Indonesian-language (Bahasa Indonesia) university theses. The system receives a new thesis PDF, compares it against a corpus of previously published theses, and produces a similarity report with overall percentage, per-source breakdown, and matched passage highlighting.

The tool reports similarity and lets the human reviewer judge — it does not make pass/fail decisions.

## Scale

- Target corpus: ~50,000 thesis documents (PDF)
- Test corpus: ~200 PDFs scraped from open-access Indonesian repositories

## Detection Approach: N-gram Fingerprinting (Winnowing)

The system uses the Winnowing algorithm for fingerprint-based text matching. This detects near-exact matches — copy-paste with minor edits — but does not flag heavy paraphrasing. This mirrors Turnitin's behavior.

### Algorithm Parameters

- **N-gram size:** 7 words — large enough to avoid false positives from common Indonesian academic phrases
- **Winnowing window size:** 4 — standard balance of coverage vs. fingerprint density
- **Minimum match threshold:** 3 consecutive aligned fingerprints (~10+ matching words) — filters out coincidental short phrase matches
- **Hash function:** 64-bit FNV-1a — fast, well-distributed, and 64-bit width avoids collision issues at 500M+ fingerprints. No text-level collision verification needed at this hash size.

### Similarity Percentage Calculation

- **Overall similarity:** (number of matched characters in the submitted document / total characters in submitted document) × 100. Character-based, relative to the submitted document's length.
- **Per-source similarity:** (number of matched characters attributed to source X / total characters in submitted document) × 100.
- Overlapping matches from multiple sources are counted once for the overall score but attributed to each source individually in the per-source breakdown.

### What Gets Detected

- Copy-paste with 1-2 word substitutions: **detected**
- Heavily rewritten/paraphrased passages: **not flagged**
- Common academic phrases (e.g., "dalam penelitian ini"): **not flagged**

## System Components

### 1. PDF Scraper (Test Corpus Builder)

**Purpose:** Download ~200 Indonesian-language academic PDFs for testing.

**Source:** Walisongo Repository (eprints.walisongo.ac.id) via OAI-PMH protocol. This repository has 27,450+ items, all open access with full-text PDFs. The EPrints/OAI-PMH approach is reusable across other Indonesian university repositories.

**Backup sources (same OAI-PMH approach):**
- UIN Sunan Gunung Djati Bandung (digilib.uinsgd.ac.id)
- UIN Sunan Kalijaga Yogyakarta (digilib.uin-suka.ac.id)

**Features:**
- Configurable target download count (default 200)
- Resume capability — skips already-downloaded files
- Metadata stored as JSON sidecar per PDF (title, author, year, source URL)
- Rate limiting (1-2 second delays between requests)
- Respects robots.txt

### 2. Text Extractor

**Purpose:** Extract and normalize text from thesis PDFs.

**Pipeline:**
1. Extract raw text from PDF using pymupdf. If extraction yields no text (scanned/image PDF), log a warning and skip the document — OCR is out of scope.
2. Normalize: lowercase, strip punctuation, remove extra whitespace
3. Remove non-content sections (cover page, table of contents, bibliography, appendices) — best-effort heuristic based on heading detection, can be disabled via `--no-section-filter` CLI flag
4. Remove Indonesian stopwords (source: Sastrawi project's Indonesian stopword list)
5. Store cleaned text in PostgreSQL alongside document metadata

### 3. Fingerprint Indexer

**Purpose:** Process documents into Winnowing fingerprints and store them for fast lookup.

**Process:**
1. Take cleaned text, generate 7-word sliding window n-grams
2. Hash each n-gram using a rolling hash
3. Apply Winnowing algorithm to select representative fingerprints
4. Store fingerprints in PostgreSQL, each linked to source document + character offset position

**Indexing a new document into the corpus:** extract text -> generate fingerprints -> insert into DB. For the full 50k corpus this is a one-time batch job.

### 4. Plagiarism Checker & Report Generator

**Checking process:**
1. Receive new thesis PDF
2. Extract and normalize text (same pipeline as indexing)
3. Generate fingerprints for the new document
4. Query DB for matching fingerprints across the corpus
5. Group matches by source document, calculate overlap

**Report output:**
- Overall similarity percentage (% of new thesis text matching existing documents)
- Per-source breakdown (list of matched source documents with individual similarity %)
- Matched passages (matching text segments with positions in both documents)
- Output formats: terminal (colored text), JSON (machine-readable), HTML (for future web UI)

## Database Schema

PostgreSQL, running in Docker.

### Tables

**documents**
- id (PK)
- title
- author
- year
- source_url
- file_path
- created_at

**document_text**
- id (PK)
- document_id (FK -> documents)
- full_text
- section_offsets

**fingerprints**
- id (PK)
- document_id (FK -> documents)
- hash_value (indexed)
- position_start
- position_end

Index on `fingerprints.hash_value` for fast lookup during checking.

## CLI Interface

Built with Typer.

```bash
# Scrape test PDFs
plagiarism-checker scrape --count 200

# Index PDFs into the corpus
plagiarism-checker index ./corpus/

# Check a new thesis
plagiarism-checker check ./new-thesis.pdf

# Check with specific output format
plagiarism-checker check ./new-thesis.pdf --format html --output report.html
```

## Project Structure

```
plagiarism-checker/
├── pyproject.toml              # uv project config
├── README.md                   # Setup & usage instructions (uv, Docker, CLI)
├── Dockerfile
├── docker-compose.yml          # PostgreSQL + app
├── src/
│   └── plagiarism_checker/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI entrypoint
│       ├── scraper/
│       │   ├── __init__.py
│       │   └── oai_harvester.py  # OAI-PMH harvester for EPrints repos
│       ├── extractor/
│       │   ├── __init__.py
│       │   └── pdf_extractor.py  # PDF text extraction + normalization
│       ├── indexer/
│       │   ├── __init__.py
│       │   ├── winnowing.py      # Winnowing algorithm implementation
│       │   └── db.py             # Database operations for fingerprints
│       ├── checker/
│       │   ├── __init__.py
│       │   ├── matcher.py        # Fingerprint matching logic
│       │   └── report.py         # Report generation (terminal, JSON, HTML)
│       └── config.py            # Settings (DB connection, algorithm params)
├── tests/
├── data/
│   └── stopwords_id.txt        # Indonesian stopwords
└── docs/
```

## Tech Stack

- **Language:** Python
- **Package manager:** uv
- **CLI framework:** Typer
- **PDF extraction:** pymupdf
- **OAI-PMH harvesting:** sickle
- **Database:** PostgreSQL (Docker container)
- **DB driver:** psycopg
- **HTTP client:** httpx

## Infrastructure

- `docker-compose.yml` runs PostgreSQL for development
- App runs locally via `uv run` during development
- Full Docker deployment (app + DB) available for production
- README.md documents setup with uv, Docker, and CLI usage

## Error Handling

- **PDF extraction fails (corrupted/scanned):** Log warning with filename, skip document, continue batch. Report skipped count at end.
- **OAI-PMH/download errors:** Retry up to 3 times with exponential backoff. If still failing, skip and log. Scraper reports success/failure counts at completion.
- **Database unreachable:** Fail immediately with clear error message — no silent data loss.
- **Document yields zero fingerprints:** Log warning, store document metadata but mark as "unprocessable" in DB.

## Testing Strategy

- **Unit tests:** Winnowing algorithm with known inputs producing expected fingerprints. Text normalization edge cases (empty text, non-Indonesian characters, mixed content).
- **Integration test:** Small corpus of 5 documents where one contains a known copied passage from another. Verify the checker detects the match and reports correct similarity percentage.
- **Test data:** Fixture files in `tests/fixtures/` — small PDFs and pre-extracted text samples.

## Out of Scope

- Web UI (future enhancement)
- Semantic/paraphrase detection
- Multi-language support
- OCR for scanned/image PDFs
- Pass/fail verdicts — the tool reports, the human decides

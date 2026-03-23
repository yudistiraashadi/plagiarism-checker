# Plagiarism Checker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Turnitin-style plagiarism detection CLI for Indonesian university theses using Winnowing fingerprinting against a PostgreSQL-backed corpus.

**Architecture:** Four-component pipeline — PDF scraper harvests test corpus via OAI-PMH, text extractor normalizes PDF content, fingerprint indexer applies Winnowing algorithm and stores hashes in PostgreSQL (via PgBouncer), and the checker queries the index to produce similarity reports.

**Tech Stack:** Python, uv, Typer, pymupdf, sickle, psycopg, httpx, PostgreSQL, PgBouncer, Docker

**Spec:** `docs/superpowers/specs/2026-03-23-plagiarism-checker-design.md`

---

## File Structure

```
plagiarism-checker/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── src/
│   └── plagiarism_checker/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── db.py                    # Shared DB connection management
│       ├── models.py                # SQL schema creation
│       ├── scraper/
│       │   ├── __init__.py
│       │   └── oai_harvester.py
│       ├── extractor/
│       │   ├── __init__.py
│       │   └── pdf_extractor.py
│       ├── indexer/
│       │   ├── __init__.py
│       │   └── winnowing.py
│       ├── checker/
│       │   ├── __init__.py
│       │   ├── matcher.py
│       │   └── report.py
│       └── utils/
│           ├── __init__.py
│           └── text.py              # Shared text normalization utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── sample_short.pdf
│   │   └── sample_indonesian.txt
│   ├── test_winnowing.py
│   ├── test_text.py
│   ├── test_pdf_extractor.py
│   ├── test_matcher.py
│   └── test_integration.py
├── data/
│   └── stopwords_id.txt
└── docs/
```

**Key design decisions:**
- `db.py` is shared (both indexer and checker need DB access) rather than living under `indexer/`
- `models.py` owns schema creation — single source of truth for table definitions
- `utils/text.py` holds normalization logic shared by extractor and checker
- Winnowing is a pure function module with no DB dependency — easy to test

---

### Task 1: Project Scaffolding & Infrastructure

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `docker-compose.yml`
- Create: `src/plagiarism_checker/__init__.py`
- Create: `src/plagiarism_checker/config.py`
- Create: `README.md`

- [ ] **Step 1: Initialize uv project**

```bash
cd /Users/yudis/Codes/Personal/plagiarism-checker
uv init --lib --name plagiarism-checker
```

This creates `pyproject.toml` and `src/plagiarism_checker/__init__.py`.

- [ ] **Step 2: Edit pyproject.toml with dependencies and CLI entrypoint**

```toml
[project]
name = "plagiarism-checker"
version = "0.1.0"
description = "Turnitin-style plagiarism detection for Indonesian university theses"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.15",
    "pymupdf>=1.25",
    "sickle>=0.7",
    "psycopg[binary]>=3.2",
    "httpx>=0.28",
    "python-dotenv>=1.1",
    "rich>=14",
]

[project.scripts]
plagiarism-checker = "plagiarism_checker.cli:app"

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-cov>=6",
]
```

- [ ] **Step 3: Create .env.example**

```env
# Database
POSTGRES_USER=plagiarism
POSTGRES_PASSWORD=plagiarism
POSTGRES_DB=plagiarism_checker
POSTGRES_PORT=5432

# PgBouncer
PGBOUNCER_PORT=6432

# App connects to PgBouncer, not directly to PostgreSQL
DATABASE_URL=postgresql://plagiarism:plagiarism@localhost:6432/plagiarism_checker
```

- [ ] **Step 4: Copy .env.example to .env**

```bash
cp .env.example .env
```

- [ ] **Step 5: Create .gitignore**

```gitignore
__pycache__/
*.pyc
.env
*.egg-info/
dist/
.venv/
data/corpus/
*.pdf
!tests/fixtures/*.pdf
```

- [ ] **Step 6: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-plagiarism}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-plagiarism}
      POSTGRES_DB: ${POSTGRES_DB:-plagiarism_checker}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-plagiarism}"]
      interval: 5s
      timeout: 3s
      retries: 5

  pgbouncer:
    image: edoburu/pgbouncer:1.24.0
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-plagiarism}:${POSTGRES_PASSWORD:-plagiarism}@postgres:5432/${POSTGRES_DB:-plagiarism_checker}
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 20
    ports:
      - "${PGBOUNCER_PORT:-6432}:5432"
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 7: Create config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://plagiarism:plagiarism@localhost:6432/plagiarism_checker",
)

# Winnowing parameters
NGRAM_SIZE = 7
WINDOW_SIZE = 4
MIN_MATCH_LENGTH = 3  # minimum consecutive fingerprint matches
```

- [ ] **Step 8: Create README.md**

Write a README covering:
- Project description (1-2 sentences)
- Prerequisites (Python 3.12+, uv, Docker)
- Setup steps: `cp .env.example .env`, `docker compose up -d`, `uv sync`
- CLI usage: `uv run plagiarism-checker scrape`, `index`, `check`
- Development: `uv run pytest`

- [ ] **Step 9: Install dependencies**

```bash
uv sync
```

- [ ] **Step 10: Start Docker services and verify**

```bash
docker compose up -d
docker compose ps
```

Verify both `postgres` and `pgbouncer` are running and healthy.

- [ ] **Step 11: Commit**

```bash
git add pyproject.toml .env.example .gitignore docker-compose.yml \
  src/plagiarism_checker/__init__.py src/plagiarism_checker/config.py \
  README.md uv.lock
git commit -m "feat: project scaffolding with uv, Docker, PgBouncer"
```

---

### Task 2: Database Layer & Schema

**Files:**
- Create: `src/plagiarism_checker/db.py`
- Create: `src/plagiarism_checker/models.py`
- Create: `src/plagiarism_checker/cli.py` (minimal — just `init-db` command)

- [ ] **Step 1: Create db.py — connection management**

```python
import psycopg
from plagiarism_checker.config import DATABASE_URL


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)
```

- [ ] **Step 2: Create models.py — schema creation**

```python
import psycopg


def create_tables(conn: psycopg.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            title TEXT,
            author TEXT,
            year INTEGER,
            source_url TEXT,
            file_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_text (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            full_text TEXT NOT NULL,
            char_count INTEGER NOT NULL DEFAULT 0,
            section_offsets JSONB
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            hash_value BIGINT NOT NULL,
            position_start INTEGER NOT NULL,
            position_end INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fingerprints_hash
        ON fingerprints (hash_value)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fingerprints_document
        ON fingerprints (document_id)
    """)
    conn.commit()
```

- [ ] **Step 3: Create minimal cli.py with init-db command**

```python
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
```

- [ ] **Step 4: Verify CLI and DB connection work**

```bash
uv run plagiarism-checker init-db
```

Expected: "Database initialized." printed, tables created in PostgreSQL.

- [ ] **Step 5: Commit**

```bash
git add src/plagiarism_checker/db.py src/plagiarism_checker/models.py \
  src/plagiarism_checker/cli.py
git commit -m "feat: database layer with schema and init-db command"
```

---

### Task 3: Text Normalization Utilities

**Files:**
- Create: `src/plagiarism_checker/utils/__init__.py`
- Create: `src/plagiarism_checker/utils/text.py`
- Create: `data/stopwords_id.txt`
- Create: `tests/__init__.py`
- Create: `tests/test_text.py`

- [ ] **Step 1: Download Indonesian stopwords**

Download the Sastrawi stopword list:

```bash
curl -sL https://raw.githubusercontent.com/sastrawi/sastrawi/master/data/stopword.txt \
  -o data/stopwords_id.txt
```

- [ ] **Step 2: Write failing tests for text normalization**

```python
# tests/test_text.py
from plagiarism_checker.utils.text import normalize_text, remove_stopwords, load_stopwords


def test_normalize_lowercases():
    assert normalize_text("Hello WORLD") == "hello world"


def test_normalize_strips_punctuation():
    assert normalize_text("hello, world!") == "hello world"


def test_normalize_collapses_whitespace():
    assert normalize_text("hello   \n  world") == "hello world"


def test_normalize_strips_numbers():
    assert normalize_text("bab 1 pendahuluan") == "bab pendahuluan"


def test_remove_stopwords():
    stopwords = {"yang", "dan", "di", "ini"}
    result = remove_stopwords("penelitian ini dilakukan di kampus", stopwords)
    assert result == "penelitian dilakukan kampus"


def test_load_stopwords_returns_set():
    stopwords = load_stopwords()
    assert isinstance(stopwords, set)
    assert len(stopwords) > 0
    assert "yang" in stopwords
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_text.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement text.py**

```python
# src/plagiarism_checker/utils/text.py
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_STOPWORDS_PATH = _PROJECT_ROOT / "data" / "stopwords_id.txt"


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def remove_stopwords(text: str, stopwords: set[str]) -> str:
    words = text.split()
    return " ".join(w for w in words if w not in stopwords)


def load_stopwords(path: Path | None = None) -> set[str]:
    p = path or _STOPWORDS_PATH
    return set(p.read_text().splitlines())
```

- [ ] **Step 5: Create utils/__init__.py**

Empty file.

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/test_text.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/plagiarism_checker/utils/ data/stopwords_id.txt tests/test_text.py tests/__init__.py
git commit -m "feat: text normalization with Indonesian stopword removal"
```

---

### Task 4: Winnowing Algorithm

**Files:**
- Create: `src/plagiarism_checker/indexer/__init__.py`
- Create: `src/plagiarism_checker/indexer/winnowing.py`
- Create: `tests/test_winnowing.py`

- [ ] **Step 1: Write failing tests for winnowing**

```python
# tests/test_winnowing.py
from plagiarism_checker.indexer.winnowing import (
    fnv1a_64,
    generate_ngrams,
    winnow,
    fingerprint_text,
)


def test_fnv1a_64_deterministic():
    h1 = fnv1a_64("hello world")
    h2 = fnv1a_64("hello world")
    assert h1 == h2


def test_fnv1a_64_different_inputs():
    h1 = fnv1a_64("hello")
    h2 = fnv1a_64("world")
    assert h1 != h2


def test_generate_ngrams_basic():
    words = "a b c d e f g h".split()
    ngrams = generate_ngrams(words, n=3)
    assert ngrams == [
        (0, "a b c"),
        (1, "b c d"),
        (2, "c d e"),
        (3, "d e f"),
        (4, "e f g"),
        (5, "f g h"),
    ]


def test_generate_ngrams_too_short():
    words = "a b".split()
    ngrams = generate_ngrams(words, n=3)
    assert ngrams == []


def test_winnow_selects_minimum_per_window():
    # With known hashes and window_size=4, winnow should select
    # the minimum hash in each window
    hashes = [(i, h) for i, h in enumerate([10, 5, 8, 3, 9, 7, 2, 6])]
    result = winnow(hashes, window_size=4)
    # Each window picks its minimum; duplicates removed
    positions = [pos for pos, _ in result]
    # Position 3 (hash=3) and position 6 (hash=2) should be selected
    assert 3 in positions
    assert 6 in positions


def test_fingerprint_text_returns_positions_and_hashes():
    text = "satu dua tiga empat lima enam tujuh delapan sembilan sepuluh"
    fps = fingerprint_text(text, ngram_size=3, window_size=2)
    assert len(fps) > 0
    for pos_start, pos_end, hash_val in fps:
        assert isinstance(pos_start, int)
        assert isinstance(pos_end, int)
        assert isinstance(hash_val, int)
        assert pos_end > pos_start


def test_fingerprint_text_empty():
    fps = fingerprint_text("", ngram_size=7, window_size=4)
    assert fps == []


def test_fingerprint_text_deterministic():
    text = "penelitian ini bertujuan untuk mengetahui pengaruh variabel terhadap hasil"
    fps1 = fingerprint_text(text)
    fps2 = fingerprint_text(text)
    assert fps1 == fps2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_winnowing.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement winnowing.py**

```python
# src/plagiarism_checker/indexer/winnowing.py
from plagiarism_checker.config import NGRAM_SIZE, WINDOW_SIZE

FNV1A_64_OFFSET = 14695981039346656037
FNV1A_64_PRIME = 1099511628211
FNV1A_64_MOD = 2**64


def fnv1a_64(text: str) -> int:
    h = FNV1A_64_OFFSET
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * FNV1A_64_PRIME) % FNV1A_64_MOD
    return h


def generate_ngrams(words: list[str], n: int = NGRAM_SIZE) -> list[tuple[int, str]]:
    if len(words) < n:
        return []
    return [(i, " ".join(words[i : i + n])) for i in range(len(words) - n + 1)]


def winnow(
    hashes: list[tuple[int, int]], window_size: int = WINDOW_SIZE
) -> list[tuple[int, int]]:
    """Select fingerprints using the Winnowing algorithm.

    Args:
        hashes: list of (position, hash_value) pairs
        window_size: sliding window size

    Returns:
        list of (position, hash_value) selected fingerprints
    """
    if len(hashes) < window_size:
        return list(hashes)

    selected: list[tuple[int, int]] = []
    prev_pos = -1

    for i in range(len(hashes) - window_size + 1):
        window = hashes[i : i + window_size]
        min_entry = min(window, key=lambda x: (x[1], x[0]))
        if min_entry[0] != prev_pos:
            selected.append(min_entry)
            prev_pos = min_entry[0]

    return selected


def fingerprint_text(
    text: str,
    ngram_size: int = NGRAM_SIZE,
    window_size: int = WINDOW_SIZE,
) -> list[tuple[int, int, int]]:
    """Generate Winnowing fingerprints for a text.

    Returns:
        list of (position_start, position_end, hash_value) tuples.
        Positions are character offsets in the original text.
    """
    words = text.split()
    if not words:
        return []

    ngrams = generate_ngrams(words, n=ngram_size)
    if not ngrams:
        return []

    hashes = [(idx, fnv1a_64(gram)) for idx, gram in ngrams]
    selected = winnow(hashes, window_size=window_size)

    # Convert word positions to character offsets
    # Build a map of word index -> (char_start, char_end)
    char_positions: list[tuple[int, int]] = []
    offset = 0
    for word in words:
        idx = text.index(word, offset)
        char_positions.append((idx, idx + len(word)))
        offset = idx + len(word)

    result: list[tuple[int, int, int]] = []
    for word_idx, hash_val in selected:
        char_start = char_positions[word_idx][0]
        end_word_idx = min(word_idx + ngram_size - 1, len(words) - 1)
        char_end = char_positions[end_word_idx][1]
        result.append((char_start, char_end, hash_val))

    return result
```

- [ ] **Step 4: Create indexer/__init__.py**

Empty file.

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_winnowing.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/plagiarism_checker/indexer/ tests/test_winnowing.py
git commit -m "feat: Winnowing algorithm with FNV-1a hashing"
```

---

### Task 5: PDF Text Extraction

**Files:**
- Create: `src/plagiarism_checker/extractor/__init__.py`
- Create: `src/plagiarism_checker/extractor/pdf_extractor.py`
- Create: `tests/test_pdf_extractor.py`
- Create: `tests/fixtures/` (test PDF)

- [ ] **Step 1: Create a test PDF fixture**

```python
# Run once to generate a test fixture
import fitz
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), "BAB I\nPENDAHULUAN\n\nPenelitian ini bertujuan untuk mengetahui pengaruh variabel independen terhadap variabel dependen dalam konteks pendidikan tinggi di Indonesia.", fontsize=12)
page = doc.new_page()
page.insert_text((72, 72), "BAB II\nTINJAUAN PUSTAKA\n\nMenurut penelitian sebelumnya, faktor utama yang mempengaruhi hasil belajar adalah motivasi dan lingkungan belajar mahasiswa.", fontsize=12)
doc.save("tests/fixtures/sample_short.pdf")
doc.close()
```

Run this as a one-off script to create the fixture.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_pdf_extractor.py
from pathlib import Path
from plagiarism_checker.extractor.pdf_extractor import extract_text_from_pdf

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_returns_text():
    text = extract_text_from_pdf(FIXTURES / "sample_short.pdf")
    assert len(text) > 0


def test_extract_contains_content():
    text = extract_text_from_pdf(FIXTURES / "sample_short.pdf")
    assert "penelitian" in text.lower()


def test_extract_nonexistent_file():
    text = extract_text_from_pdf(FIXTURES / "nonexistent.pdf")
    assert text is None


def test_extract_returns_none_for_empty(tmp_path):
    # Create an empty PDF (no text content)
    import fitz
    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "empty.pdf"
    doc.save(str(path))
    doc.close()
    text = extract_text_from_pdf(path)
    assert text is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_pdf_extractor.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement pdf_extractor.py**

```python
# src/plagiarism_checker/extractor/pdf_extractor.py
import logging
import re
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)

# Headings that mark non-content sections to filter out
_SKIP_SECTIONS = re.compile(
    r"^(daftar\s+isi|daftar\s+pustaka|daftar\s+tabel|daftar\s+gambar|"
    r"daftar\s+lampiran|lampiran|bibliografi|referensi|kata\s+pengantar|"
    r"table\s+of\s+contents|bibliography|references|appendix)\b",
    re.IGNORECASE,
)


def extract_text_from_pdf(
    path: Path, section_filter: bool = True
) -> str | None:
    """Extract text from a PDF file.

    Args:
        path: Path to the PDF file.
        section_filter: If True, attempt to remove non-content sections
            (table of contents, bibliography, appendices, etc.)

    Returns None if the file doesn't exist or contains no extractable text.
    """
    if not path.exists():
        logger.warning("File not found: %s", path)
        return None

    try:
        doc = fitz.open(str(path))
    except Exception:
        logger.warning("Failed to open PDF: %s", path)
        return None

    text_parts: list[str] = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        logger.warning("No text extracted (scanned/image PDF?): %s", path)
        return None

    if section_filter:
        full_text = _filter_sections(full_text)
        if not full_text.strip():
            logger.warning("No text remaining after section filtering: %s", path)
            return None

    return full_text


def _filter_sections(text: str) -> str:
    """Remove non-content sections based on heading detection."""
    lines = text.split("\n")
    result: list[str] = []
    skipping = False

    for line in lines:
        stripped = line.strip()
        # Check if this line is a heading that starts a skip section
        if _SKIP_SECTIONS.match(stripped):
            skipping = True
            continue
        # Check if we hit a new BAB heading (content resumes)
        if re.match(r"^BAB\s+[IVXLCDM\d]+", stripped, re.IGNORECASE):
            skipping = False
        if not skipping:
            result.append(line)

    return "\n".join(result)
```

- [ ] **Step 5: Create extractor/__init__.py**

Empty file.

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/test_pdf_extractor.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/plagiarism_checker/extractor/ tests/test_pdf_extractor.py tests/fixtures/
git commit -m "feat: PDF text extraction with pymupdf"
```

---

### Task 6: Database Operations for Indexing

**Files:**
- Create: `src/plagiarism_checker/indexer/db.py` (rename planned `db.py` from root — this is indexing-specific DB ops, shared `db.py` stays at package root for connection)
- Rename: move the shared `get_connection` to `src/plagiarism_checker/db.py` (already done in Task 2)

Actually, keeping it simple: `src/plagiarism_checker/db.py` handles connection + all DB operations.

**Files:**
- Modify: `src/plagiarism_checker/db.py`

- [ ] **Step 1: Add document and fingerprint DB operations to db.py**

Add these functions to the existing `db.py`:

```python
def insert_document(
    conn: psycopg.Connection,
    file_path: str,
    title: str | None = None,
    author: str | None = None,
    year: int | None = None,
    source_url: str | None = None,
) -> int:
    """Insert a document record and return its ID."""
    row = conn.execute(
        """
        INSERT INTO documents (title, author, year, source_url, file_path, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        RETURNING id
        """,
        (title, author, year, source_url, file_path),
    ).fetchone()
    conn.commit()
    return row[0]


def insert_document_text(
    conn: psycopg.Connection, document_id: int, full_text: str
) -> None:
    conn.execute(
        """
        INSERT INTO document_text (document_id, full_text, char_count)
        VALUES (%s, %s, %s)
        """,
        (document_id, full_text, len(full_text)),
    )
    conn.commit()


def insert_fingerprints(
    conn: psycopg.Connection,
    document_id: int,
    fingerprints: list[tuple[int, int, int]],
) -> None:
    """Batch insert fingerprints. Each tuple is (pos_start, pos_end, hash_value)."""
    with conn.cursor() as cur:
        with cur.copy(
            "COPY fingerprints (document_id, hash_value, position_start, position_end) FROM STDIN"
        ) as copy:
            for pos_start, pos_end, hash_val in fingerprints:
                copy.write_row((document_id, hash_val, pos_start, pos_end))
    conn.commit()


def update_document_status(
    conn: psycopg.Connection, document_id: int, status: str
) -> None:
    conn.execute(
        "UPDATE documents SET status = %s WHERE id = %s",
        (status, document_id),
    )
    conn.commit()


def find_matching_fingerprints(
    conn: psycopg.Connection, hash_values: list[int]
) -> list[tuple[int, int, int, int]]:
    """Find fingerprints matching any of the given hashes.

    Returns list of (document_id, hash_value, position_start, position_end).
    """
    if not hash_values:
        return []
    rows = conn.execute(
        """
        SELECT document_id, hash_value, position_start, position_end
        FROM fingerprints
        WHERE hash_value = ANY(%s)
        """,
        (hash_values,),
    ).fetchall()
    return rows


def get_document(conn: psycopg.Connection, document_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, title, author, year, source_url, file_path FROM documents WHERE id = %s",
        (document_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "author": row[2],
        "year": row[3],
        "source_url": row[4],
        "file_path": row[5],
    }


def get_document_text(conn: psycopg.Connection, document_id: int) -> str | None:
    row = conn.execute(
        "SELECT full_text FROM document_text WHERE document_id = %s",
        (document_id,),
    ).fetchone()
    return row[0] if row else None
```

- [ ] **Step 2: Verify by running init-db and inserting a test record manually**

```bash
uv run python -c "
from plagiarism_checker.db import get_connection, insert_document
from plagiarism_checker.models import create_tables
conn = get_connection()
create_tables(conn)
doc_id = insert_document(conn, '/tmp/test.pdf', title='Test')
print(f'Inserted document {doc_id}')
conn.close()
"
```

Expected: "Inserted document 1"

- [ ] **Step 3: Commit**

```bash
git add src/plagiarism_checker/db.py
git commit -m "feat: database operations for documents and fingerprints"
```

---

### Task 7: OAI-PMH Scraper

**Files:**
- Create: `src/plagiarism_checker/scraper/__init__.py`
- Create: `src/plagiarism_checker/scraper/oai_harvester.py`
- Modify: `src/plagiarism_checker/cli.py` (add `scrape` command)

- [ ] **Step 1: Implement oai_harvester.py**

```python
# src/plagiarism_checker/scraper/oai_harvester.py
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sickle import Sickle

logger = logging.getLogger(__name__)

DEFAULT_OAI_URL = "https://eprints.walisongo.ac.id/cgi/oai2"
DEFAULT_OUTPUT_DIR = Path("data/corpus")
MAX_RETRIES = 3


def _check_robots_txt(url: str) -> bool:
    """Check if the URL is allowed by robots.txt."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True  # Allow if robots.txt is unreachable


def _download_with_retry(
    client: httpx.Client, url: str, max_retries: int = MAX_RETRIES
) -> httpx.Response:
    """Download with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            logger.warning(
                "Retry %d/%d for %s (waiting %ds): %s",
                attempt + 1, max_retries, url, wait, e,
            )
            time.sleep(wait)


def harvest_pdf_urls(
    oai_url: str = DEFAULT_OAI_URL,
    max_records: int = 200,
) -> list[dict]:
    """Harvest metadata records from an OAI-PMH endpoint.

    Returns list of dicts with keys: identifier, title, creator, date, url
    """
    if not _check_robots_txt(oai_url):
        logger.error("Blocked by robots.txt: %s", oai_url)
        return []

    sickle = Sickle(oai_url)
    records_out: list[dict] = []

    try:
        records = sickle.ListRecords(metadataPrefix="oai_dc")
    except Exception:
        logger.error("Failed to connect to OAI-PMH endpoint: %s", oai_url)
        return []

    for record in records:
        if len(records_out) >= max_records:
            break

        meta = record.metadata
        if not meta:
            continue

        # Look for PDF URLs in the identifier/relation fields
        urls = meta.get("identifier", []) + meta.get("relation", [])
        pdf_url = None
        for u in urls:
            if isinstance(u, str) and u.endswith(".pdf"):
                pdf_url = u
                break

        if not pdf_url:
            continue

        records_out.append({
            "identifier": record.header.identifier,
            "title": (meta.get("title", [""])[0] if meta.get("title") else ""),
            "creator": (meta.get("creator", [""])[0] if meta.get("creator") else ""),
            "date": (meta.get("date", [""])[0] if meta.get("date") else ""),
            "url": pdf_url,
        })

    logger.info("Found %d records with PDF URLs", len(records_out))
    return records_out


def download_pdfs(
    records: list[dict],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    delay: float = 1.5,
) -> tuple[int, int]:
    """Download PDFs from harvested records.

    Returns (success_count, failure_count).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    success = 0
    failure = 0

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for i, record in enumerate(records):
            filename = f"{i + 1:04d}.pdf"
            pdf_path = output_dir / filename
            meta_path = output_dir / f"{i + 1:04d}.json"

            if pdf_path.exists():
                logger.info("Skipping existing: %s", filename)
                success += 1
                continue

            if not _check_robots_txt(record["url"]):
                logger.warning("Blocked by robots.txt: %s", record["url"])
                failure += 1
                continue

            try:
                logger.info(
                    "Downloading %d/%d: %s", i + 1, len(records), record["title"][:60]
                )
                resp = _download_with_retry(client, record["url"])
                pdf_path.write_bytes(resp.content)
                meta_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
                success += 1
            except Exception as e:
                logger.warning("Failed to download %s after %d retries: %s", record["url"], MAX_RETRIES, e)
                failure += 1

            time.sleep(delay)

    return success, failure
```

- [ ] **Step 2: Add scrape command to cli.py**

```python
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
```

- [ ] **Step 3: Create scraper/__init__.py**

Empty file.

- [ ] **Step 4: Test the scrape command with a small count**

```bash
uv run plagiarism-checker scrape --count 3
```

Expected: Downloads 3 PDFs to `data/corpus/` with JSON metadata sidecars.

- [ ] **Step 5: Commit**

```bash
git add src/plagiarism_checker/scraper/ src/plagiarism_checker/cli.py
git commit -m "feat: OAI-PMH scraper for Indonesian academic PDFs"
```

---

### Task 8: Index Command — Full Pipeline (Extract + Fingerprint + Store)

**Files:**
- Modify: `src/plagiarism_checker/cli.py` (add `index` command)

- [ ] **Step 1: Add index command to cli.py**

```python
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
```

- [ ] **Step 2: Test with the scraped PDFs (or fixture)**

```bash
uv run plagiarism-checker index tests/fixtures/
```

Expected: Indexes the sample PDF, prints "Indexed: 1, Skipped: 0".

- [ ] **Step 3: Commit**

```bash
git add src/plagiarism_checker/cli.py
git commit -m "feat: index command — extract, fingerprint, and store PDFs"
```

---

### Task 9: Plagiarism Matcher

**Files:**
- Create: `src/plagiarism_checker/checker/__init__.py`
- Create: `src/plagiarism_checker/checker/matcher.py`
- Create: `tests/test_matcher.py`

- [ ] **Step 1: Write failing tests for matcher**

```python
# tests/test_matcher.py
from plagiarism_checker.checker.matcher import (
    group_matches_by_document,
    find_consecutive_matches,
    calculate_similarity,
    MatchResult,
)


def test_group_matches_by_document():
    # Simulated DB results: (document_id, hash_value, position_start, position_end)
    db_matches = [
        (1, 100, 0, 20),
        (1, 200, 21, 40),
        (2, 100, 5, 25),
        (1, 300, 41, 60),
    ]
    # Submitted fingerprints: (pos_start, pos_end, hash_value)
    submitted = [(0, 20, 100), (21, 40, 200), (41, 60, 300)]
    grouped = group_matches_by_document(db_matches, submitted)
    assert 1 in grouped
    assert 2 in grouped
    assert len(grouped[1]) == 3
    assert len(grouped[2]) == 1


def test_find_consecutive_matches():
    # Pairs of (submitted_pos, source_pos) sorted by submitted position
    match_pairs = [
        (0, 0),
        (1, 1),
        (2, 2),
        (5, 10),  # gap — not consecutive
        (6, 11),
    ]
    runs = find_consecutive_matches(match_pairs, min_length=3)
    assert len(runs) == 1
    assert len(runs[0]) == 3  # first three are consecutive


def test_calculate_similarity():
    result = calculate_similarity(
        matched_char_count=150,
        total_char_count=1000,
    )
    assert result == 15.0


def test_calculate_similarity_zero():
    result = calculate_similarity(matched_char_count=0, total_char_count=1000)
    assert result == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_matcher.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement matcher.py**

```python
# src/plagiarism_checker/checker/matcher.py
from collections.abc import Callable
from dataclasses import dataclass, field
from plagiarism_checker.config import MIN_MATCH_LENGTH


@dataclass
class MatchedPassage:
    submitted_start: int
    submitted_end: int
    source_start: int
    source_end: int


@dataclass
class MatchResult:
    document_id: int
    title: str | None
    author: str | None
    similarity_pct: float
    matched_passages: list[MatchedPassage] = field(default_factory=list)


def group_matches_by_document(
    db_matches: list[tuple[int, int, int, int]],
    submitted_fps: list[tuple[int, int, int]],
) -> dict[int, list[tuple]]:
    """Group DB matches by document_id, paired with submitted fingerprint info.

    db_matches: (document_id, hash_value, source_pos_start, source_pos_end)
    submitted_fps: (pos_start, pos_end, hash_value)

    Returns: {document_id: [(sub_pos_start, sub_pos_end, src_pos_start, src_pos_end, hash_value), ...]}
    """
    # Use a list to handle duplicate hashes at different positions
    sub_by_hash: dict[int, list[tuple[int, int]]] = {}
    for pos_start, pos_end, hash_val in submitted_fps:
        sub_by_hash.setdefault(hash_val, []).append((pos_start, pos_end))

    grouped: dict[int, list[tuple]] = {}
    for doc_id, hash_val, src_start, src_end in db_matches:
        if hash_val not in sub_by_hash:
            continue
        for sub_start, sub_end in sub_by_hash[hash_val]:
            grouped.setdefault(doc_id, []).append(
                (sub_start, sub_end, src_start, src_end, hash_val)
            )

    return grouped


def find_consecutive_matches(
    match_pairs: list[tuple[int, int]],
    min_length: int = MIN_MATCH_LENGTH,
) -> list[list[tuple[int, int]]]:
    """Find runs of consecutive matching fingerprints.

    match_pairs: sorted list of (submitted_word_idx, source_word_idx)
    Returns: list of runs, where each run is a list of (sub_idx, src_idx) pairs
    """
    if not match_pairs:
        return []

    runs: list[list[tuple[int, int]]] = []
    current_run = [match_pairs[0]]

    for i in range(1, len(match_pairs)):
        prev_sub, prev_src = match_pairs[i - 1]
        curr_sub, curr_src = match_pairs[i]
        if curr_sub == prev_sub + 1 and curr_src == prev_src + 1:
            current_run.append(match_pairs[i])
        else:
            if len(current_run) >= min_length:
                runs.append(current_run)
            current_run = [match_pairs[i]]

    if len(current_run) >= min_length:
        runs.append(current_run)

    return runs


def calculate_similarity(matched_char_count: int, total_char_count: int) -> float:
    if total_char_count == 0:
        return 0.0
    return round((matched_char_count / total_char_count) * 100, 1)


def check_document(
    submitted_fps: list[tuple[int, int, int]],
    submitted_text: str,
    db_matches: list[tuple[int, int, int, int]],
    get_doc_info: Callable[[int], dict | None],
) -> tuple[float, list[MatchResult]]:
    """Run full plagiarism check.

    Args:
        submitted_fps: fingerprints of submitted document
        submitted_text: full normalized text of submitted document
        db_matches: raw matches from DB query
        get_doc_info: callable(doc_id) -> dict with title, author

    Returns:
        (overall_similarity_pct, list of MatchResult per source document)
    """
    total_chars = len(submitted_text)
    grouped = group_matches_by_document(db_matches, submitted_fps)

    results: list[MatchResult] = []
    all_matched_ranges: list[tuple[int, int]] = []

    for doc_id, matches in grouped.items():
        # Sort by submitted position
        matches.sort(key=lambda m: m[0])

        # Build word-index-like pairs for consecutive detection
        # Use enumerate-based indices since fingerprints are ordered
        indexed_matches = list(enumerate(matches))
        # Create pairs: (sequential index in submitted, sequential index in source)
        # We need to find runs where both submitted and source positions increase together
        match_pairs: list[tuple[int, int]] = []
        src_positions = sorted(set(m[2] for m in matches))
        src_pos_to_idx = {pos: i for i, pos in enumerate(src_positions)}

        for i, m in enumerate(matches):
            sub_start, sub_end, src_start, src_end, _ = m
            match_pairs.append((i, src_pos_to_idx[src_start]))

        runs = find_consecutive_matches(match_pairs, min_length=MIN_MATCH_LENGTH)

        doc_matched_chars = 0
        passages: list[MatchedPassage] = []

        for run in runs:
            run_matches = [matches[pair[0]] for pair in run]
            sub_start = run_matches[0][0]
            sub_end = run_matches[-1][1]
            src_start = run_matches[0][2]
            src_end = run_matches[-1][3]

            char_span = sub_end - sub_start
            doc_matched_chars += char_span
            all_matched_ranges.append((sub_start, sub_end))

            passages.append(MatchedPassage(
                submitted_start=sub_start,
                submitted_end=sub_end,
                source_start=src_start,
                source_end=src_end,
            ))

        if passages:
            doc_info = get_doc_info(doc_id)
            results.append(MatchResult(
                document_id=doc_id,
                title=doc_info.get("title") if doc_info else None,
                author=doc_info.get("author") if doc_info else None,
                similarity_pct=calculate_similarity(doc_matched_chars, total_chars),
                matched_passages=passages,
            ))

    # Overall similarity: merge overlapping ranges, count unique matched chars
    merged = _merge_ranges(all_matched_ranges)
    overall_matched = sum(end - start for start, end in merged)
    overall_pct = calculate_similarity(overall_matched, total_chars)

    results.sort(key=lambda r: r.similarity_pct, reverse=True)
    return overall_pct, results


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
```

- [ ] **Step 4: Create checker/__init__.py**

Empty file.

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_matcher.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/plagiarism_checker/checker/ tests/test_matcher.py
git commit -m "feat: plagiarism matcher with consecutive fingerprint detection"
```

---

### Task 10: Report Generator

**Files:**
- Create: `src/plagiarism_checker/checker/report.py`

- [ ] **Step 1: Implement report.py**

```python
# src/plagiarism_checker/checker/report.py
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
    # Collect all matched ranges with source info
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
```

- [ ] **Step 2: Commit**

```bash
git add src/plagiarism_checker/checker/report.py
git commit -m "feat: report generator with terminal, JSON, and HTML output"
```

---

### Task 11: Check Command — Full Pipeline

**Files:**
- Modify: `src/plagiarism_checker/cli.py` (add `check` command)

- [ ] **Step 1: Add check command to cli.py**

```python
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

    if format == "json":
        report = format_json(overall_pct, results, cleaned)
    elif format == "html":
        report = format_html(overall_pct, results, cleaned)
    else:
        report = format_terminal(overall_pct, results, cleaned)

    if output:
        output.write_text(report)
        typer.echo(f"Report written to {output}")
    else:
        typer.echo(report)
```

- [ ] **Step 2: Test end-to-end with fixture**

```bash
# Index the fixture
uv run plagiarism-checker index tests/fixtures/

# Check the same file against itself (should show ~100% similarity)
uv run plagiarism-checker check tests/fixtures/sample_short.pdf
```

Expected: Report showing high similarity percentage since the document is in the corpus.

- [ ] **Step 3: Test JSON output**

```bash
uv run plagiarism-checker check tests/fixtures/sample_short.pdf --format json
```

Expected: Valid JSON output with similarity data.

- [ ] **Step 4: Commit**

```bash
git add src/plagiarism_checker/cli.py
git commit -m "feat: check command — full plagiarism detection pipeline"
```

---

### Task 12: Integration Test

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Create conftest.py with DB fixture**

```python
# tests/conftest.py
import os
import pytest
import psycopg
from plagiarism_checker.models import create_tables

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://plagiarism:plagiarism@localhost:6432/plagiarism_checker_test",
)


@pytest.fixture
def db_conn():
    """Provide a clean test database connection."""
    # Connect to default DB to create test DB
    default_url = TEST_DB_URL.rsplit("/", 1)[0] + "/plagiarism_checker"
    with psycopg.connect(default_url, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS plagiarism_checker_test")
        conn.execute("CREATE DATABASE plagiarism_checker_test")

    conn = psycopg.connect(TEST_DB_URL)
    create_tables(conn)
    yield conn
    conn.close()

    with psycopg.connect(default_url, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS plagiarism_checker_test")
```

- [ ] **Step 2: Write integration test**

```python
# tests/test_integration.py
from plagiarism_checker.checker.matcher import check_document
from plagiarism_checker.db import (
    insert_document,
    insert_document_text,
    insert_fingerprints,
    find_matching_fingerprints,
    get_document,
)
from plagiarism_checker.indexer.winnowing import fingerprint_text
from plagiarism_checker.utils.text import normalize_text, remove_stopwords, load_stopwords


def test_detects_copied_passage(db_conn):
    """A document with copied text should be detected."""
    stopwords = load_stopwords()

    # Original document
    original = (
        "penelitian ini bertujuan untuk mengetahui pengaruh motivasi belajar "
        "terhadap prestasi akademik mahasiswa program studi teknik informatika "
        "universitas negeri semarang pada semester genap tahun ajaran dua ribu "
        "dua puluh lima metode penelitian yang digunakan adalah metode kuantitatif "
        "dengan pendekatan survei populasi dalam penelitian ini adalah seluruh "
        "mahasiswa aktif program studi teknik informatika"
    )
    original_clean = remove_stopwords(normalize_text(original), stopwords)
    original_fps = fingerprint_text(original_clean)

    doc_id = insert_document(db_conn, "/test/original.pdf", title="Original Thesis")
    insert_document_text(db_conn, doc_id, original_clean)
    insert_fingerprints(db_conn, doc_id, original_fps)

    # Submitted document with copied passage
    submitted = (
        "bab satu pendahuluan latar belakang masalah pendidikan tinggi "
        "penelitian ini bertujuan untuk mengetahui pengaruh motivasi belajar "
        "terhadap prestasi akademik mahasiswa program studi teknik informatika "
        "universitas negeri semarang pada semester genap tahun ajaran dua ribu "
        "dua puluh lima metode penelitian yang digunakan adalah metode kuantitatif "
        "bab dua tinjauan pustaka teori motivasi belajar"
    )
    submitted_clean = remove_stopwords(normalize_text(submitted), stopwords)
    submitted_fps = fingerprint_text(submitted_clean)

    hash_values = [h for _, _, h in submitted_fps]
    db_matches = find_matching_fingerprints(db_conn, hash_values)

    overall_pct, results = check_document(
        submitted_fps, submitted_clean, db_matches,
        lambda doc_id: get_document(db_conn, doc_id),
    )

    assert overall_pct > 0
    assert len(results) >= 1
    assert results[0].document_id == doc_id


def test_no_match_for_unique_text(db_conn):
    """A completely unique document should show 0% similarity."""
    stopwords = load_stopwords()

    # Index a document
    original = (
        "analisis dampak perubahan iklim terhadap produksi pertanian "
        "padi sawah daerah pesisir pantai utara jawa barat periode "
        "sepuluh tahun terakhir menggunakan pendekatan geospasial"
    )
    original_clean = remove_stopwords(normalize_text(original), stopwords)
    original_fps = fingerprint_text(original_clean)

    doc_id = insert_document(db_conn, "/test/original2.pdf", title="Climate Thesis")
    insert_document_text(db_conn, doc_id, original_clean)
    insert_fingerprints(db_conn, doc_id, original_fps)

    # Completely different submitted document
    submitted = (
        "pengembangan aplikasi mobile berbasis flutter untuk sistem "
        "manajemen inventaris gudang perusahaan manufaktur skala menengah "
        "studi kasus perusahaan tekstil bandung jawa barat indonesia"
    )
    submitted_clean = remove_stopwords(normalize_text(submitted), stopwords)
    submitted_fps = fingerprint_text(submitted_clean)

    hash_values = [h for _, _, h in submitted_fps]
    db_matches = find_matching_fingerprints(db_conn, hash_values)

    overall_pct, results = check_document(
        submitted_fps, submitted_clean, db_matches,
        lambda doc_id: get_document(db_conn, doc_id),
    )

    assert overall_pct == 0.0
    assert len(results) == 0
```

- [ ] **Step 3: Run integration tests**

```bash
uv run pytest tests/test_integration.py -v
```

Expected: Both tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_integration.py
git commit -m "test: integration tests for plagiarism detection pipeline"
```

---

### Task 13: Dockerfile & Production Docker Compose

**Files:**
- Create: `Dockerfile`
- Modify: `docker-compose.yml` (add app service, commented out by default)

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY src/ src/
COPY data/ data/

ENTRYPOINT ["uv", "run", "plagiarism-checker"]
```

- [ ] **Step 2: Add app service to docker-compose.yml (commented out)**

Add to the end of docker-compose.yml services:

```yaml
  # Uncomment to run the app in Docker
  # app:
  #   build: .
  #   environment:
  #     DATABASE_URL: postgresql://${POSTGRES_USER:-plagiarism}:${POSTGRES_PASSWORD:-plagiarism}@pgbouncer:5432/${POSTGRES_DB:-plagiarism_checker}
  #   depends_on:
  #     - pgbouncer
  #   volumes:
  #     - ./data:/app/data
```

- [ ] **Step 3: Build and verify Docker image**

```bash
docker build -t plagiarism-checker .
```

Expected: Image builds successfully.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: Dockerfile for production deployment"
```

---

### Task 14: Final README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write complete README**

Cover:
- Project description
- Prerequisites (Python 3.12+, uv, Docker)
- Quick start:
  1. `cp .env.example .env`
  2. `docker compose up -d`
  3. `uv sync`
  4. `uv run plagiarism-checker init-db`
- CLI commands: `scrape`, `index`, `check` with examples
- Configuration (.env variables)
- Development: `uv run pytest`
- Docker deployment

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: complete README with setup and usage instructions"
```

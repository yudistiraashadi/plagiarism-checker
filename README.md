# Plagiarism Checker

A Turnitin-style plagiarism detection tool for Indonesian university theses, using the Winnowing algorithm against an OAI-PMH corpus.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker and Docker Compose

## Setup

```bash
cp .env.example .env
docker compose up -d
uv sync
```

## CLI Usage

```bash
# Scrape theses from OAI-PMH repository
uv run plagiarism-checker scrape

# Index scraped documents into the database
uv run plagiarism-checker index

# Check a thesis for plagiarism
uv run plagiarism-checker check path/to/thesis.pdf
```

## Development

```bash
uv run pytest
```

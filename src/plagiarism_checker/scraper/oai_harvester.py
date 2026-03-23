# src/plagiarism_checker/scraper/oai_harvester.py
import json
import logging
import time
from pathlib import Path

import httpx
from sickle import Sickle

logger = logging.getLogger(__name__)

DEFAULT_OAI_URL = "https://eprints.walisongo.ac.id/cgi/oai2"
DEFAULT_OUTPUT_DIR = Path("data/corpus")
MAX_RETRIES = 3


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

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


def build_position_map(
    raw_text: str, stopwords: set[str]
) -> list[tuple[int, int, int, int]]:
    """Build a word-level mapping from cleaned text positions to raw text positions.

    Returns a list of (cleaned_start, cleaned_end, raw_start, raw_end) tuples.
    """
    mapping: list[tuple[int, int, int, int]] = []
    cleaned_offset = 0

    for match in re.finditer(r"\S+", raw_text):
        raw_word = match.group()
        raw_start = match.start()
        raw_end = match.end()

        # Apply same normalization as normalize_text
        normalized = raw_word.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\d+", "", normalized)
        normalized = normalized.strip()

        if not normalized or normalized in stopwords:
            continue

        cleaned_start = cleaned_offset
        cleaned_end = cleaned_offset + len(normalized)
        mapping.append((cleaned_start, cleaned_end, raw_start, raw_end))
        cleaned_offset = cleaned_end + 1  # +1 for the space separator

    return mapping


def map_cleaned_range_to_raw(
    mapping: list[tuple[int, int, int, int]],
    cleaned_start: int,
    cleaned_end: int,
) -> tuple[int, int]:
    """Translate a character range in cleaned text to the corresponding range in raw text."""
    raw_starts = []
    raw_ends = []

    for c_start, c_end, r_start, r_end in mapping:
        # Check overlap: two ranges overlap if one starts before the other ends
        if c_start < cleaned_end and c_end > cleaned_start:
            raw_starts.append(r_start)
            raw_ends.append(r_end)

    if not raw_starts:
        return (0, 0)

    return (min(raw_starts), max(raw_ends))

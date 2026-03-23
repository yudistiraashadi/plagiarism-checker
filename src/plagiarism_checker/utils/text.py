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

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

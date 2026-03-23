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

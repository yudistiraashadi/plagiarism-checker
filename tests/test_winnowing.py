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
    hashes = [(i, h) for i, h in enumerate([10, 5, 8, 3, 9, 7, 2, 6])]
    result = winnow(hashes, window_size=4)
    positions = [pos for pos, _ in result]
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

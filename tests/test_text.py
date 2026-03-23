from plagiarism_checker.utils.text import (
    normalize_text,
    remove_stopwords,
    load_stopwords,
    build_position_map,
    map_cleaned_range_to_raw,
)


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


def test_build_position_map_basic():
    raw = "Hello, World! This is a test."
    stopwords = {"this", "is", "a"}
    mapping = build_position_map(raw, stopwords)
    assert len(mapping) == 3
    assert mapping[0] == (0, 5, 0, 6)      # "hello" -> "Hello,"
    assert mapping[1] == (6, 11, 7, 13)    # "world" -> "World!"
    assert mapping[2] == (12, 16, 24, 29)  # "test" -> "test."


def test_build_position_map_empty():
    mapping = build_position_map("", set())
    assert mapping == []


def test_map_cleaned_range_to_raw():
    raw = "Hello, World! This is a test document here."
    stopwords = {"this", "is", "a"}
    mapping = build_position_map(raw, stopwords)
    raw_start, raw_end = map_cleaned_range_to_raw(mapping, 0, 16)
    assert raw_start == 0
    assert raw_end == 28

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

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

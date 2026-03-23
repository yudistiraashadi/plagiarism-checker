from collections.abc import Callable
from dataclasses import dataclass, field
from plagiarism_checker.config import MIN_MATCH_LENGTH


@dataclass
class MatchedPassage:
    submitted_start: int
    submitted_end: int
    source_start: int
    source_end: int


@dataclass
class MatchResult:
    document_id: int
    title: str | None
    author: str | None
    similarity_pct: float
    matched_passages: list[MatchedPassage] = field(default_factory=list)


def group_matches_by_document(
    db_matches: list[tuple[int, int, int, int]],
    submitted_fps: list[tuple[int, int, int]],
) -> dict[int, list[tuple]]:
    """Group DB matches by document_id, paired with submitted fingerprint info.

    db_matches: (document_id, hash_value, source_pos_start, source_pos_end)
    submitted_fps: (pos_start, pos_end, hash_value)

    Returns: {document_id: [(sub_pos_start, sub_pos_end, src_pos_start, src_pos_end, hash_value), ...]}
    """
    # Use a list to handle duplicate hashes at different positions
    sub_by_hash: dict[int, list[tuple[int, int]]] = {}
    for pos_start, pos_end, hash_val in submitted_fps:
        sub_by_hash.setdefault(hash_val, []).append((pos_start, pos_end))

    grouped: dict[int, list[tuple]] = {}
    for doc_id, hash_val, src_start, src_end in db_matches:
        if hash_val not in sub_by_hash:
            continue
        for sub_start, sub_end in sub_by_hash[hash_val]:
            grouped.setdefault(doc_id, []).append(
                (sub_start, sub_end, src_start, src_end, hash_val)
            )

    return grouped


def find_consecutive_matches(
    match_pairs: list[tuple[int, int]],
    min_length: int = MIN_MATCH_LENGTH,
) -> list[list[tuple[int, int]]]:
    """Find runs of consecutive matching fingerprints.

    match_pairs: sorted list of (submitted_word_idx, source_word_idx)
    Returns: list of runs, where each run is a list of (sub_idx, src_idx) pairs
    """
    if not match_pairs:
        return []

    runs: list[list[tuple[int, int]]] = []
    current_run = [match_pairs[0]]

    for i in range(1, len(match_pairs)):
        prev_sub, prev_src = match_pairs[i - 1]
        curr_sub, curr_src = match_pairs[i]
        if curr_sub == prev_sub + 1 and curr_src == prev_src + 1:
            current_run.append(match_pairs[i])
        else:
            if len(current_run) >= min_length:
                runs.append(current_run)
            current_run = [match_pairs[i]]

    if len(current_run) >= min_length:
        runs.append(current_run)

    return runs


def calculate_similarity(matched_char_count: int, total_char_count: int) -> float:
    if total_char_count == 0:
        return 0.0
    return round((matched_char_count / total_char_count) * 100, 1)


def check_document(
    submitted_fps: list[tuple[int, int, int]],
    submitted_text: str,
    db_matches: list[tuple[int, int, int, int]],
    get_doc_info: Callable[[int], dict | None],
) -> tuple[float, list[MatchResult]]:
    """Run full plagiarism check.

    Args:
        submitted_fps: fingerprints of submitted document
        submitted_text: full normalized text of submitted document
        db_matches: raw matches from DB query
        get_doc_info: callable(doc_id) -> dict with title, author

    Returns:
        (overall_similarity_pct, list of MatchResult per source document)
    """
    total_chars = len(submitted_text)
    grouped = group_matches_by_document(db_matches, submitted_fps)

    results: list[MatchResult] = []
    all_matched_ranges: list[tuple[int, int]] = []

    for doc_id, matches in grouped.items():
        # Sort by submitted position
        matches.sort(key=lambda m: m[0])

        # Build word-index-like pairs for consecutive detection
        # Use enumerate-based indices since fingerprints are ordered
        # Create pairs: (sequential index in submitted, sequential index in source)
        # We need to find runs where both submitted and source positions increase together
        match_pairs: list[tuple[int, int]] = []
        src_positions = sorted(set(m[2] for m in matches))
        src_pos_to_idx = {pos: i for i, pos in enumerate(src_positions)}

        for i, m in enumerate(matches):
            sub_start, sub_end, src_start, src_end, _ = m
            match_pairs.append((i, src_pos_to_idx[src_start]))

        runs = find_consecutive_matches(match_pairs, min_length=MIN_MATCH_LENGTH)

        doc_matched_chars = 0
        passages: list[MatchedPassage] = []

        for run in runs:
            run_matches = [matches[pair[0]] for pair in run]
            sub_start = run_matches[0][0]
            sub_end = run_matches[-1][1]
            src_start = run_matches[0][2]
            src_end = run_matches[-1][3]

            char_span = sub_end - sub_start
            doc_matched_chars += char_span
            all_matched_ranges.append((sub_start, sub_end))

            passages.append(MatchedPassage(
                submitted_start=sub_start,
                submitted_end=sub_end,
                source_start=src_start,
                source_end=src_end,
            ))

        if passages:
            doc_info = get_doc_info(doc_id)
            results.append(MatchResult(
                document_id=doc_id,
                title=doc_info.get("title") if doc_info else None,
                author=doc_info.get("author") if doc_info else None,
                similarity_pct=calculate_similarity(doc_matched_chars, total_chars),
                matched_passages=passages,
            ))

    # Overall similarity: merge overlapping ranges, count unique matched chars
    merged = _merge_ranges(all_matched_ranges)
    overall_matched = sum(end - start for start, end in merged)
    overall_pct = calculate_similarity(overall_matched, total_chars)

    results.sort(key=lambda r: r.similarity_pct, reverse=True)
    return overall_pct, results


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged

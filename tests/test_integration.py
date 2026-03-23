from plagiarism_checker.checker.matcher import check_document
from plagiarism_checker.db import (
    insert_document,
    insert_document_text,
    insert_fingerprints,
    find_matching_fingerprints,
    get_document,
)
from plagiarism_checker.indexer.winnowing import fingerprint_text
from plagiarism_checker.utils.text import normalize_text, remove_stopwords, load_stopwords


def test_detects_copied_passage(db_conn):
    """A document with copied text should be detected."""
    stopwords = load_stopwords()

    # Original document
    original = (
        "penelitian ini bertujuan untuk mengetahui pengaruh motivasi belajar "
        "terhadap prestasi akademik mahasiswa program studi teknik informatika "
        "universitas negeri semarang pada semester genap tahun ajaran dua ribu "
        "dua puluh lima metode penelitian yang digunakan adalah metode kuantitatif "
        "dengan pendekatan survei populasi dalam penelitian ini adalah seluruh "
        "mahasiswa aktif program studi teknik informatika"
    )
    original_clean = remove_stopwords(normalize_text(original), stopwords)
    original_fps = fingerprint_text(original_clean)

    doc_id = insert_document(db_conn, "/test/original.pdf", title="Original Thesis")
    insert_document_text(db_conn, doc_id, original_clean)
    insert_fingerprints(db_conn, doc_id, original_fps)

    # Submitted document with copied passage
    submitted = (
        "bab satu pendahuluan latar belakang masalah pendidikan tinggi "
        "penelitian ini bertujuan untuk mengetahui pengaruh motivasi belajar "
        "terhadap prestasi akademik mahasiswa program studi teknik informatika "
        "universitas negeri semarang pada semester genap tahun ajaran dua ribu "
        "dua puluh lima metode penelitian yang digunakan adalah metode kuantitatif "
        "bab dua tinjauan pustaka teori motivasi belajar"
    )
    submitted_clean = remove_stopwords(normalize_text(submitted), stopwords)
    submitted_fps = fingerprint_text(submitted_clean)

    hash_values = [h for _, _, h in submitted_fps]
    db_matches = find_matching_fingerprints(db_conn, hash_values)

    overall_pct, results = check_document(
        submitted_fps, submitted_clean, db_matches,
        lambda doc_id: get_document(db_conn, doc_id),
    )

    assert overall_pct > 0
    assert len(results) >= 1
    assert results[0].document_id == doc_id


def test_no_match_for_unique_text(db_conn):
    """A completely unique document should show 0% similarity."""
    stopwords = load_stopwords()

    # Index a document
    original = (
        "analisis dampak perubahan iklim terhadap produksi pertanian "
        "padi sawah daerah pesisir pantai utara jawa barat periode "
        "sepuluh tahun terakhir menggunakan pendekatan geospasial"
    )
    original_clean = remove_stopwords(normalize_text(original), stopwords)
    original_fps = fingerprint_text(original_clean)

    doc_id = insert_document(db_conn, "/test/original2.pdf", title="Climate Thesis")
    insert_document_text(db_conn, doc_id, original_clean)
    insert_fingerprints(db_conn, doc_id, original_fps)

    # Completely different submitted document
    submitted = (
        "pengembangan aplikasi mobile berbasis flutter untuk sistem "
        "manajemen inventaris gudang perusahaan manufaktur skala menengah "
        "studi kasus perusahaan tekstil bandung jawa barat indonesia"
    )
    submitted_clean = remove_stopwords(normalize_text(submitted), stopwords)
    submitted_fps = fingerprint_text(submitted_clean)

    hash_values = [h for _, _, h in submitted_fps]
    db_matches = find_matching_fingerprints(db_conn, hash_values)

    overall_pct, results = check_document(
        submitted_fps, submitted_clean, db_matches,
        lambda doc_id: get_document(db_conn, doc_id),
    )

    assert overall_pct == 0.0
    assert len(results) == 0

import psycopg
from plagiarism_checker.config import DATABASE_URL


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)


def insert_document(
    conn: psycopg.Connection,
    file_path: str,
    title: str | None = None,
    author: str | None = None,
    year: int | None = None,
    source_url: str | None = None,
) -> int:
    """Insert a document record and return its ID."""
    row = conn.execute(
        """
        INSERT INTO documents (title, author, year, source_url, file_path, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        RETURNING id
        """,
        (title, author, year, source_url, file_path),
    ).fetchone()
    conn.commit()
    return row[0]


def insert_document_text(
    conn: psycopg.Connection, document_id: int, full_text: str
) -> None:
    conn.execute(
        """
        INSERT INTO document_text (document_id, full_text, char_count)
        VALUES (%s, %s, %s)
        """,
        (document_id, full_text, len(full_text)),
    )
    conn.commit()


def _to_signed64(h: int) -> int:
    """Convert an unsigned 64-bit hash to a signed 64-bit integer for PostgreSQL bigint."""
    if h >= 2**63:
        return h - 2**64
    return h


def insert_fingerprints(
    conn: psycopg.Connection,
    document_id: int,
    fingerprints: list[tuple[int, int, int]],
) -> None:
    """Batch insert fingerprints. Each tuple is (pos_start, pos_end, hash_value)."""
    with conn.cursor() as cur:
        with cur.copy(
            "COPY fingerprints (document_id, hash_value, position_start, position_end) FROM STDIN"
        ) as copy:
            for pos_start, pos_end, hash_val in fingerprints:
                copy.write_row((document_id, _to_signed64(hash_val), pos_start, pos_end))
    conn.commit()


def update_document_status(
    conn: psycopg.Connection, document_id: int, status: str
) -> None:
    conn.execute(
        "UPDATE documents SET status = %s WHERE id = %s",
        (status, document_id),
    )
    conn.commit()


def find_matching_fingerprints(
    conn: psycopg.Connection, hash_values: list[int]
) -> list[tuple[int, int, int, int]]:
    """Find fingerprints matching any of the given hashes.

    Returns list of (document_id, hash_value, position_start, position_end).
    """
    if not hash_values:
        return []
    signed_hashes = [_to_signed64(h) for h in hash_values]
    rows = conn.execute(
        """
        SELECT document_id, hash_value, position_start, position_end
        FROM fingerprints
        WHERE hash_value = ANY(%s)
        """,
        (signed_hashes,),
    ).fetchall()
    return rows


def get_document(conn: psycopg.Connection, document_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, title, author, year, source_url, file_path FROM documents WHERE id = %s",
        (document_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "author": row[2],
        "year": row[3],
        "source_url": row[4],
        "file_path": row[5],
    }


def get_document_text(conn: psycopg.Connection, document_id: int) -> str | None:
    row = conn.execute(
        "SELECT full_text FROM document_text WHERE document_id = %s",
        (document_id,),
    ).fetchone()
    return row[0] if row else None

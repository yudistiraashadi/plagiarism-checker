import psycopg


def create_tables(conn: psycopg.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            title TEXT,
            author TEXT,
            year INTEGER,
            source_url TEXT,
            file_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_text (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            full_text TEXT NOT NULL,
            char_count INTEGER NOT NULL DEFAULT 0,
            section_offsets JSONB
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            hash_value BIGINT NOT NULL,
            position_start INTEGER NOT NULL,
            position_end INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fingerprints_hash
        ON fingerprints (hash_value)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fingerprints_document
        ON fingerprints (document_id)
    """)
    conn.commit()

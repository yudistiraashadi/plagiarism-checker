import os
import pytest
import psycopg
from plagiarism_checker.config import DATABASE_URL
from plagiarism_checker.models import create_tables

# Derive test DB URL from the app's DATABASE_URL
_base = DATABASE_URL.rsplit("/", 1)[0]
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", f"{_base}/plagiarism_checker_test")

# Direct PostgreSQL URL for admin operations (replace PgBouncer port with PostgreSQL port)
_ADMIN_URL = DATABASE_URL.replace(":6433/", ":5433/").replace(":6432/", ":5432/")


@pytest.fixture
def db_conn():
    """Provide a clean test database connection."""
    with psycopg.connect(_ADMIN_URL, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS plagiarism_checker_test")
        conn.execute("CREATE DATABASE plagiarism_checker_test")

    # For actual test operations, connect directly to PostgreSQL test DB
    _test_db_direct = TEST_DB_URL.replace(":6433/", ":5433/").replace(":6432/", ":5432/")
    conn = psycopg.connect(_test_db_direct)
    create_tables(conn)
    yield conn
    conn.close()

    with psycopg.connect(_ADMIN_URL, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS plagiarism_checker_test")

from app.db import normalize_database_url


def test_normalizes_supabase_postgresql_url_to_psycopg3():
    assert (
        normalize_database_url("postgresql://user:secret@pooler.example.com:5432/postgres")
        == "postgresql+psycopg://user:secret@pooler.example.com:5432/postgres"
    )


def test_normalizes_legacy_postgres_scheme_to_psycopg3():
    assert normalize_database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_preserves_explicit_driver_and_sqlite_urls():
    explicit = "postgresql+psycopg://u:p@host/db"
    sqlite = "sqlite:///:memory:"
    assert normalize_database_url(explicit) == explicit
    assert normalize_database_url(sqlite) == sqlite

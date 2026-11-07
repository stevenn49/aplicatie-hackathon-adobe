"""
Test fixtures.

Every test runs against a scratch MySQL database (`marketpulse_test`) that is
created and dropped around the session, never the development database the
dashboard uses. The app's settings are overridden BEFORE `main` is imported,
because `database.connection` builds the engine at import time.
"""
import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Must happen before any project import.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+pymysql://marketpulse:marketpulse@127.0.0.1:3307/marketpulse_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("OPENROUTER_API_KEY", "")
os.environ.setdefault("OPENROUTER_MODEL", "")


def _split_url(url: str):
    """Return (server_url_without_db, database_name) for a SQLAlchemy MySQL URL."""
    prefix, _, rest = url.partition("://")
    credentials, _, host_part = rest.rpartition("@")
    host, _, database = host_part.partition("/")
    return f"{prefix}://{credentials}@{host}", database


@pytest.fixture(scope="session", autouse=True)
def scratch_database():
    """
    Create the scratch database before the session and drop it afterwards.
    Skips the whole suite (with a clear reason) when MySQL is unreachable.
    """
    from sqlalchemy import create_engine, text

    server_url, database = _split_url(TEST_DATABASE_URL)
    try:
        admin = create_engine(server_url, pool_pre_ping=True)
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{database}`"))
            conn.execute(
                text(
                    f"CREATE DATABASE `{database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            conn.commit()
        admin.dispose()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"MySQL is not reachable for tests: {exc}", allow_module_level=True)

    yield database

    try:
        admin = create_engine(server_url, pool_pre_ping=True)
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{database}`"))
            conn.commit()
        admin.dispose()
    except Exception:
        pass


@pytest.fixture(scope="session")
def client(scratch_database):
    """A TestClient with the lifespan running, so tables exist and seeds land."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_session(client):
    from database.connection import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

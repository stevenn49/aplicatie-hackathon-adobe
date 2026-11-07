import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from config import settings

logger = logging.getLogger("marketpulse.database")

# MySQL only. There is deliberately no fallback: a wrong DATABASE_URL used to
# silently create an empty SQLite file, which made a broken configuration look
# like a working application. Fail loudly instead.
if not settings.DATABASE_URL.startswith("mysql"):
    raise RuntimeError(
        f"DATABASE_URL must be a MySQL URL (mysql+pymysql://user:pass@host:port/db). "
        f"Got: {settings.DATABASE_URL.split('://')[0]}://..."
    )

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=False,
)
logger.info(f"Connected to database backend: {settings.DATABASE_URL.split('://')[0]}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session and ensures
    it is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Creates database tables if they do not exist.
    """
    import database.models  # noqa: F401 - ensure models are registered
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


def ping_db() -> bool:
    """
    Cheap liveness probe used by /health.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database ping failed: {exc}")
        return False

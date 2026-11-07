import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from config import settings
from database.connection import init_db, get_db, SessionLocal, ping_db
from database.seeds import seed_database_if_empty
from api.products import router as products_router
from api.analytics import router as analytics_router
from api.marketing import router as marketing_router
from api.admin import router as admin_router

# Setup structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("marketpulse.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management:
    Initializes the MySQL schema and populates the baseline dataset when empty.
    """
    logger.info("Initializing MarketPulse AI Backend...")
    init_db()

    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()

    logger.info("MarketPulse AI Backend started successfully.")
    yield
    logger.info("Shutting down MarketPulse AI Backend.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Market Intelligence API for technology products, consumer sentiment, price evolution, and trends.",
    version="1.10.0",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS) for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(products_router)
app.include_router(analytics_router)
app.include_router(marketing_router)
app.include_router(admin_router)


@app.get("/", tags=["General"])
def root():
    """
    Root entry point detailing application status and documentation URLs.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.1.0",
        "status": "operational",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json"
    }


@app.get("/health", tags=["General"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check verifying API responsiveness and database connectivity.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "online",
        "database": db_status,
        "database_backend": settings.DATABASE_URL.split("://")[0],
        "environment": settings.APP_ENV,
        "llm": "configured" if settings.llm_enabled else "not configured",
        "llm_model": settings.OPENROUTER_MODEL or None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

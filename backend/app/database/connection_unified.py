"""# =============================================================================
# CodeForge AI - Unified Database Connection
# =============================================================================
# Provides unified database access supporting both PostgreSQL and SQLite.
# Automatically selects the appropriate backend based on environment.
# =============================================================================
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy import event

# Base for all models
Base = declarative_base()

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


def get_database_url() -> str:
    """Get the appropriate database URL based on configuration."""
    if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
        url = DATABASE_URL
        if not url.startswith("sqlite+aiosqlite"):
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return url
    elif DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        url = DATABASE_URL
        if not url.startswith("postgresql+asyncpg"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    elif USE_SQLITE or not DATABASE_URL:
        # Default SQLite path - stored in backend directory
        import pathlib
        backend_dir = pathlib.Path(__file__).resolve().parent.parent.parent
        db_path = os.getenv("SQLITE_PATH", str(backend_dir / "codeforge.db"))
        url = f"sqlite+aiosqlite:///{db_path}"
        return url
    else:
        # PostgreSQL configured via DATABASE_URL
        url = DATABASE_URL
        if not url.startswith("postgresql+asyncpg"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


def is_sqlite() -> bool:
    """Check if we're using SQLite."""
    url = get_database_url()
    return "sqlite" in url.lower()


# Create engine based on database type
_db_url = get_database_url()

if is_sqlite():
    # SQLite configuration
    engine = create_async_engine(
        _db_url,
        echo=DEBUG,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # SQLite optimizations
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
        
else:
    # PostgreSQL configuration
    engine = create_async_engine(
        _db_url,
        echo=DEBUG,
        poolclass=NullPool,
    )

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initialize database - create all tables."""
    # Ensure all models are imported before table creation
    import app.database.models  # noqa: F401
    import app.database.models_extended  # noqa: F401
    
    # Ensure data directory exists for SQLite
    if is_sqlite():
        import os
        os.makedirs(os.path.dirname(_db_url.replace("sqlite+aiosqlite:///", "")), exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    db_type = "SQLite" if is_sqlite() else "PostgreSQL"
    print(f"[OK] Database initialized ({db_type})")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db_info() -> dict:
    """Get database connection information (safe for logging)."""
    url = get_database_url()
    
    if is_sqlite():
        path = url.replace("sqlite+aiosqlite:///", "")
        return {
            "type": "SQLite",
            "path": path,
        }
    else:
        # Hide credentials in URL
        safe_url = url
        if "@" in url:
            parts = url.split("@")
            safe_url = parts[0].split("://")[0] + "://***@" + parts[1]
        return {
            "type": "PostgreSQL",
            "url": safe_url,
        }


# Print connection info on import
print(f"Database: {get_db_info()}")

"""# =============================================================================
# CodeForge AI - SQLite Database Adapter
# =============================================================================
# Provides SQLite support for HuggingFace Spaces deployment.
# Handles SQLite-specific configurations and migrations.
# =============================================================================
"""

import os
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Check if we should use SQLite
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "")


def is_sqlite() -> bool:
    """Check if we're using SQLite."""
    return USE_SQLITE or DATABASE_URL.startswith("sqlite")


def get_sqlite_url(db_path: Optional[str] = None) -> str:
    """Get SQLite database URL."""
    if db_path:
        path = Path(db_path)
    else:
        # Default path for HuggingFace Spaces
        data_dir = Path("/app/data")
        if not data_dir.exists():
            data_dir = Path.home() / ".codeforge"
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "codeforge.db"
    
    return f"sqlite+aiosqlite:///{path}"


def create_sqlite_engine(url: str):
    """Create SQLite-optimized async engine."""
    engine = create_async_engine(
        url,
        echo=os.getenv("DEBUG", "false").lower() == "true",
        # SQLite-specific settings
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Single connection for SQLite
    )
    
    # Enable WAL mode and other optimizations
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # Write-Ahead Logging for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        # Increase cache size (in KB)
        cursor.execute("PRAGMA cache_size=-64000")
        # Synchronous mode - NORMAL is a good balance
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Temp store in memory
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
    
    return engine


async def init_sqlite_db(engine, Base):
    """Initialize SQLite database with all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"SQLite database initialized")


async def migrate_postgres_to_sqlite(
    postgres_url: str,
    sqlite_path: str
) -> bool:
    """Migrate data from PostgreSQL to SQLite.
    
    Useful for users who want to switch to HF Spaces from a PostgreSQL setup.
    """
    from sqlalchemy import create_engine, MetaData, Table
    from sqlalchemy.orm import Session
    
    print("Starting PostgreSQL to SQLite migration...")
    
    try:
        # Connect to PostgreSQL
        pg_engine = create_engine(postgres_url)
        metadata = MetaData()
        metadata.reflect(bind=pg_engine)
        
        # Create SQLite engine
        sqlite_url = f"sqlite:///{sqlite_path}"
        sqlite_engine = create_engine(sqlite_url)
        
        # Create all tables in SQLite
        metadata.create_all(bind=sqlite_engine)
        
        # Copy data
        with Session(pg_engine) as pg_session, Session(sqlite_engine) as sqlite_session:
            for table_name in metadata.tables:
                table = metadata.tables[table_name]
                rows = pg_session.execute(table.select()).fetchall()
                
                if rows:
                    print(f"  Migrating {len(rows)} rows from {table_name}")
                    # Insert in batches
                    for i in range(0, len(rows), 100):
                        batch = rows[i:i+100]
                        sqlite_session.execute(
                            table.insert(),
                            [dict(row._mapping) for row in batch]
                        )
                    sqlite_session.commit()
        
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False


def get_connection_info() -> dict:
    """Get current database connection information."""
    db_url = DATABASE_URL or get_sqlite_url()
    
    if is_sqlite():
        # Extract path from URL
        path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
        db_exists = Path(path).exists() if path else False
        size = Path(path).stat().st_size if db_exists else 0
        
        return {
            "type": "SQLite",
            "path": path,
            "exists": db_exists,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2) if size else 0,
            "url": db_url
        }
    else:
        return {
            "type": "PostgreSQL",
            "url": db_url.replace(db_url.split("@")[0].split("//")[1], "***") if "@" in db_url else db_url,
            "host": db_url.split("@")[1].split("/")[0] if "@" in db_url else "unknown"
        }


# CLI for database operations
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SQLite Database Utilities")
    parser.add_argument("--info", action="store_true", help="Show database info")
    parser.add_argument("--migrate", help="Migrate from PostgreSQL URL")
    parser.add_argument("--output", help="SQLite output path for migration")
    
    args = parser.parse_args()
    
    if args.info:
        import json
        print(json.dumps(get_connection_info(), indent=2))
    
    elif args.migrate and args.output:
        asyncio.run(migrate_postgres_to_sqlite(args.migrate, args.output))
    
    else:
        parser.print_help()

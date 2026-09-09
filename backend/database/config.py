"""
PostgreSQL Database Configuration and Session Management
Handles connection string resolution, environment variable loading via dotenv,
SQLAlchemy engine initialization with connection pooling, and session management.
"""

import os
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env from project root if present
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

Base = declarative_base()

def get_database_url() -> str:
    """Builds and normalizes PostgreSQL database connection URL"""
    custom_url = os.getenv("DATABASE_URL")
    if custom_url:
        # Normalize postgres:// to postgresql:// (for compatibility with modern SQLAlchemy)
        if custom_url.startswith("postgres://"):
            custom_url = custom_url.replace("postgres://", "postgresql://", 1)
        return custom_url

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "social_intelligence")
    ssl_mode = os.getenv("POSTGRES_SSLMODE")

    url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    if ssl_mode:
        url += f"?sslmode={ssl_mode}"
    return url

DATABASE_URL = get_database_url()
engine = None
SessionLocal = None

def init_engine(db_url: Optional[str] = None):
    """Initializes or re-initializes the SQLAlchemy Engine & SessionLocal"""
    global DATABASE_URL, engine, SessionLocal
    if db_url:
        DATABASE_URL = db_url
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = get_database_url()

    try:
        engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args={"connect_timeout": 15}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine
    except Exception as e:
        engine = None
        SessionLocal = None
        return None

# Initialize default engine
init_engine()

def get_db():
    """FastAPI Dependency for database sessions"""
    if SessionLocal is None:
        return None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

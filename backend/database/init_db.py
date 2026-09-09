"""
PostgreSQL Database Setup, Migration & Initialization CLI Utility
Provides automated database creation, table migrations, schema verification, and data seeding.

Usage:
    python -m backend.database.init_db
    python -m backend.database.init_db --seed
    python -m backend.database.init_db --check
"""

import sys
import os
import argparse
import time
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text, inspect

from backend.database.config import DATABASE_URL, get_database_url, init_engine, Base
from backend.database.models import PostRecord, NetworkInteractionRecord, TrendingTopicRecord
from backend.database.postgres_repository import postgres_repo

SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"

def parse_pg_url(url: str):
    """Extracts connection parameters from a PostgreSQL URL"""
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        parsed = urlparse(url)
        return {
            "user": parsed.username or "postgres",
            "password": parsed.password or "postgres",
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "dbname": parsed.path.lstrip("/") or "social_intelligence"
        }
    return {
        "user": "postgres",
        "password": "postgres",
        "host": "localhost",
        "port": 5432,
        "dbname": "social_intelligence"
    }

def create_database_if_not_exists(db_url: str = None) -> bool:
    """Connects to default postgres DB and creates the target database if missing"""
    target_url = db_url or get_database_url()
    params = parse_pg_url(target_url)
    target_db = params["dbname"]

    print(f"[*] Checking PostgreSQL server at {params['host']}:{params['port']}...")
    try:
        # Connect to administrative 'postgres' database
        conn = psycopg2.connect(
            dbname="postgres",
            user=params["user"],
            password=params["password"],
            host=params["host"],
            port=params["port"],
            connect_timeout=5
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if target database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (target_db,))
        exists = cursor.fetchone()

        if not exists:
            print(f"[*] Database '{target_db}' does not exist. Creating database...")
            cursor.execute(f'CREATE DATABASE "{target_db}";')
            print(f"[+] Database '{target_db}' created successfully.")
        else:
            print(f"[+] Database '{target_db}' already exists.")

        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[-] Notice during database check: {e}")
        return False

def apply_schema_and_tables(db_url: str = None) -> bool:
    """Creates tables via SQLAlchemy models and executes schema.sql indexes"""
    engine = init_engine(db_url)
    if engine is None:
        print("[-] Error: SQLAlchemy engine could not be created.")
        return False

    try:
        print("[*] Creating tables from SQLAlchemy models...")
        Base.metadata.create_all(bind=engine)
        print("[+] Tables mapped: post_records, network_interactions, trending_topics")

        # Execute raw SQL schema script for custom indexes and definitions
        if SCHEMA_SQL_PATH.exists():
            print(f"[*] Applying SQL schema script from {SCHEMA_SQL_PATH.name}...")
            with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            with engine.connect() as conn:
                for statement in schema_sql.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        try:
                            conn.execute(text(stmt))
                        except Exception:
                            pass
                conn.commit()
            print("[+] SQL schema script applied.")

        # Re-initialize postgres repository
        postgres_repo.init_db()
        return True
    except Exception as e:
        print(f"[-] Error applying schema: {e}")
        return False

def verify_tables() -> bool:
    """Inspects tables and columns in PostgreSQL database"""
    from backend.database.config import engine
    if engine is None:
        print("[-] Engine is not connected.")
        return False

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n[+] Verified Tables in PostgreSQL ({len(tables)} found):")
        for table in tables:
            cols = [col["name"] for col in inspector.get_columns(table)]
            print(f"    - {table} ({len(cols)} columns: {', '.join(cols[:5])}...)")
        return True
    except Exception as e:
        print(f"[-] Verification error: {e}")
        return False

def seed_sample_data(count: int = 50):
    """Seeds synthetic multi-platform posts into PostgreSQL"""
    print(f"\n[*] Seeding {count} realistic AI social media records into PostgreSQL...")
    from backend.ingestion.connectors import INFLUENCERS_AND_USERS, STREAM_CORPUS
    from backend.ml.sentiment_engine import sentiment_engine
    from backend.ml.demographic_engine import demographic_engine
    import random

    now = time.time()
    inserted = 0
    for i in range(count):
        author = random.choice(INFLUENCERS_AND_USERS)
        template = random.choice(STREAM_CORPUS)
        t = now - (count - i) * 15

        sent = sentiment_engine.analyze(template["text"])
        demo = demographic_engine.infer_profile(author.get("bio", ""), template["text"], author.get("location", ""))

        post_data = {
            "id": f"init_seed_{i+1:04d}",
            "platform": template["platform"],
            "text": template["text"],
            "author": author,
            "timestamp_epoch": t,
            "timestamp_iso": time.strftime('%H:%M:%S', time.localtime(t)),
            "sentiment": sent,
            "demographics": demo,
            "engagement": {
                "likes": random.randint(15, 3200),
                "shares": random.randint(4, 850),
                "replies": random.randint(1, 420)
            },
            "target_user": template.get("target_user"),
            "interaction_type": template.get("interaction", "retweet")
        }

        if postgres_repo.insert_post(post_data):
            inserted += 1

        if post_data["target_user"] and post_data["target_user"] != author["username"]:
            postgres_repo.insert_interaction(
                source_user=author["username"],
                target_user=post_data["target_user"],
                interaction_type=post_data["interaction_type"],
                sentiment=sent["valence"],
                timestamp=t
            )

    print(f"[+] Successfully seeded {inserted}/{count} records into PostgreSQL.")

def sync_real_users_to_postgres() -> int:
    """Synchronizes all authentic multi-platform real users into PostgreSQL real_users table"""
    print("\n[*] Synchronizing all 140+ authentic real users into PostgreSQL 'real_users' table...")
    from backend.ingestion.real_connectors import real_user_manager
    count = postgres_repo.sync_all_real_users(real_user_manager.users)
    print(f"[+] Successfully synchronized {count} real user profiles into PostgreSQL.")
    return count

def check_status():
    """Prints current database health check and diagnostics"""
    print("\n================ PostgreSQL Health Diagnostics ================")
    url = get_database_url()
    try:
        parsed = urlparse(url)
        masked_netloc = f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
        masked_url = f"{parsed.scheme}://{masked_netloc}{parsed.path}"
    except Exception:
        masked_url = url

    print(f"[*] Target Connection URL: {masked_url}")
    health = postgres_repo.check_health()
    print(f"[*] Status: {health.get('status', 'unknown').upper()}")
    print(f"[*] Details: {health}")
    print("===============================================================\n")

def main():
    parser = argparse.ArgumentParser(description="PostgreSQL Database Initializer and Management CLI")
    parser.add_argument("--url", type=str, default=None, help="Custom PostgreSQL Connection URL")
    parser.add_argument("--check", action="store_true", help="Run database health diagnostics only")
    parser.add_argument("--seed", action="store_true", help="Seed sample dataset after schema initialization")
    parser.add_argument("--sync-users", action="store_true", help="Synchronize all real users into real_users table")
    parser.add_argument("--count", type=int, default=50, help="Number of seed records to insert")
    args = parser.parse_args()

    if args.url:
        os.environ["DATABASE_URL"] = args.url

    if args.check:
        check_status()
        return

    print("===============================================================")
    print("       AETHERIA // PostgreSQL Database Provisioning Tool        ")
    print("===============================================================")

    # Step 1: Ensure database exists
    create_database_if_not_exists(args.url)

    # Step 2: Apply schema and create tables
    success = apply_schema_and_tables(args.url)

    if success:
        # Step 3: Verify tables
        verify_tables()

        # Step 4: Sync all real users
        sync_real_users_to_postgres()

        # Step 5: Seed posts if requested
        if args.seed:
            seed_sample_data(args.count)

        # Step 6: Final health check
        check_status()
        print("[+] PostgreSQL Database setup and data storage completed successfully!")
    else:
        print("\n[-] Setup notice: PostgreSQL is currently unreachable on the configured host/port.")
        print("[!] Tip: Set your PostgreSQL connection in .env or pass --url.")
        print("    Example: python -m backend.database.init_db --url postgresql://postgres:password@localhost:5432/social_intelligence")
        check_status()

if __name__ == "__main__":
    main()


"""
Automated Unit Tests for PostgreSQL Database Layer & Repository
"""

import unittest
import time
from backend.database.config import Base, DATABASE_URL
from backend.database.models import PostRecord, NetworkInteractionRecord, TrendingTopicRecord
from backend.database.postgres_repository import PostgresRepository
from backend.database.memory_db import timeline_db

class TestPostgresDatabase(unittest.TestCase):

    def test_database_url_and_config(self):
        """Verify PostgreSQL configuration loads valid dialect prefix"""
        self.assertTrue(DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgresql+psycopg2://"))

    def test_models_metadata(self):
        """Verify SQLAlchemy relational model declarations and table mapping"""
        tables = Base.metadata.tables
        self.assertIn("post_records", tables)
        self.assertIn("network_interactions", tables)
        self.assertIn("trending_topics", tables)
        
        post_table = tables["post_records"]
        self.assertIn("platform", post_table.columns)
        self.assertIn("sentiment_valence", post_table.columns)
        self.assertIn("primary_emotion", post_table.columns)
        self.assertIn("sarcasm_detected", post_table.columns)
        self.assertIn("inferred_age_bracket", post_table.columns)

    def test_postgres_repository_health(self):
        """Verify repository health check method responds structured status"""
        repo = PostgresRepository()
        health = repo.check_health()
        self.assertIn("status", health)
        self.assertIn("database", health)
        self.assertEqual(health["database"], "PostgreSQL")

    def test_timeline_database_integration(self):
        """Verify timeline_db insert persists and aggregates correctly"""
        dummy_post = {
            "id": "pg_test_001",
            "platform": "X",
            "text": "PostgreSQL integration test for real-time social analytics!",
            "author": {
                "username": "tester_pg",
                "name": "DB Tester",
                "location": "San Francisco, USA",
                "role": "QA Engineer",
                "followers": 500
            },
            "timestamp_epoch": time.time(),
            "timestamp_iso": "12:00:00",
            "sentiment": {
                "sentiment_label": "Positive",
                "confidence_score": 0.95,
                "valence": 0.85,
                "primary_emotion": "joy",
                "sarcasm": {"is_sarcastic": False, "confidence": 0.05},
                "stance": {"label": "Supportive"}
            },
            "demographics": {
                "inferred_age_bracket": "25-34",
                "geographic_origin": "United States",
                "inferred_language": "English",
                "primary_interest": "Tech & AI"
            },
            "engagement": {
                "likes": 50,
                "shares": 10,
                "replies": 2
            }
        }
        timeline_db.insert(dummy_post)
        records = timeline_db.get_records(limit=10)
        self.assertTrue(any(r["id"] == "pg_test_001" for r in records))
        
        kpis = timeline_db.get_kpis()
        self.assertGreater(kpis["total_posts"], 0)

if __name__ == "__main__":
    unittest.main()

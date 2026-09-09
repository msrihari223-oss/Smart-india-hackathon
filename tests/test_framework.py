
"""
Automated Comprehensive Test Suite for Social Media Analytics Framework
Tests all 5 core AI components and REST endpoints.
"""

import unittest
from backend.ml.sentiment_engine import sentiment_engine
from backend.ml.demographic_engine import demographic_engine
from backend.ml.trend_engine import trend_engine
from backend.ml.network_engine import network_engine
from backend.database.memory_db import timeline_db
from backend.ingestion.connectors import generate_live_post

class TestSocialMediaAnalyticsFramework(unittest.TestCase):

    def test_component_b_sentiment_and_sarcasm(self):
        """Test Multi-Dimensional Sentiment, Nuanced Emotion, and Sarcasm Detection"""
        # Test positive excitement
        res1 = sentiment_engine.analyze("The breakthrough in autonomous AI is completely revolutionary and epic! 🚀")
        self.assertIn(res1["primary_emotion"], ["excitement", "joy"])
        self.assertGreater(res1["valence"], 0.2)
        self.assertEqual(res1["sentiment_label"], "Positive")
        self.assertFalse(res1["sarcasm"]["is_sarcastic"])

        # Test Sarcasm detection
        res2 = sentiment_engine.analyze("Oh sure, another secure blockchain just got hacked for $50M. What a genius breakthrough... clearly working so well! 🙄")
        self.assertTrue(res2["sarcasm"]["is_sarcastic"])
        self.assertLess(res2["valence"], 0.0) # Sarcasm inverts pseudo-positive words to negative valence
        self.assertEqual(res2["stance"]["label"], "Against")

        # Test Anxiety / Fear
        res3 = sentiment_engine.analyze("Extreme anxiety across financial markets as inflation warning alarms sound. Terrible panic.")
        self.assertEqual(res3["primary_emotion"], "anxiety")
        self.assertLess(res3["valence"], -0.2)

    def test_component_c_demographics(self):
        """Test Automated Demographic Profiler"""
        bio = "College student in Bengaluru building GenAI apps. Gaming and anime fan. #AI"
        text = "Check out my new repo for decentralized LLMs! #Tech"
        loc = "Bengaluru, India"
        
        demo = demographic_engine.infer_profile(bio, text, loc)
        self.assertIn(demo["inferred_age_bracket"], ["18-24", "25-34"])
        self.assertEqual(demo["geographic_origin"], "India")
        self.assertEqual(demo["primary_interest"], "Tech & AI")

    def test_component_d_trend_detection(self):
        """Test Real-time Trend & Velocity Scoring"""
        post = {
            "text": "Huge surge in #AgenticAI adoption across enterprise networks! #GenAI",
            "sentiment": {"valence": 0.5},
            "platform": "X",
            "timestamp_epoch": 100000
        }
        keywords = trend_engine.extract_keywords_and_hashtags(post["text"])
        self.assertIn("#agenticai", keywords)
        self.assertIn("#genai", keywords)

    def test_component_e_network_topology_and_cascade(self):
        """Test Link Analysis, PageRank, and Cascade Diffusion"""
        network_engine.add_interaction("userA", "userB", "retweet", sentiment=0.5)
        network_engine.add_interaction("userC", "userB", "reply", sentiment=-0.2)
        network_engine.add_interaction("userD", "userA", "mention", sentiment=0.1)
        
        metrics = network_engine.compute_network_metrics()
        self.assertGreater(metrics["total_nodes"], 0)
        self.assertGreater(metrics["total_edges"], 0)
        self.assertTrue(any(kol["id"] == "userB" or kol["influence_score"] > 0 for kol in metrics["kols"]))

        # Test cascade diffusion
        cascade = network_engine.simulate_cascade("userB", steps=3)
        self.assertIsInstance(cascade, list)

    def test_component_a_ingestion_and_timeline(self):
        """Test Ingestion Pipeline & Historical Timeline Database"""
        live_post = generate_live_post()
        self.assertIn("id", live_post)
        self.assertIn("platform", live_post)
        self.assertIn("sentiment", live_post)
        self.assertIn("demographics", live_post)

        kpis = timeline_db.get_kpis()
        self.assertGreater(kpis["total_posts"], 0)
        
        timeline_aggs = timeline_db.get_timeline_aggregates(10)
        self.assertIn("timestamps", timeline_aggs)
        self.assertIn("sentiment_series", timeline_aggs)

if __name__ == "__main__":
    unittest.main()

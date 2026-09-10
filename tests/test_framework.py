"""
Automated Comprehensive Test Suite for Social Media Analytics Framework
Tests all core AI intelligence components, NLP accuracy, content moderation, and REST data pipelines.
"""

import unittest
from backend.ml.sentiment_engine import sentiment_engine, toxicity_engine
from backend.ml.demographic_engine import demographic_engine
from backend.ml.trend_engine import trend_engine
from backend.ml.network_engine import network_engine
from backend.database.memory_db import timeline_db
from backend.ingestion.connectors import generate_live_post

class TestSocialMediaAnalyticsFramework(unittest.TestCase):

    def test_sentiment_accuracy_and_emotion_distribution(self):
        """Test Multi-Dimensional Sentiment, Nuanced Emotion, and Sarcasm Detection"""
        # 1. Positive excitement
        res1 = sentiment_engine.analyze("The breakthrough in autonomous AI is completely revolutionary and epic! 🚀")
        self.assertIn(res1["primary_emotion"], ["excitement", "joy"])
        self.assertGreater(res1["valence"], 0.2)
        self.assertEqual(res1["sentiment_label"], "Positive")
        self.assertFalse(res1["sarcasm"]["is_sarcastic"])
        
        # Check emotion probabilities sum to ~1.0
        dist_sum = sum(res1["emotion_scores"].values())
        self.assertAlmostEqual(dist_sum, 1.0, places=2)

        # 2. Sarcasm detection & stance inversion
        res2 = sentiment_engine.analyze("Oh sure, another secure blockchain just got hacked for $50M. What a genius breakthrough... clearly working so well! 🙄")
        self.assertTrue(res2["sarcasm"]["is_sarcastic"])
        self.assertLess(res2["valence"], 0.0) # Sarcasm inverts pseudo-positive words to negative valence
        self.assertEqual(res2["stance"]["label"], "Against")

        # 3. Anxiety / Fear
        res3 = sentiment_engine.analyze("Extreme anxiety across financial markets as inflation warning alarms sound. Terrible panic.")
        self.assertEqual(res3["primary_emotion"], "anxiety")
        self.assertLess(res3["valence"], -0.2)

        # 4. Factual / Neutral statement
        res4 = sentiment_engine.analyze("The quarterly report will be presented on Tuesday at 10:00 AM in Conference Room B.")
        self.assertEqual(res4["primary_emotion"], "neutral")
        self.assertEqual(res4["sentiment_label"], "Neutral")
        self.assertAlmostEqual(res4["valence"], 0.0, delta=0.15)

        # 5. Multi-sentence negation boundary isolation (negation in sentence 1 must not spoil sentence 2)
        res5 = sentiment_engine.analyze("I was not able to attend yesterday. However, the keynote was fantastic and brilliant!")
        self.assertEqual(res5["sentiment_label"], "Positive")
        self.assertIn(res5["primary_emotion"], ["joy", "excitement", "supportive"])

    def test_toxicity_and_slang_whitelisting(self):
        """Test Content Moderation, Danger Words, and Slang Whitelist Protection"""
        # Benign slang should NOT be flagged as toxic
        safe_res = toxicity_engine.analyze_toxicity("This new AI feature is killing it! Slay queen, absolutely killer design and bomb food.")
        self.assertFalse(safe_res["is_toxic"])
        self.assertEqual(safe_res["severity"], "SAFE")

        # Real harassment / profanity should be flagged
        bad_res = toxicity_engine.analyze_toxicity("You are an absolute idiot and a loser, I hate you!")
        self.assertTrue(bad_res["is_toxic"])
        self.assertIn(bad_res["severity"], ["MEDIUM", "HIGH", "CRITICAL"])
        self.assertTrue(len(bad_res["detected_bad_words"]) > 0)

    def test_demographic_profiling(self):
        """Test Automated Demographic Profiler"""
        bio = "College student in Bengaluru building GenAI apps. Gaming and anime fan. #AI"
        text = "Check out my new repo for decentralized LLMs! #Tech"
        loc = "Bengaluru, India"
        
        demo = demographic_engine.infer_profile(bio, text, loc)
        self.assertIn(demo["inferred_age_bracket"], ["18-24", "25-34"])
        self.assertEqual(demo["geographic_origin"], "India")
        self.assertEqual(demo["primary_interest"], "Tech & AI")
        self.assertIn("age_distribution", demo)
        self.assertIn("interest_distribution", demo)

    def test_trend_detection_and_virality(self):
        """Test Real-time Trend & Velocity Scoring"""
        post = {
            "text": "Huge surge in #AgenticAI adoption across enterprise networks! #GenAI",
            "sentiment": {"valence": 0.5, "primary_emotion": "excitement"},
            "platform": "X",
            "timestamp_epoch": 100000
        }
        keywords = trend_engine.extract_keywords_and_hashtags(post["text"])
        self.assertTrue(any("agenticai" in k.lower() for k in keywords))
        self.assertTrue(any("genai" in k.lower() for k in keywords))

        trends = trend_engine.get_trending_topics()
        self.assertGreater(len(trends), 0)
        self.assertIn("virality_score", trends[0])
        self.assertIn("velocity", trends[0])
        self.assertIn("dominant_emotion", trends[0])

    def test_network_topology_and_cascade(self):
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

    def test_ingestion_and_timeline_db(self):
        """Test Ingestion Pipeline & Historical Timeline Database"""
        live_post = generate_live_post()
        self.assertIn("id", live_post)
        self.assertIn("platform", live_post)
        self.assertIn("sentiment", live_post)
        self.assertIn("demographics", live_post)

        timeline_db.insert(live_post)
        kpis = timeline_db.get_kpis()
        self.assertGreater(kpis["total_posts"], 0)
        
        timeline_aggs = timeline_db.get_timeline_aggregates(10)
        self.assertIn("timestamps", timeline_aggs)
        self.assertIn("sentiment_series", timeline_aggs)
        self.assertIn("emotion_stacked", timeline_aggs)

if __name__ == "__main__":
    unittest.main()

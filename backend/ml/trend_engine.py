"""
Real-Time Trend & Topic Detection Engine
Extracts emerging topics, hashtags, semantic n-grams, calculates virality velocity scores,
and predicts rising narratives chronologically.
"""

import re
import time
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple
import numpy as np

class TrendEngine:
    def __init__(self, window_size: int = 500):
        self.window_size = window_size
        self.post_history: List[Dict[str, Any]] = []
        self.topic_snapshots: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "about", 
            "is", "are", "was", "were", "this", "that", "it", "of", "from", "by", "as", "be", 
            "have", "has", "had", "will", "would", "can", "could", "should", "just", "so", "than",
            "then", "there", "their", "they", "we", "you", "i", "he", "she", "what", "which", "who", "when"
        }

    def add_post(self, post: Dict[str, Any]):
        """
        Ingests a post into the trend window.
        """
        self.post_history.append(post)
        if len(self.post_history) > self.window_size:
            self.post_history.pop(0)

    def extract_keywords_and_hashtags(self, text: str) -> List[str]:
        """
        Extracts hashtags and salient 1-gram / 2-gram terms.
        """
        # 1. Extract Hashtags
        hashtags = [h.lower() for h in re.findall(r'#\w+', text)]
        
        # 2. Extract clean words
        clean_text = re.sub(r'http\S+|[^\w\s#]', ' ', text.lower())
        tokens = [w for w in clean_text.split() if len(w) > 3 and w not in self.stop_words]
        
        # Bigrams
        bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1)]
        
        return hashtags + tokens[:5] + bigrams[:3]

    def get_trending_topics(self) -> List[Dict[str, Any]]:
        """
        Computes real-time trends, velocity scores, sentiment alignment, and virality predictions.
        """
        if not self.post_history:
            return []

        now = time.time()
        # Divide history into recent window (last 60s) vs baseline
        recent_window_posts = [p for p in self.post_history if now - p.get("timestamp_epoch", now) <= 120]
        older_window_posts = [p for p in self.post_history if now - p.get("timestamp_epoch", now) > 120]

        recent_counts = Counter()
        recent_sentiments = defaultdict(list)
        recent_platforms = defaultdict(set)
        recent_posts_map = defaultdict(list)

        for p in recent_window_posts:
            text = p.get("text", "")
            sentiment_score = p.get("sentiment", {}).get("valence", 0.0)
            platform = p.get("platform", "X")
            
            # Extract hashtags & key topics
            extracted = self.extract_keywords_and_hashtags(text)
            for item in extracted:
                recent_counts[item] += 1
                recent_sentiments[item].append(sentiment_score)
                recent_platforms[item].add(platform)
                recent_posts_map[item].append(p.get("id"))

        older_counts = Counter()
        for p in older_window_posts:
            for item in self.extract_keywords_and_hashtags(p.get("text", "")):
                older_counts[item] += 1

        trends = []
        top_candidates = recent_counts.most_common(20)

        for topic, r_count in top_candidates:
            if r_count < 2:
                continue
                
            o_count = older_counts.get(topic, 0)
            
            # Velocity: rate of change of volume
            velocity = round((r_count - (o_count / 2.0)) / max(1, r_count + o_count) * 100, 1)
            
            # Virality Score (0 - 100)
            platform_multiplier = len(recent_platforms[topic]) / 4.0 # Cross-platform virality booster
            virality_score = min(99.9, max(10.0, round((r_count * 12.0) + (velocity * 0.4) + (platform_multiplier * 20), 1)))
            
            # Status: Emerging, Viral Surge, Steady, Declining
            if virality_score > 75:
                status = "Viral Surge 🔥"
            elif velocity > 25:
                status = "Emerging 🚀"
            elif velocity > 0:
                status = "Active ⚡"
            else:
                status = "Cooling ❄️"

            # Sentiment average
            sents = recent_sentiments.get(topic, [0.0])
            avg_sent = round(sum(sents) / len(sents), 2)
            sent_label = "Positive" if avg_sent > 0.15 else ("Negative" if avg_sent < -0.15 else "Neutral")

            trends.append({
                "topic": topic,
                "volume": r_count + o_count,
                "recent_volume": r_count,
                "velocity": velocity,
                "virality_score": virality_score,
                "status": status,
                "avg_sentiment": avg_sent,
                "sentiment_label": sent_label,
                "platforms": list(recent_platforms[topic]),
                "sample_post_count": len(recent_posts_map[topic])
            })

        # Sort by virality score
        trends.sort(key=lambda x: x["virality_score"], reverse=True)
        return trends[:12]

trend_engine = TrendEngine()

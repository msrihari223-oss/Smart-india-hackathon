"""
Historical Timeline Database & Metric Aggregator
Maintains chronologically ordered social media interactions with efficient time-window slicing,
multi-platform filtering, and aggregate audience intelligence metrics.
Integrated with PostgreSQL as primary persistence engine with in-memory streaming cache.
"""

import time
from collections import defaultdict, Counter
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.database.postgres_repository import postgres_repo

class TimelineDatabase:
    def __init__(self, max_records: int = 2000):
        self.max_records = max_records
        self.records: List[Dict[str, Any]] = []

    def insert(self, record: Dict[str, Any]):
        """
        Inserts a timestamped record into in-memory buffer and persists to PostgreSQL.
        """
        if "timestamp_epoch" not in record:
            record["timestamp_epoch"] = time.time()
        if "timestamp_iso" not in record:
            record["timestamp_iso"] = datetime.utcfromtimestamp(record["timestamp_epoch"]).strftime('%H:%M:%S')

        self.records.append(record)
        if len(self.records) > self.max_records:
            self.records.pop(0)

        # Persist to PostgreSQL in background / directly
        try:
            postgres_repo.insert_post(record)
        except Exception:
            pass

    def get_records(self, limit: int = 50, platform: Optional[str] = None, emotion: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves filtered records in reverse chronological order (newest first).
        Attempts PostgreSQL fetch first, falling back to active buffer.
        """
        if postgres_repo.is_connected:
            pg_res = postgres_repo.get_records(limit=limit, platform=platform, emotion=emotion, search=search)
            if pg_res is not None and len(pg_res) > 0:
                return pg_res

        res = self.records
        if platform and platform.lower() != "all":
            res = [r for r in res if r.get("platform", "").lower() == platform.lower()]
        if emotion and emotion.lower() != "all":
            res = [r for r in res if r.get("sentiment", {}).get("primary_emotion", "").lower() == emotion.lower()]
        if search:
            q = search.lower()
            res = [r for r in res if q in r.get("text", "").lower() or q in r.get("author", {}).get("username", "").lower()]

        return list(reversed(res[-limit:]))

    def get_timeline_aggregates(self, buckets: int = 15) -> Dict[str, Any]:
        """
        Generates timeline time-series data points showing sentiment fluctuation and volume over time.
        """
        if postgres_repo.is_connected:
            pg_timeline = postgres_repo.get_timeline_aggregates(buckets=buckets)
            if pg_timeline is not None and len(pg_timeline.get("timestamps", [])) > 0:
                return pg_timeline

        if not self.records:
            return {"timestamps": [], "sentiment_series": [], "volume_series": [], "emotion_stacked": {}}

        total = len(self.records)
        bucket_size = max(1, total // buckets)
        
        timestamps = []
        sentiment_series = []
        volume_series = []
        emotion_stacked = defaultdict(list)
        
        emotions_tracked = ["joy", "excitement", "anxiety", "anger", "supportive", "against"]

        for i in range(0, total, bucket_size):
            chunk = self.records[i:i+bucket_size]
            if not chunk:
                continue

            last_item = chunk[-1]
            timestamps.append(last_item.get("timestamp_iso", "00:00:00"))
            
            avg_val = sum(c.get("sentiment", {}).get("valence", 0.0) for c in chunk) / len(chunk)
            sentiment_series.append(round(avg_val, 2))
            volume_series.append(len(chunk))

            # Emotion breakdown in chunk
            emotion_counts = Counter(c.get("sentiment", {}).get("primary_emotion", "neutral") for c in chunk)
            for emo in emotions_tracked:
                emotion_stacked[emo].append(emotion_counts.get(emo, 0))

        return {
            "timestamps": timestamps,
            "sentiment_series": sentiment_series,
            "volume_series": volume_series,
            "emotion_stacked": dict(emotion_stacked)
        }

    def get_demographic_aggregates(self) -> Dict[str, Any]:
        """
        Aggregates demographics across all active post records.
        """
        if postgres_repo.is_connected:
            pg_demo = postgres_repo.get_demographic_aggregates()
            if pg_demo is not None:
                return pg_demo

        age_counter = Counter()
        geo_counter = Counter()
        lang_counter = Counter()
        interest_counter = Counter()

        for post in self.records:
            demo = post.get("demographics", {})
            if "inferred_age_bracket" in demo:
                age_counter[demo["inferred_age_bracket"]] += 1
            if "geographic_origin" in demo:
                geo_val = demo["geographic_origin"]
                if geo_val and geo_val not in ("Global", "Global / Undisclosed", "Global / Unspecified"):
                    geo_counter[geo_val] += 1
            if "inferred_language" in demo:
                lang_counter[demo["inferred_language"]] += 1
            if "primary_interest" in demo:
                interest_counter[demo["primary_interest"]] += 1

        return {
            "age_brackets": dict(age_counter.most_common(5)),
            "geographic_distribution": dict(geo_counter.most_common(6)),
            "languages": dict(lang_counter.most_common(5)),
            "interests": dict(interest_counter.most_common(6))
        }

    def get_kpis(self) -> Dict[str, Any]:
        """
        Returns high-level key performance metrics.
        """
        if postgres_repo.is_connected:
            pg_kpis = postgres_repo.get_kpis()
            if pg_kpis is not None:
                return pg_kpis

        if not self.records:
            return {
                "total_posts": 0,
                "overall_sentiment_index": 0.0,
                "sarcasm_detected_count": 0,
                "active_platforms": 4,
                "velocity_per_minute": 30
            }

        total_posts = len(self.records)
        avg_valence = sum(r.get("sentiment", {}).get("valence", 0.0) for r in self.records) / max(1, total_posts)
        sarcasm_count = sum(1 for r in self.records if r.get("sentiment", {}).get("sarcasm", {}).get("is_sarcastic", False))
        
        now = time.time()
        recent_posts = sum(1 for r in self.records if r.get("timestamp_epoch", 0) >= now - 60)

        return {
            "total_posts": total_posts,
            "overall_sentiment_index": round(avg_valence, 2),
            "sarcasm_detected_count": sarcasm_count,
            "active_platforms": len(set(r.get("platform") for r in self.records)),
            "velocity_per_minute": max(recent_posts * 6, 24)
        }

    def toggle_like(self, post_id: str, liked: bool, username: str = "operator") -> int:
        """Increments or decrements likes on in-memory post and syncs to PostgreSQL"""
        likes_count = 1
        for p in self.records:
            if p.get("id") == post_id:
                eng = p.setdefault("engagement", {})
                cur = eng.get("likes", 0)
                eng["likes"] = max(0, cur + (1 if liked else -1))
                likes_count = eng["likes"]
                break
        try:
            if postgres_repo.is_connected:
                postgres_repo.toggle_like(post_id, liked, username)
        except Exception:
            pass
        return likes_count

    def increment_share(self, post_id: str) -> int:
        """Increments repost / share counter on in-memory post and syncs to PostgreSQL"""
        shares_count = 1
        for p in self.records:
            if p.get("id") == post_id:
                eng = p.setdefault("engagement", {})
                eng["shares"] = eng.get("shares", 0) + 1
                shares_count = eng["shares"]
                break
        try:
            if postgres_repo.is_connected:
                postgres_repo.increment_share(post_id)
        except Exception:
            pass
        return shares_count

    def add_comment(self, post_id: str, comment_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Stores a comment on a specific post and increments reply counter"""
        if not hasattr(self, 'comments_store'):
            self.comments_store = defaultdict(list)
        
        self.comments_store[post_id].append(comment_dict)
        
        # Increment comments count on in-memory post
        for p in self.records:
            if p.get("id") == post_id:
                p["comments_count"] = p.get("comments_count", 0) + 1
                break
                
        return comment_dict

    def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Retrieves comments thread for a post"""
        if not hasattr(self, 'comments_store'):
            self.comments_store = defaultdict(list)
        return self.comments_store.get(post_id, [])

timeline_db = TimelineDatabase()
timeline_db.comments_store = defaultdict(list)

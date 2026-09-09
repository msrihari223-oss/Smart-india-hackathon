"""
PostgreSQL Repository & Analytical Aggregation Service
Executes CRUD operations, analytical rollups, demographic breakdowns,
network topology caching, and timeline bucket computations directly against PostgreSQL.
Includes connection pooling, offline circuit-breaker / cooldown, and graceful in-memory fallback.
"""

import time
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from sqlalchemy import func, desc, or_
from backend.database.config import SessionLocal, engine, Base, init_engine
from backend.database.models import PostRecord, NetworkInteractionRecord, TrendingTopicRecord, RealUserRecord, AppUserRecord, PostCommentRecord, PostLikeRecord

class PostgresRepository:
    def __init__(self):
        self.is_connected = False
        self.last_attempt_time = 0.0
        self.retry_cooldown = 30.0  # seconds between reconnect attempts when offline
        self.init_db()

    def init_db(self, force: bool = False) -> bool:
        """Initializes tables in PostgreSQL schema if database is reachable"""
        now = time.time()
        if not force and not self.is_connected and (now - self.last_attempt_time < self.retry_cooldown):
            return False

        self.last_attempt_time = now
        if engine is None:
            self.is_connected = False
            return False
        try:
            Base.metadata.create_all(bind=engine)
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def reconnect(self, custom_url: Optional[str] = None) -> bool:
        """Re-establishes database connection with updated credentials"""
        init_engine(custom_url)
        return self.init_db(force=True)

    def check_health(self) -> Dict[str, Any]:
        """Check connection health and record counts across all tables"""
        try:
            if not self.is_connected:
                self.init_db()

            if not self.is_connected or SessionLocal is None:
                return {
                    "status": "offline",
                    "database": "PostgreSQL",
                    "error": "Cannot connect to PostgreSQL host. In-memory storage & streaming fallback active."
                }
            
            with SessionLocal() as db:
                count = db.query(func.count(PostRecord.id)).scalar() or 0
                comments_count = db.query(func.count(PostCommentRecord.id)).scalar() or 0
                likes_count = db.query(func.count(PostLikeRecord.id)).scalar() or 0
                users_count = db.query(func.count(AppUserRecord.id)).scalar() or 0
                interactions = db.query(func.count(NetworkInteractionRecord.id)).scalar() or 0
                trends = db.query(func.count(TrendingTopicRecord.id)).scalar() or 0
                real_users_count = db.query(func.count(RealUserRecord.id)).scalar() or 0
                return {
                    "status": "connected",
                    "database": "PostgreSQL",
                    "tables": {
                        "post_records": count,
                        "post_comments": comments_count,
                        "post_likes": likes_count,
                        "app_users": users_count,
                        "real_users": real_users_count,
                        "network_interactions": interactions,
                        "trending_topics": trends
                    }
                }
        except Exception as e:
            self.is_connected = False
            return {"status": "offline", "database": "PostgreSQL", "error": str(e)}

    def save_real_user(self, u: Dict[str, Any]) -> bool:
        """Persists or updates a real user profile in PostgreSQL database"""
        if not self.is_connected or SessionLocal is None:
            return False
        try:
            record = RealUserRecord(
                id=u.get("id"),
                platform=u.get("platform", "Unknown"),
                username=u.get("username", ""),
                name=u.get("name", ""),
                bio=u.get("bio", ""),
                location=u.get("location", ""),
                followers=u.get("followers", 0),
                avatar=u.get("avatar", ""),
                profile_url=u.get("profile_url", ""),
                demographics=u.get("demographics", {}),
                posts_count=u.get("posts_count", 1),
                sentiment_avg=u.get("sentiment_avg", 0.0),
                primary_emotion=u.get("primary_emotion", "neutral"),
                recent_posts=u.get("recent_posts", []),
                first_seen=u.get("first_seen", time.time()),
                last_active=u.get("last_active", time.time())
            )
            with SessionLocal() as db:
                db.merge(record)
                db.commit()
            return True
        except Exception:
            return False

    def sync_all_real_users(self, users_dict: Dict[str, Any]) -> int:
        """Bulk persists all registered in-memory real users into PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return 0
        saved_count = 0
        try:
            with SessionLocal() as db:
                for u in users_dict.values():
                    rec = RealUserRecord(
                        id=u.get("id"),
                        platform=u.get("platform", "Unknown"),
                        username=u.get("username", ""),
                        name=u.get("name", ""),
                        bio=u.get("bio", ""),
                        location=u.get("location", ""),
                        followers=u.get("followers", 0),
                        avatar=u.get("avatar", ""),
                        profile_url=u.get("profile_url", ""),
                        demographics=u.get("demographics", {}),
                        posts_count=u.get("posts_count", 1),
                        sentiment_avg=u.get("sentiment_avg", 0.0),
                        primary_emotion=u.get("primary_emotion", "neutral"),
                        recent_posts=u.get("recent_posts", []),
                        first_seen=u.get("first_seen", time.time()),
                        last_active=u.get("last_active", time.time())
                    )
                    db.merge(rec)
                    saved_count += 1
                db.commit()
            return saved_count
        except Exception:
            return saved_count


    def insert_post(self, post_data: Dict[str, Any]) -> bool:
        """Persists a new post record with full ML analytics into PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return False
        try:
            author = post_data.get("author", {})
            sentiment = post_data.get("sentiment", {})
            sarcasm = sentiment.get("sarcasm", {})
            demographics = post_data.get("demographics", {})
            engagement = post_data.get("engagement", {})

            record = PostRecord(
                id=post_data.get("id"),
                platform=post_data.get("platform", "Unknown"),
                text=post_data.get("text", ""),
                author_username=author.get("username"),
                author_name=author.get("name"),
                author_bio=author.get("bio"),
                author_location=author.get("location"),
                author_followers=author.get("followers", 0),
                author_avatar=author.get("avatar"),
                author_role=author.get("role"),
                timestamp_epoch=post_data.get("timestamp_epoch", time.time()),
                timestamp_iso=post_data.get("timestamp_iso", time.strftime('%H:%M:%S')),
                sentiment_label=sentiment.get("sentiment_label"),
                sentiment_score=sentiment.get("confidence_score", 0.0),
                sentiment_valence=sentiment.get("valence", 0.0),
                primary_emotion=sentiment.get("primary_emotion"),
                sarcasm_detected=sarcasm.get("is_sarcastic", False),
                sarcasm_confidence=sarcasm.get("confidence", 0.0),
                stance=sentiment.get("stance", {}).get("label") if isinstance(sentiment.get("stance"), dict) else str(sentiment.get("stance", "")),
                inferred_age_bracket=demographics.get("inferred_age_bracket"),
                geographic_origin=demographics.get("geographic_origin"),
                inferred_language=demographics.get("inferred_language"),
                primary_interest=demographics.get("primary_interest"),
                likes_count=engagement.get("likes", 0),
                shares_count=engagement.get("shares", 0),
                replies_count=engagement.get("replies", 0),
                target_user=post_data.get("target_user"),
                interaction_type=post_data.get("interaction_type"),
                media_type=post_data.get("media_type", "none"),
                media_url=post_data.get("media_url"),
                comments_count=post_data.get("comments_count", 0),
                raw_payload=post_data
            )

            with SessionLocal() as db:
                db.merge(record)
                db.commit()
            return True
        except Exception:
            self.is_connected = False
            return False

    def insert_comment(self, comment_data: Dict[str, Any]) -> bool:
        """Persists a comment record with AI toxicity audit into PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return False
        try:
            record = PostCommentRecord(
                id=comment_data.get("id"),
                post_id=comment_data.get("post_id"),
                author_username=comment_data.get("author_username", "anonymous"),
                author_name=comment_data.get("author_name", "Anonymous"),
                author_avatar=comment_data.get("author_avatar", ""),
                author_role=comment_data.get("author_role", "Citizen"),
                text=comment_data.get("text", ""),
                timestamp_epoch=comment_data.get("timestamp_epoch", time.time()),
                timestamp_iso=comment_data.get("timestamp_iso", time.strftime('%H:%M:%S')),
                sentiment_label=comment_data.get("sentiment_label", "neutral"),
                sentiment_score=comment_data.get("sentiment_score", 0.0),
                is_toxic=comment_data.get("is_toxic", False),
                severity=comment_data.get("severity", "SAFE"),
                detected_bad_words=comment_data.get("detected_bad_words", []),
                warning_issued=comment_data.get("warning_issued", False)
            )

            with SessionLocal() as db:
                db.merge(record)
                # Increment post comment count
                post_rec = db.query(PostRecord).filter(PostRecord.id == comment_data.get("post_id")).first()
                if post_rec:
                    post_rec.comments_count = (post_rec.comments_count or 0) + 1
                db.commit()
            return True
        except Exception:
            return False

    def toggle_like(self, post_id: str, liked: bool, username: str = "operator") -> int:
        """Records like in post_likes table and updates post_records.likes_count in PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return 1
        try:
            with SessionLocal() as db:
                like_id = f"like_{post_id}_{username}"
                if liked:
                    like_rec = PostLikeRecord(
                        id=like_id,
                        post_id=post_id,
                        username=username,
                        created_at_epoch=time.time(),
                        created_at_iso=time.strftime('%H:%M:%S')
                    )
                    db.merge(like_rec)
                else:
                    db.query(PostLikeRecord).filter(
                        PostLikeRecord.post_id == post_id,
                        PostLikeRecord.username == username
                    ).delete()
                
                # Update PostRecord likes_count
                post = db.query(PostRecord).filter(PostRecord.id == post_id).first()
                if post:
                    cur = post.likes_count or 0
                    post.likes_count = max(0, cur + (1 if liked else -1))
                    db.commit()
                    return post.likes_count
                else:
                    db.commit()
            return 1
        except Exception:
            return 1

    def increment_share(self, post_id: str) -> int:
        """Increments post share/repost count in PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return 1
        try:
            with SessionLocal() as db:
                post = db.query(PostRecord).filter(PostRecord.id == post_id).first()
                if post:
                    post.shares_count = (post.shares_count or 0) + 1
                    db.commit()
                    return post.shares_count
            return 1
        except Exception:
            return 1

    def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Fetches all comments for a given post from PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return []
        try:
            with SessionLocal() as db:
                records = db.query(PostCommentRecord).filter(
                    PostCommentRecord.post_id == post_id
                ).order_by(PostCommentRecord.timestamp_epoch.asc()).all()
                return [
                    {
                        "id": r.id,
                        "post_id": r.post_id,
                        "author_username": r.author_username,
                        "author_name": r.author_name,
                        "author_avatar": r.author_avatar,
                        "author_role": r.author_role,
                        "text": r.text,
                        "timestamp_epoch": r.timestamp_epoch,
                        "timestamp_iso": r.timestamp_iso,
                        "sentiment_label": r.sentiment_label,
                        "sentiment_score": r.sentiment_score,
                        "is_toxic": r.is_toxic,
                        "severity": r.severity,
                        "detected_bad_words": r.detected_bad_words,
                        "warning_issued": r.warning_issued
                    }
                    for r in records
                ]
        except Exception:
            return []

    def insert_interaction(self, source_user: str, target_user: str, interaction_type: str, sentiment: float, timestamp: float) -> bool:
        """Persists social graph interaction edge to PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return False
        try:
            record = NetworkInteractionRecord(
                source_user=source_user,
                target_user=target_user,
                interaction_type=interaction_type,
                sentiment=sentiment,
                timestamp_epoch=timestamp
            )
            with SessionLocal() as db:
                db.add(record)
                db.commit()
            return True
        except Exception:
            return False

    def upsert_trending_topic(self, topic: str, volume: int, velocity: float, virality_score: float, sentiment_score: float, dominant_emotion: str) -> bool:
        """Upserts a real-time trending topic metric into PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return False
        try:
            with SessionLocal() as db:
                existing = db.query(TrendingTopicRecord).filter(TrendingTopicRecord.topic == topic).first()
                if existing:
                    existing.volume = volume
                    existing.velocity = velocity
                    existing.virality_score = virality_score
                    existing.sentiment_score = sentiment_score
                    existing.dominant_emotion = dominant_emotion
                    existing.updated_at = time.time()
                else:
                    record = TrendingTopicRecord(
                        topic=topic,
                        volume=volume,
                        velocity=velocity,
                        virality_score=virality_score,
                        sentiment_score=sentiment_score,
                        dominant_emotion=dominant_emotion,
                        updated_at=time.time()
                    )
                    db.add(record)
                db.commit()
            return True
        except Exception:
            return False

    def get_records(self, limit: int = 50, platform: Optional[str] = None, emotion: Optional[str] = None, search: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Retrieves reverse-chronological filtered posts directly from PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return None
        try:
            with SessionLocal() as db:
                query = db.query(PostRecord)
                if platform and platform.lower() != "all":
                    query = query.filter(func.lower(PostRecord.platform) == platform.lower())
                if emotion and emotion.lower() != "all":
                    query = query.filter(func.lower(PostRecord.primary_emotion) == emotion.lower())
                if search:
                    q = f"%{search.lower()}%"
                    query = query.filter(
                        or_(
                            func.lower(PostRecord.text).like(q),
                            func.lower(PostRecord.author_username).like(q)
                        )
                    )

                results = query.order_by(desc(PostRecord.timestamp_epoch)).limit(limit).all()
                if not results:
                    return []

                posts = []
                for r in results:
                    if r.raw_payload:
                        posts.append(r.raw_payload)
                    else:
                        posts.append({
                            "id": r.id,
                            "platform": r.platform,
                            "text": r.text,
                            "author": {
                                "username": r.author_username,
                                "name": r.author_name,
                                "bio": r.author_bio,
                                "location": r.author_location,
                                "avatar": r.author_avatar,
                                "role": r.author_role,
                                "followers": r.author_followers
                            },
                            "timestamp_epoch": r.timestamp_epoch,
                            "timestamp_iso": r.timestamp_iso,
                            "sentiment": {
                                "sentiment_label": r.sentiment_label,
                                "confidence_score": r.sentiment_score,
                                "valence": r.sentiment_valence,
                                "primary_emotion": r.primary_emotion,
                                "sarcasm": {"is_sarcastic": r.sarcasm_detected, "confidence": r.sarcasm_confidence},
                                "stance": {"label": r.stance}
                            },
                            "demographics": {
                                "inferred_age_bracket": r.inferred_age_bracket,
                                "geographic_origin": r.geographic_origin,
                                "inferred_language": r.inferred_language,
                                "primary_interest": r.primary_interest
                            },
                            "engagement": {
                                "likes": r.likes_count,
                                "shares": r.shares_count,
                                "replies": r.replies_count
                            },
                            "target_user": r.target_user,
                            "interaction_type": r.interaction_type
                        })
                return posts
        except Exception:
            self.is_connected = False
            return None

    def get_timeline_aggregates(self, buckets: int = 15) -> Optional[Dict[str, Any]]:
        """Computes timeline aggregate metrics from PostgreSQL post records"""
        if not self.is_connected or SessionLocal is None:
            return None
        try:
            with SessionLocal() as db:
                records = db.query(PostRecord).order_by(PostRecord.timestamp_epoch.asc()).all()
                if not records or len(records) == 0:
                    return None

                total = len(records)
                bucket_size = max(1, total // buckets)
                timestamps = []
                sentiment_series = []
                volume_series = []
                emotion_stacked = defaultdict(list)
                emotions_tracked = ["joy", "excitement", "anxiety", "anger", "supportive", "against"]

                for i in range(0, total, bucket_size):
                    chunk = records[i:i+bucket_size]
                    if not chunk:
                        continue

                    last_item = chunk[-1]
                    timestamps.append(last_item.timestamp_iso or "00:00:00")
                    avg_val = sum(c.sentiment_valence or 0.0 for c in chunk) / len(chunk)
                    sentiment_series.append(round(avg_val, 2))
                    volume_series.append(len(chunk))

                    emotion_counts = Counter((c.primary_emotion or "neutral").lower() for c in chunk)
                    for emo in emotions_tracked:
                        emotion_stacked[emo].append(emotion_counts.get(emo, 0))

                return {
                    "timestamps": timestamps,
                    "sentiment_series": sentiment_series,
                    "volume_series": volume_series,
                    "emotion_stacked": dict(emotion_stacked)
                }
        except Exception:
            self.is_connected = False
            return None

    def get_demographic_aggregates(self) -> Optional[Dict[str, Any]]:
        """Computes aggregate demographics directly from PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return None
        try:
            with SessionLocal() as db:
                # Group by Age
                age_q = db.query(PostRecord.inferred_age_bracket, func.count(PostRecord.id))\
                          .filter(PostRecord.inferred_age_bracket.isnot(None))\
                          .group_by(PostRecord.inferred_age_bracket)\
                          .order_by(desc(func.count(PostRecord.id))).limit(5).all()

                # Group by Geo
                geo_q = db.query(PostRecord.geographic_origin, func.count(PostRecord.id))\
                          .filter(PostRecord.geographic_origin.isnot(None))\
                          .group_by(PostRecord.geographic_origin)\
                          .order_by(desc(func.count(PostRecord.id))).limit(6).all()

                # Group by Language
                lang_q = db.query(PostRecord.inferred_language, func.count(PostRecord.id))\
                           .filter(PostRecord.inferred_language.isnot(None))\
                           .group_by(PostRecord.inferred_language)\
                           .order_by(desc(func.count(PostRecord.id))).limit(5).all()

                # Group by Interest
                int_q = db.query(PostRecord.primary_interest, func.count(PostRecord.id))\
                          .filter(PostRecord.primary_interest.isnot(None))\
                          .group_by(PostRecord.primary_interest)\
                          .order_by(desc(func.count(PostRecord.id))).limit(6).all()

                if not age_q and not geo_q:
                    return None

                return {
                    "age_brackets": {k: v for k, v in age_q if k},
                    "geographic_distribution": {k: v for k, v in geo_q if k},
                    "languages": {k: v for k, v in lang_q if k},
                    "interests": {k: v for k, v in int_q if k}
                }
        except Exception:
            self.is_connected = False
            return None

    def get_trending_topics(self, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Retrieves trending topics ordered by virality score from PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return None
        try:
            with SessionLocal() as db:
                topics = db.query(TrendingTopicRecord)\
                           .order_by(desc(TrendingTopicRecord.virality_score))\
                           .limit(limit).all()
                if not topics:
                    return None

                return [
                    {
                        "topic": t.topic,
                        "volume": t.volume,
                        "velocity": t.velocity,
                        "virality_score": t.virality_score,
                        "sentiment_score": t.sentiment_score,
                        "dominant_emotion": t.dominant_emotion
                    }
                    for t in topics
                ]
        except Exception:
            self.is_connected = False
            return None

    def get_kpis(self) -> Optional[Dict[str, Any]]:
        """Aggregates platform KPIs from PostgreSQL"""
        if not self.is_connected or SessionLocal is None:
            return None
        try:
            with SessionLocal() as db:
                total_posts = db.query(func.count(PostRecord.id)).scalar() or 0
                if total_posts == 0:
                    return None

                avg_valence = db.query(func.avg(PostRecord.sentiment_valence)).scalar() or 0.0
                sarcasm_count = db.query(func.count(PostRecord.id)).filter(PostRecord.sarcasm_detected == True).scalar() or 0
                active_platforms = db.query(func.count(func.distinct(PostRecord.platform))).scalar() or 1

                now = time.time()
                recent_1m = db.query(func.count(PostRecord.id)).filter(PostRecord.timestamp_epoch >= now - 60).scalar() or 0

                return {
                    "total_posts": total_posts,
                    "overall_sentiment_index": round(float(avg_valence), 2),
                    "sarcasm_detected_count": sarcasm_count,
                    "active_platforms": active_platforms,
                    "velocity_per_minute": max(recent_1m * 6, 24)
                }
        except Exception:
            self.is_connected = False
            return None

postgres_repo = PostgresRepository()

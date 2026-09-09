"""
PostgreSQL SQLAlchemy Relational Models for SENTINEL-X Intelligence Platform
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, Index, BigInteger
from backend.database.config import Base

class PostRecord(Base):
    """
    Persisted Social Media Posts with Multi-Platform Ingestion,
    AI Sentiment Analysis, Emotion Breakdown, Sarcasm Detection, and Demographic Traits.
    """
    __tablename__ = "post_records"

    id = Column(String(64), primary_key=True, index=True)
    platform = Column(String(32), index=True, nullable=False)
    text = Column(Text, nullable=False)

    # Author metadata
    author_username = Column(String(64), index=True)
    author_name = Column(String(128))
    author_bio = Column(Text)
    author_location = Column(String(128))
    author_followers = Column(Integer, default=0)
    author_avatar = Column(String(256))
    author_role = Column(String(64))

    # Timestamps
    timestamp_epoch = Column(Float, index=True, nullable=False)
    timestamp_iso = Column(String(32))

    # Sentiment & Emotion Intelligence
    sentiment_label = Column(String(32), index=True)
    sentiment_score = Column(Float, default=0.0)
    sentiment_valence = Column(Float, default=0.0)
    primary_emotion = Column(String(32), index=True)
    sarcasm_detected = Column(Boolean, default=False, index=True)
    sarcasm_confidence = Column(Float, default=0.0)
    stance = Column(String(32))

    # Demographic Intelligence
    inferred_age_bracket = Column(String(32), index=True)
    geographic_origin = Column(String(64), index=True)
    inferred_language = Column(String(32), index=True)
    primary_interest = Column(String(64), index=True)

    # Engagement Counters
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    replies_count = Column(Integer, default=0)

    # Network relations
    target_user = Column(String(64), nullable=True, index=True)
    interaction_type = Column(String(32), nullable=True)

    # Media Attachments (Photos / Videos)
    media_type = Column(String(32), default="none")  # "none", "photo", "video"
    media_url = Column(Text, nullable=True)

    # Comments Counter
    comments_count = Column(Integer, default=0)

    # Full Raw JSON Payload
    raw_payload = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_platform_emotion", "platform", "primary_emotion"),
        Index("ix_time_platform", "timestamp_epoch", "platform"),
    )


class PostCommentRecord(Base):
    """
    Persisted Comments on Social Media Posts with AI Toxicity Moderation & Warning Audits.
    """
    __tablename__ = "post_comments"

    id = Column(String(64), primary_key=True, index=True)
    post_id = Column(String(64), index=True, nullable=False)
    author_username = Column(String(64), index=True, nullable=False)
    author_name = Column(String(128))
    author_avatar = Column(String(512))
    author_role = Column(String(64), default="Citizen")
    text = Column(Text, nullable=False)
    
    timestamp_epoch = Column(Float, index=True, nullable=False)
    timestamp_iso = Column(String(32))

    sentiment_label = Column(String(32), default="neutral")
    sentiment_score = Column(Float, default=0.0)

    # Moderation & Warning Intelligence
    is_toxic = Column(Boolean, default=False, index=True)
    severity = Column(String(32), default="SAFE")
    detected_bad_words = Column(JSON, nullable=True)
    warning_issued = Column(Boolean, default=False)


class NetworkInteractionRecord(Base):
    """
    Social Network Graph Interactions & Edge Weights
    """
    __tablename__ = "network_interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_user = Column(String(64), index=True, nullable=False)
    target_user = Column(String(64), index=True, nullable=False)
    interaction_type = Column(String(32), nullable=False)
    sentiment = Column(Float, default=0.0)
    timestamp_epoch = Column(Float, index=True, nullable=False)


class TrendingTopicRecord(Base):
    """
    Tracked Real-Time Trending Topics & Virality Velocity
    """
    __tablename__ = "trending_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(128), unique=True, index=True, nullable=False)
    volume = Column(Integer, default=1)
    velocity = Column(Float, default=0.0)
    virality_score = Column(Float, default=0.0)
    sentiment_score = Column(Float, default=0.0)
    dominant_emotion = Column(String(32), default="neutral")
    updated_at = Column(Float, nullable=False)


class RealUserRecord(Base):
    """
    Persisted Real User Profiles across Telegram, X, YouTube, Reddit, Facebook, Instagram
    """
    __tablename__ = "real_users"

    id = Column(String(128), primary_key=True, index=True)
    platform = Column(String(32), index=True, nullable=False)
    username = Column(String(128), index=True, nullable=False)
    name = Column(String(128))
    bio = Column(Text)
    location = Column(String(128))
    followers = Column(BigInteger, default=0)
    avatar = Column(String(512))
    profile_url = Column(String(512))
    demographics = Column(JSON, nullable=True)
    posts_count = Column(Integer, default=1)
    sentiment_avg = Column(Float, default=0.0)
    primary_emotion = Column(String(32), default="neutral")
    recent_posts = Column(JSON, nullable=True)
    first_seen = Column(Float, default=0.0)
    last_active = Column(Float, default=0.0, index=True)


class AppUserRecord(Base):
    """
    Application Users for Authentication, Security Clearance, and Role-Based Access Control.
    """
    __tablename__ = "app_users"

    id = Column(String(64), primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    phone_number = Column(String(32), index=True, nullable=True, default="")
    password_hash = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    full_name = Column(String(128), default="")
    role = Column(String(64), default="Analyst")  # Admin, Commander, Analyst, Operator
    clearance_level = Column(String(32), default="Level 3")
    avatar = Column(String(512), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(Float, nullable=False)
    last_login = Column(Float, nullable=False)


class PostLikeRecord(Base):
    """
    Persisted Post Likes mapping User interactions to Posts in PostgreSQL.
    """
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(64), index=True, nullable=False)
    username = Column(String(64), index=True, nullable=False)
    timestamp_epoch = Column(Float, nullable=False)

    __table_args__ = (
        Index("ix_post_likes_post_user", "post_id", "username"),
    )




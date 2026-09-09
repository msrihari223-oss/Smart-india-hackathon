-- PostgreSQL Schema for Social Media Intelligence & Analytics Framework (SENTINEL-X)

CREATE TABLE IF NOT EXISTS post_records (
    id VARCHAR(64) PRIMARY KEY,
    platform VARCHAR(32) NOT NULL,
    text TEXT NOT NULL,
    
    -- Author Details
    author_username VARCHAR(64),
    author_name VARCHAR(128),
    author_bio TEXT,
    author_location VARCHAR(128),
    author_followers INT DEFAULT 0,
    author_avatar VARCHAR(256),
    author_role VARCHAR(64),
    
    -- Timestamps
    timestamp_epoch DOUBLE PRECISION NOT NULL,
    timestamp_iso VARCHAR(32),
    
    -- Sentiment & Emotion
    sentiment_label VARCHAR(32),
    sentiment_score DOUBLE PRECISION DEFAULT 0.0,
    sentiment_valence DOUBLE PRECISION DEFAULT 0.0,
    primary_emotion VARCHAR(32),
    sarcasm_detected BOOLEAN DEFAULT FALSE,
    sarcasm_confidence DOUBLE PRECISION DEFAULT 0.0,
    stance VARCHAR(32),
    
    -- Demographics
    inferred_age_bracket VARCHAR(32),
    geographic_origin VARCHAR(64),
    inferred_language VARCHAR(32),
    primary_interest VARCHAR(64),
    
    -- Engagement
    likes_count INT DEFAULT 0,
    shares_count INT DEFAULT 0,
    replies_count INT DEFAULT 0,
    
    -- Network Links
    target_user VARCHAR(64),
    interaction_type VARCHAR(32),

    -- Media Attachments (Photos / Videos)
    media_type VARCHAR(32) DEFAULT 'none',
    media_url VARCHAR(1024),
    comments_count INT DEFAULT 0,
    
    -- Full Raw Payload
    raw_payload JSONB
);

-- Indexes for ultra-fast query and aggregate performance
CREATE INDEX IF NOT EXISTS ix_post_platform ON post_records(platform);
CREATE INDEX IF NOT EXISTS ix_post_timestamp ON post_records(timestamp_epoch DESC);
CREATE INDEX IF NOT EXISTS ix_post_emotion ON post_records(primary_emotion);
CREATE INDEX IF NOT EXISTS ix_post_author ON post_records(author_username);
CREATE INDEX IF NOT EXISTS ix_post_geo ON post_records(geographic_origin);
CREATE INDEX IF NOT EXISTS ix_post_platform_emotion ON post_records(platform, primary_emotion);

-- Post Comments & Moderation Audits Table
CREATE TABLE IF NOT EXISTS post_comments (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL,
    author_username VARCHAR(64) NOT NULL,
    author_name VARCHAR(128),
    author_avatar VARCHAR(512),
    author_role VARCHAR(64) DEFAULT 'Citizen',
    text TEXT NOT NULL,
    timestamp_epoch DOUBLE PRECISION NOT NULL,
    timestamp_iso VARCHAR(32),
    sentiment_label VARCHAR(32) DEFAULT 'neutral',
    sentiment_score DOUBLE PRECISION DEFAULT 0.0,
    is_toxic BOOLEAN DEFAULT FALSE,
    severity VARCHAR(32) DEFAULT 'SAFE',
    detected_bad_words JSONB,
    warning_issued BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_comment_post_id ON post_comments(post_id);
CREATE INDEX IF NOT EXISTS ix_comment_author ON post_comments(author_username);
CREATE INDEX IF NOT EXISTS ix_comment_time ON post_comments(timestamp_epoch DESC);

-- Network Interactions Table
CREATE TABLE IF NOT EXISTS network_interactions (
    id SERIAL PRIMARY KEY,
    source_user VARCHAR(64) NOT NULL,
    target_user VARCHAR(64) NOT NULL,
    interaction_type VARCHAR(32) NOT NULL,
    sentiment DOUBLE PRECISION DEFAULT 0.0,
    timestamp_epoch DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_net_source ON network_interactions(source_user);
CREATE INDEX IF NOT EXISTS ix_net_target ON network_interactions(target_user);
CREATE INDEX IF NOT EXISTS ix_net_time ON network_interactions(timestamp_epoch DESC);

-- Trending Topics Table
CREATE TABLE IF NOT EXISTS trending_topics (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(128) UNIQUE NOT NULL,
    volume INT DEFAULT 1,
    velocity DOUBLE PRECISION DEFAULT 0.0,
    virality_score DOUBLE PRECISION DEFAULT 0.0,
    sentiment_score DOUBLE PRECISION DEFAULT 0.0,
    dominant_emotion VARCHAR(32) DEFAULT 'neutral',
    updated_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_trend_virality ON trending_topics(virality_score DESC);

-- Real Users Table
CREATE TABLE IF NOT EXISTS real_users (
    id VARCHAR(128) PRIMARY KEY,
    platform VARCHAR(32) NOT NULL,
    username VARCHAR(128) NOT NULL,
    name VARCHAR(128),
    bio TEXT,
    location VARCHAR(128),
    followers BIGINT DEFAULT 0,
    avatar VARCHAR(512),
    profile_url VARCHAR(512),
    demographics JSONB,
    posts_count INT DEFAULT 1,
    sentiment_avg DOUBLE PRECISION DEFAULT 0.0,
    primary_emotion VARCHAR(32) DEFAULT 'neutral',
    recent_posts JSONB,
    first_seen DOUBLE PRECISION DEFAULT 0.0,
    last_active DOUBLE PRECISION DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS ix_real_user_platform ON real_users(platform);
CREATE INDEX IF NOT EXISTS ix_real_user_username ON real_users(username);
CREATE INDEX IF NOT EXISTS ix_real_user_active ON real_users(last_active DESC);

-- Application Users Table (Authentication & Access Control)
CREATE TABLE IF NOT EXISTS app_users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(128) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    full_name VARCHAR(128) DEFAULT '',
    role VARCHAR(64) DEFAULT 'Analyst',
    clearance_level VARCHAR(32) DEFAULT 'Level 3',
    avatar VARCHAR(512) DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DOUBLE PRECISION NOT NULL,
    last_login DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_app_user_username ON app_users(username);
CREATE INDEX IF NOT EXISTS ix_app_user_email ON app_users(email);

-- Post Likes Table (Automatic User Likes Persistence)
CREATE TABLE IF NOT EXISTS post_likes (
    id VARCHAR(128) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL,
    username VARCHAR(64) NOT NULL,
    created_at_epoch DOUBLE PRECISION NOT NULL,
    created_at_iso VARCHAR(32)
);

CREATE INDEX IF NOT EXISTS ix_post_likes_post_id ON post_likes(post_id);
CREATE INDEX IF NOT EXISTS ix_post_likes_user ON post_likes(username);
CREATE INDEX IF NOT EXISTS ix_post_likes_post_user ON post_likes(post_id, username);



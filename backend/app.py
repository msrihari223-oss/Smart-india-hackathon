"""
Main FastAPI Application & Real-Time Intelligence Server
Serves REST APIs, WebSocket live streams, and static frontend dashboard.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from pydantic import BaseModel

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.ingestion.stream_engine import stream_broadcaster
from backend.database.memory_db import timeline_db
from backend.database.postgres_repository import postgres_repo
from backend.ml.sentiment_engine import sentiment_engine
from backend.ml.demographic_engine import demographic_engine
from backend.ml.trend_engine import trend_engine
from backend.ml.network_engine import network_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Non-blocking PostgreSQL initialization & sync in background thread
    async def init_and_sync_db():
        try:
            await asyncio.to_thread(postgres_repo.init_db)
            from backend.ingestion.real_connectors import real_user_manager
            synced = await asyncio.to_thread(postgres_repo.sync_all_real_users, real_user_manager.users)
            
            # Auto sync real-time trending topics into PostgreSQL / Supabase
            trends = trend_engine.get_trending_topics()
            synced_trends = await asyncio.to_thread(postgres_repo.sync_all_trending_topics, trends)
            print(f"[+] Background DB ready: auto-synced {synced} real users & {synced_trends} trending topics to PostgreSQL!")
        except Exception as e:
            print(f"[!] Background DB initialization notice: {e}")

    asyncio.create_task(init_and_sync_db())
    # Start background live stream task
    broadcast_task = asyncio.create_task(stream_broadcaster.broadcast_live_event())
    yield
    # Cleanup
    stream_broadcaster.is_running = False
    broadcast_task.cancel()

app = FastAPI(
    title="AI-Driven Social Media Analytics Framework",
    description="Full-stack real-time intelligence platform covering Sentiment, Demographics, Trends, and Network Topology",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend Static Path
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# ----------------- WebSocket Live Stream -----------------

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await stream_broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client controls (e.g. speed change, pause)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        stream_broadcaster.disconnect(websocket)
    except Exception:
        stream_broadcaster.disconnect(websocket)

# ----------------- REST API Endpoints -----------------

@app.get("/api/db/health")
async def get_db_health():
    """Retrieve PostgreSQL Database Connection and Persistence Health Status"""
    return postgres_repo.check_health()

@app.post("/api/db/reconnect")
async def reconnect_db(db_url: Optional[str] = Query(None)):
    """Re-attempts connection to PostgreSQL host or updates connection URL dynamically"""
    success = postgres_repo.reconnect(db_url)
    return {"success": success, "health": postgres_repo.check_health()}

@app.get("/api/kpis")
async def get_kpis():
    """Retrieve top-level platform analytics KPIs"""
    return timeline_db.get_kpis()

@app.get("/api/feed")
@app.get("/api/live/stream")
async def get_feed(
    limit: int = Query(30, ge=1, le=100),
    platform: Optional[str] = Query(None),
    emotion: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Retrieve chronologically ordered social media feed with filters"""
    return timeline_db.get_records(limit=limit, platform=platform, emotion=emotion, search=search)

@app.get("/api/timeline")
async def get_timeline(buckets: int = Query(15, ge=5, le=50)):
    """Retrieve timeline sentiment fluctuation, volume, and stacked emotions over time"""
    return timeline_db.get_timeline_aggregates(buckets=buckets)

@app.get("/api/demographics")
async def get_demographics():
    """Retrieve aggregate demographic distributions: age, geo, language, interests"""
    return timeline_db.get_demographic_aggregates()

@app.get("/api/trends")
async def get_trends():
    """Retrieve real-time trending topics, virality scores, velocity, and sentiment"""
    return trend_engine.get_trending_topics()

@app.get("/api/network")
async def get_network():
    """Retrieve network topology: nodes, edges, KOLs, and community clusters"""
    return network_engine.compute_network_metrics()

@app.get("/api/network/cascade")
async def get_cascade(seed_user: Optional[str] = Query(None), steps: int = Query(4, ge=1, le=6)):
    """Simulate viral information cascade diffusion from a seed influencer"""
    return network_engine.simulate_cascade(start_node=seed_user or "tech_visionary", steps=steps)

# Custom Text Analysis Sandbox Request Model
class CustomAnalysisRequest(BaseModel):
    text: str
    user_bio: Optional[str] = ""
    location: Optional[str] = ""

@app.post("/api/analyze")
async def analyze_custom_post(req: CustomAnalysisRequest):
    """
    On-demand AI Deep Analyzer sandbox: runs full ML pipeline on any arbitrary post, bio, or handle.
    Includes comprehensive bad-word, toxic hashtag, and profanity moderation guardrails.
    """
    sentiment_res = sentiment_engine.analyze(req.text)
    demo_res = demographic_engine.infer_profile(req.user_bio or "", req.text, req.location or "")
    keywords = trend_engine.extract_keywords_and_hashtags(req.text)

    return {
        "text": req.text,
        "sentiment": sentiment_res,
        "demographics": demo_res,
        "extracted_topics": keywords,
        "toxicity": sentiment_res.get("toxicity", {})
    }

@app.post("/api/check-toxicity")
async def check_toxicity_fast(req: CustomAnalysisRequest):
    """
    Ultra-low-latency endpoint for live typing / instant bad-word and toxic hashtag detection.
    """
    from backend.ml.sentiment_engine import toxicity_engine
    return toxicity_engine.analyze_toxicity(req.text)


# ----------------- Media Posting & Interactive Comments Endpoints -----------------

class CreatePostRequest(BaseModel):
    text: str
    platform: Optional[str] = "X"
    media_type: Optional[str] = "none"  # "none", "photo", "video"
    media_url: Optional[str] = None
    author_name: Optional[str] = "Operator"
    author_username: Optional[str] = "operator"
    author_role: Optional[str] = "Intelligence Operator"
    author_avatar: Optional[str] = None
    location: Optional[str] = "Global Station"

class CreateCommentRequest(BaseModel):
    text: str
    author_username: Optional[str] = "operator"
    author_name: Optional[str] = "Operator"
    author_avatar: Optional[str] = None
    author_role: Optional[str] = "Analyst"
    force_publish: Optional[bool] = False

class ToggleLikeRequest(BaseModel):
    liked: bool = True
    username: Optional[str] = "operator"

class RepostRequest(BaseModel):
    author_username: Optional[str] = "operator"
    author_name: Optional[str] = "Operator"
    author_avatar: Optional[str] = None
    author_role: Optional[str] = "Analyst"
    commentary: Optional[str] = None

# Media Uploads Directory
UPLOAD_DIR = os.path.join(FRONTEND_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/media/upload")
async def upload_media_file(file: UploadFile = File(...)):
    """
    Receives user photo/video file upload, writes to disk, and returns the accessible URL
    for persistence in PostgreSQL database.
    """
    import uuid
    import shutil

    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"
    if not ext:
        ext = ".png" if "image" in (file.content_type or "") else ".mp4"

    clean_filename = f"media_{uuid.uuid4().hex[:12]}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, clean_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media_url = f"/static/uploads/{clean_filename}"
    media_type = "video" if any(ext.endswith(x) for x in [".mp4", ".webm", ".mov", ".avi", ".mkv"]) or ("video" in (file.content_type or "")) else "photo"

    return {
        "success": True,
        "media_url": media_url,
        "media_type": media_type,
        "filename": clean_filename
    }

@app.post("/api/posts/create")
async def create_user_post(req: CreatePostRequest):
    """
    Creates and broadcasts a new user post with optional Photo/Video attachments.
    Runs full AI NLP sentiment, demographic analysis, and stores in database & active stream.
    """
    import uuid
    import time
    from datetime import datetime

    post_id = f"post_usr_{uuid.uuid4().hex[:10]}"
    now_epoch = time.time()
    now_iso = datetime.fromtimestamp(now_epoch).strftime('%H:%M:%S')

    sentiment_res = sentiment_engine.analyze(req.text)
    demo_res = demographic_engine.infer_profile("", req.text, req.location or "Global Station")
    
    avatar = req.author_avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={req.author_username}"

    post_payload = {
        "id": post_id,
        "platform": req.platform or "X",
        "text": req.text,
        "media_type": req.media_type or ("photo" if req.media_url and any(req.media_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]) else ("video" if req.media_url else "none")),
        "media_url": req.media_url,
        "author": {
            "name": req.author_name or "Operator",
            "username": req.author_username or "operator",
            "bio": "Aetheria Intelligence Contributor",
            "location": req.location or "Global Station",
            "followers": 15400,
            "avatar": avatar,
            "role": req.author_role or "Intelligence Operator",
            "profile_url": "#"
        },
        "timestamp_epoch": now_epoch,
        "timestamp_iso": now_iso,
        "sentiment": sentiment_res,
        "demographics": demo_res,
        "engagement": {
            "likes": 1,
            "shares": 0,
            "replies": 0
        },
        "comments_count": 0,
        "raw_payload": None
    }

    # Store in memory & PostgreSQL
    timeline_db.insert(post_payload)

    # Broadcast live over WebSocket to all connected dashboard stations
    try:
        await stream_broadcaster.broadcast_custom_event({
            "type": "LIVE_POST",
            "post": post_payload,
            "kpis": timeline_db.get_kpis(),
            "trends": trend_engine.get_trending_topics()
        })
    except Exception:
        pass

    return {"success": True, "post": post_payload}


@app.get("/api/posts/{post_id}/comments")
async def get_post_comments(post_id: str):
    """Retrieve all comments on a post"""
    if postgres_repo.is_connected:
        comments = postgres_repo.get_comments(post_id)
        if comments:
            return {"post_id": post_id, "comments": comments}

    comments = timeline_db.get_comments(post_id)
    return {"post_id": post_id, "comments": comments}


@app.post("/api/posts/{post_id}/comments")
async def add_post_comment(post_id: str, req: CreateCommentRequest):
    """
    Submits a comment on a post with automated bad-word / toxic language moderation.
    If bad words, slurs, or harassment are detected, returns a moderation warning prompt.
    """
    import uuid
    import time
    from datetime import datetime
    from backend.ml.sentiment_engine import toxicity_engine

    # Step 1: AI Toxicity Moderation Check
    tox = toxicity_engine.analyze_toxicity(req.text)

    if tox["is_toxic"] and not req.force_publish:
        return {
            "success": False,
            "warning_required": True,
            "toxicity": tox,
            "message": "⚠️ Community Moderation Policy Violation: Toxic, abusive, or offensive language detected."
        }

    # Step 2: Sentiment score
    sent_res = sentiment_engine.analyze(req.text)

    comment_id = f"cmt_{uuid.uuid4().hex[:10]}"
    now_epoch = time.time()
    now_iso = datetime.fromtimestamp(now_epoch).strftime('%H:%M:%S')

    comment_dict = {
        "id": comment_id,
        "post_id": post_id,
        "author_username": req.author_username or "operator",
        "author_name": req.author_name or "Operator",
        "author_avatar": req.author_avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={req.author_username}",
        "author_role": req.author_role or "Analyst",
        "text": req.text,
        "timestamp_epoch": now_epoch,
        "timestamp_iso": now_iso,
        "sentiment_label": sent_res.get("sentiment_label", "neutral"),
        "sentiment_score": sent_res.get("valence", 0.0),
        "is_toxic": tox["is_toxic"],
        "severity": tox.get("severity", "SAFE"),
        "detected_bad_words": tox.get("detected_bad_words", []) + tox.get("detected_bad_hashtags", []),
        "warning_issued": tox["is_toxic"]
    }

    # Persist in memory & database
    timeline_db.add_comment(post_id, comment_dict)
    if postgres_repo.is_connected:
        postgres_repo.insert_comment(comment_dict)

    return {
        "success": True,
        "warning_required": False,
        "comment": comment_dict,
        "toxicity": tox
    }


@app.post("/api/posts/{post_id}/like")
async def toggle_post_like(post_id: str, req: ToggleLikeRequest):
    """
    Toggles user like state on a post, updates like counter and returns current total.
    """
    new_likes = timeline_db.toggle_like(post_id, req.liked, req.username or "operator")
    return {"success": True, "post_id": post_id, "likes": new_likes, "liked": req.liked}


@app.post("/api/posts/{post_id}/repost")
async def repost_post(post_id: str, req: RepostRequest):
    """
    Creates a Repost / Retweet of an existing post, increments original post's share count,
    and broadcasts the reposted post to the live ingestion stream.
    """
    import uuid
    import time
    from datetime import datetime

    # 1. Increment original post shares
    new_shares = timeline_db.increment_share(post_id)

    # 2. Find original post details
    orig_post = None
    for p in timeline_db.records:
        if p.get("id") == post_id:
            orig_post = p
            break

    orig_author = orig_post.get("author", {}).get("username", "user") if orig_post else "user"
    orig_text = orig_post.get("text", "") if orig_post else ""
    orig_media_type = orig_post.get("media_type", "none") if orig_post else "none"
    orig_media_url = orig_post.get("media_url") if orig_post else None
    platform = orig_post.get("platform", "X") if orig_post else "X"

    repost_text = req.commentary if req.commentary and req.commentary.strip() else f"RT @{orig_author}: {orig_text}"
    
    repost_id = f"repost_{uuid.uuid4().hex[:10]}"
    now_epoch = time.time()
    now_iso = datetime.fromtimestamp(now_epoch).strftime('%H:%M:%S')

    sentiment_res = sentiment_engine.analyze(repost_text)
    demo_res = demographic_engine.infer_profile("", repost_text, "Global Station")
    avatar = req.author_avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={req.author_username}"

    repost_payload = {
        "id": repost_id,
        "platform": platform,
        "text": repost_text,
        "media_type": orig_media_type,
        "media_url": orig_media_url,
        "interaction_type": "REPOST",
        "target_user": orig_author,
        "author": {
            "name": req.author_name or "Operator",
            "username": req.author_username or "operator",
            "bio": "Aetheria Intelligence Contributor",
            "location": "Global Station",
            "followers": 15400,
            "avatar": avatar,
            "role": req.author_role or "Intelligence Operator",
            "profile_url": "#"
        },
        "timestamp_epoch": now_epoch,
        "timestamp_iso": now_iso,
        "sentiment": sentiment_res,
        "demographics": demo_res,
        "engagement": {
            "likes": 1,
            "shares": 0,
            "replies": 0
        },
        "comments_count": 0,
        "raw_payload": None
    }

    timeline_db.insert(repost_payload)

    # Broadcast live over WebSocket
    try:
        await stream_broadcaster.broadcast_custom_event({
            "type": "LIVE_POST",
            "post": repost_payload,
            "kpis": timeline_db.get_kpis(),
            "trends": trend_engine.get_trending_topics()
        })
    except Exception:
        pass

    return {
        "success": True,
        "repost": repost_payload,
        "original_post_id": post_id,
        "original_shares": new_shares
    }


# ----------------- Real Users Intelligence Endpoints -----------------
from backend.ingestion.real_connectors import real_user_manager, real_user_fetcher
from fastapi.responses import Response
import csv
import io

@app.get("/api/real-users")
async def get_real_users(
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(60, ge=1, le=300)
):
    """Retrieve indexed real users across Telegram, X, Instagram, YouTube, Reddit"""
    # Ensure some initial users are indexed if empty
    if not real_user_manager.users:
        real_user_fetcher.refresh_real_stream_buffer()
        # Process a few to seed
        for _ in range(12):
            real_user_fetcher.get_next_real_post()

    users = real_user_manager.get_all_users(platform=platform, search=search, limit=limit)
    stats = real_user_manager.get_user_stats()
    return {
        "total_count": len(users),
        "stats": stats,
        "users": users
    }

@app.get("/api/real-users/stats")
async def get_real_user_stats():
    """Retrieve statistical summary of indexed real users by platform"""
    return real_user_manager.get_user_stats()

@app.post("/api/real-users/collect-now")
async def trigger_real_collection():
    """Immediately triggers a live multi-threaded crawl across Telegram, YouTube, Reddit, X, Instagram"""
    real_user_fetcher.refresh_real_stream_buffer()
    collected = []
    for _ in range(15):
        p = real_user_fetcher.get_next_real_post()
        if p:
            collected.append(p)
    return {
        "status": "success",
        "collected_posts_count": len(collected),
        "total_indexed_real_users": len(real_user_manager.users),
        "stats": real_user_manager.get_user_stats()
    }

@app.post("/api/real-users/sync-db")
async def sync_real_users_to_database():
    """Forces synchronization of all authentic real users directly into the PostgreSQL real_users table"""
    synced_count = postgres_repo.sync_all_real_users(real_user_manager.users)
    return {
        "status": "success",
        "synced_users_count": synced_count,
        "database": "PostgreSQL (Supabase)",
        "table": "real_users"
    }

@app.get("/api/real-users/export")
async def export_real_users(format: str = Query("json", pattern="^(json|csv)$")):
    """Export all collected real user data in JSON or CSV format for download"""
    users = real_user_manager.get_all_users(limit=1000)
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Platform", "Username", "Display Name", "Bio", "Location", "Followers/Karma",
            "Profile URL", "Inferred Age", "Inferred Geo", "Inferred Language", "Primary Interest",
            "Avg Sentiment Valence", "Primary Emotion", "Total Posts Collected"
        ])
        for u in users:
            demo = u.get("demographics", {})
            writer.writerow([
                u.get("platform", ""),
                u.get("username", ""),
                u.get("name", ""),
                u.get("bio", "").replace("\n", " "),
                u.get("location", ""),
                u.get("followers", 0),
                u.get("profile_url", ""),
                demo.get("inferred_age_bracket", "25-34"),
                demo.get("geographic_origin", "Global"),
                demo.get("inferred_language", "English"),
                demo.get("primary_interest", "Tech"),
                u.get("sentiment_avg", 0.0),
                u.get("primary_emotion", "neutral"),
                u.get("posts_count", 1)
            ])
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=real_social_users.csv"}
        )
    else:
        return users

class StreamControlRequest(BaseModel):
    speed_seconds: float

@app.post("/api/stream/control")
async def control_stream(req: StreamControlRequest):
    """Adjust live stream generation delay (speed)"""
    from backend.ingestion.stream_engine import stream_broadcaster
    stream_broadcaster.stream_delay = max(0.5, min(10.0, req.speed_seconds))
    return {"status": "ok", "speed_seconds": stream_broadcaster.stream_delay}

# ----------------- PostgreSQL Database Endpoints -----------------
from backend.database.postgres_repository import postgres_repo
from backend.database.init_db import create_database_if_not_exists, apply_schema_and_tables, sync_real_users_to_postgres

@app.get("/api/db/health")
async def get_db_health():
    """Retrieve PostgreSQL connection state, active tables, and records count"""
    return postgres_repo.check_health()

@app.post("/api/db/reconnect")
async def reconnect_db(db_url: Optional[str] = Query(None)):
    """Reconnect or update PostgreSQL connection URL on-demand and sync tables"""
    connected = postgres_repo.reconnect(db_url)
    if connected:
        sync_real_users_to_postgres()
    return {
        "status": "connected" if connected else "offline",
        "health": postgres_repo.check_health()
    }

@app.post("/api/db/create")
async def create_and_init_db(db_url: Optional[str] = Query(None)):
    """Automatically creates target PostgreSQL database and initializes all tables & real users"""
    created = create_database_if_not_exists(db_url)
    tables_ready = apply_schema_and_tables(db_url)
    synced_users = sync_real_users_to_postgres() if tables_ready else 0
    return {
        "database_created": created,
        "tables_ready": tables_ready,
        "synced_real_users": synced_users,
        "health": postgres_repo.check_health()
    }



# ----------------- Authentication & Access Control Endpoints -----------------
from backend.auth import auth_manager

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    phone_number: str
    password: str
    full_name: Optional[str] = ""
    role: Optional[str] = "Analyst"
    clearance_level: Optional[str] = "Level 3"

class ForgotPasswordRequest(BaseModel):
    identifier: str
    new_password: str

class LogoutRequest(BaseModel):
    token: str

@app.post("/api/auth/login")
async def auth_login(req: LoginRequest):
    """Authenticate credentials (User ID / Email / Phone Number + Password) and issue session token"""
    res = auth_manager.login(req.username, req.password)
    return res

@app.post("/api/auth/register")
async def auth_register(req: RegisterRequest):
    """Register new security clearance profile & credentials directly to database"""
    res = auth_manager.register(
        username=req.username,
        email=req.email,
        phone_number=req.phone_number,
        password=req.password,
        full_name=req.full_name or "",
        role=req.role or "Analyst",
        clearance_level=req.clearance_level or "Level 3"
    )
    return res

@app.post("/api/auth/forgot-password")
async def auth_forgot_password(req: ForgotPasswordRequest):
    """Reset user password in PostgreSQL database by User ID, Email, or Phone Number"""
    res = auth_manager.forgot_password(req.identifier, req.new_password)
    return res

@app.get("/api/auth/me")
async def auth_me(token: Optional[str] = Query(None)):
    """Validate active operator session token and retrieve profile"""
    if not token:
        return {"authenticated": False, "user": None}
    user = auth_manager.validate_token(token)
    if user:
        return {"authenticated": True, "user": user}
    return {"authenticated": False, "user": None}

@app.post("/api/auth/logout")
async def auth_logout(req: LogoutRequest):
    """Terminate and invalidate operator session token"""
    success = auth_manager.logout(req.token)
    return {"success": success, "message": "Session terminated."}


# ----------------- Static Frontend Hosting -----------------
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/login")
    @app.get("/login.html")
    async def serve_login():
        return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

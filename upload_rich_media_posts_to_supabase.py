import time
import random
import uuid
from backend.database.postgres_repository import postgres_repo
from backend.database.config import SessionLocal, engine
from sqlalchemy import text

print("Connecting to Supabase PostgreSQL...")
db_ok = postgres_repo.init_db(force=True)
print("Connected:", postgres_repo.is_connected)

if not postgres_repo.is_connected:
    print("Error: Could not connect to PostgreSQL.")
    exit(1)

# Ensure schema columns exist
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE post_records ADD COLUMN IF NOT EXISTS media_type VARCHAR(32) DEFAULT 'none';"))
    conn.execute(text("ALTER TABLE post_records ADD COLUMN IF NOT EXISTS media_url TEXT;"))
    conn.execute(text("ALTER TABLE post_records ALTER COLUMN media_url TYPE TEXT;"))
    conn.commit()

# Fast bulk update existing records via direct SQL
print("\n[*] Updating existing records with photos and videos in Supabase...")
with engine.connect() as conn:
    # Set videos for YouTube
    conn.execute(text("""
        UPDATE post_records 
        SET media_type = 'video', 
            media_url = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'
        WHERE LOWER(platform) = 'youtube' AND (media_url IS NULL OR media_type = 'none');
    """))

    # Set photos for Instagram
    conn.execute(text("""
        UPDATE post_records 
        SET media_type = 'photo', 
            media_url = 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80'
        WHERE LOWER(platform) = 'instagram' AND (media_url IS NULL OR media_type = 'none');
    """))

    # Set photos for X
    conn.execute(text("""
        UPDATE post_records 
        SET media_type = 'photo', 
            media_url = 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80'
        WHERE LOWER(platform) = 'x' AND (media_url IS NULL OR media_type = 'none') AND id LIKE '%2%';
    """))

    # Set videos for Facebook
    conn.execute(text("""
        UPDATE post_records 
        SET media_type = 'video', 
            media_url = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
        WHERE LOWER(platform) = 'facebook' AND (media_url IS NULL OR media_type = 'none') AND id LIKE '%4%';
    """))

    # Set photos for Reddit
    conn.execute(text("""
        UPDATE post_records 
        SET media_type = 'photo', 
            media_url = 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80'
        WHERE LOWER(platform) = 'reddit' AND (media_url IS NULL OR media_type = 'none');
    """))

    # Set photos for Telegram
    conn.execute(text("""
        UPDATE post_records 
        SET media_type = 'photo', 
            media_url = 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80'
        WHERE LOWER(platform) = 'telegram' AND (media_url IS NULL OR media_type = 'none') AND id LIKE '%1%';
    """))

    conn.commit()

# Bulk insert 100 new rich media posts directly
print("\n[*] Uploading fresh photo and video posts directly into Supabase post_records...")
SAMPLE_PHOTOS = [
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1507413245164-6160d8298b31?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=1200&q=80"
]

SAMPLE_VIDEOS = [
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
]

POST_TEMPLATES = [
    ("Breakthrough in neural network efficiency: 4x throughput with 50% less VRAM on next-gen hardware benchmarks. Full architecture breakdown attached! #AI #MachineLearning #Silicon", "photo"),
    ("Live demo of autonomous drone navigation using onboard edge transformers in GPS-denied environments! Check out the real-time sensor feed. #Robotics #AutonomousAI", "video"),
    ("Quantum coherence record achieved at room temperature! This changes everything for practical quantum computing clusters. #QuantumTech #Physics #DeepTech", "photo"),
    ("Decentralized Liquidity Pool Stress Test & Quantitative Risk Analysis under extreme market volatility. Watch the visual simulation. #DeFi #FinTech #Crypto", "video"),
    ("Zero-Trust cloud security mesh deployed across 14 global edge clusters. Latency reduced to under 3ms. #CyberSecurity #CloudInfrastructure", "photo"),
    ("Generative video diffusion pipelines now rendering cinematic 4K physics at 60 FPS in real time. Watch this breathtaking benchmark! #GenerativeAI #VFX", "video"),
    ("Spatial computing and brain-computer interface telemetry live stream demonstration. Next-gen neural interface in action. #BCI #NeuroTech", "video"),
    ("New open-source WebAssembly compiler benchmark comparisons against native C++/Rust binaries. Charts and profiling report attached. #WebAssembly #OpenSource", "photo"),
    ("Global climate telemetry satellite array captures high-resolution polar ice sheet dynamics in real-time. #SpaceTech #EarthObservation", "photo"),
    ("Next-generation humanoid robot dexterity test: manipulating delicate microelectronics with sub-millimeter precision. #HumanoidRobots #AI", "video")
]

platforms = ["Instagram", "YouTube", "X", "Reddit", "Facebook", "Telegram"]
now = time.time()

for i in range(100):
    t_epoch = now - (100 - i) * 20
    t_iso = time.strftime('%H:%M:%S', time.localtime(t_epoch))
    text_content, m_type = POST_TEMPLATES[i % len(POST_TEMPLATES)]
    m_url = SAMPLE_PHOTOS[i % len(SAMPLE_PHOTOS)] if m_type == "photo" else SAMPLE_VIDEOS[i % len(SAMPLE_VIDEOS)]
    plat = platforms[i % len(platforms)]
    
    post_item = {
        "id": f"media_post_{uuid.uuid4().hex[:12]}",
        "platform": plat,
        "text": f"{text_content} [Dispatch #{i+1}]",
        "author": {
            "name": f"Creator {plat} {i+1}",
            "username": f"{plat.lower()}_creator_{i+1}",
            "bio": f"Verified {plat} Contributor",
            "location": "Global Station",
            "followers": random.randint(10000, 1500000),
            "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed=media_{i+1}",
            "role": "Verified Creator"
        },
        "timestamp_epoch": t_epoch,
        "timestamp_iso": t_iso,
        "sentiment": {
            "sentiment_label": "positive",
            "confidence_score": 0.9,
            "valence": 0.65,
            "primary_emotion": "excitement",
            "sarcasm": {"is_sarcastic": False, "confidence": 0.0},
            "stance": {"label": "supportive"}
        },
        "demographics": {
            "inferred_age_bracket": "25-34",
            "geographic_origin": "Global",
            "inferred_language": "English",
            "primary_interest": "Technology"
        },
        "engagement": {
            "likes": random.randint(50, 4500),
            "shares": random.randint(10, 850),
            "replies": random.randint(5, 320)
        },
        "media_type": m_type,
        "media_url": m_url,
        "comments_count": random.randint(1, 15)
    }
    postgres_repo.insert_post(post_item)

# 3. Final Verification in Database
with engine.connect() as conn:
    total_posts = conn.execute(text("SELECT COUNT(*) FROM post_records")).scalar()
    photo_posts = conn.execute(text("SELECT COUNT(*) FROM post_records WHERE media_type = 'photo'")).scalar()
    video_posts = conn.execute(text("SELECT COUNT(*) FROM post_records WHERE media_type = 'video'")).scalar()
    
    print("\n================ Supabase PostgreSQL Media Posts Status ================")
    print(f"Total Posts in Database: {total_posts}")
    print(f"Photo Posts Stored:      {photo_posts}")
    print(f"Video Posts Stored:      {video_posts}")
    print("========================================================================\n")

print("SUCCESS: Photos and Videos are verified and saved in Supabase database!")

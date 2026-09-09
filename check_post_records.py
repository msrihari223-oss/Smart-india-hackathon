from backend.database.postgres_repository import postgres_repo
from backend.database.config import SessionLocal
from backend.database.models import PostRecord
from sqlalchemy import func

postgres_repo.init_db(force=True)
print("Connected:", postgres_repo.is_connected)

if postgres_repo.is_connected and SessionLocal is not None:
    with SessionLocal() as db:
        cnt = db.query(func.count(PostRecord.id)).scalar()
        print("Total posts in post_records:", cnt)
        
        sample_posts = db.query(PostRecord).limit(5).all()
        for p in sample_posts:
            print(f"- [{p.platform}] {p.author_username}: {p.text[:40]}... (media: {p.media_type}, {p.media_url})")

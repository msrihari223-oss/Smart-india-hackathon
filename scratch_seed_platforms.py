from backend.database.postgres_repository import postgres_repo
from backend.database.config import SessionLocal
from backend.database.models import PostRecord
from backend.ingestion.real_connectors import real_user_fetcher
from backend.ml.sentiment_engine import sentiment_engine
from backend.ml.demographic_engine import demographic_engine
import time, random
from sqlalchemy import func

def seed_platforms():
    postgres_repo.init_db()
    with SessionLocal() as session:
        print("[*] Populating balanced initial posts across all platforms...")
        all_posts = (
            real_user_fetcher.fetch_x_bluesky_posts(35) +
            real_user_fetcher.fetch_telegram_posts() +
            real_user_fetcher.fetch_reddit_posts() +
            real_user_fetcher.fetch_youtube_posts() +
            real_user_fetcher.fetch_instagram_posts() +
            real_user_fetcher.fetch_facebook_posts()
        )

        now = time.time()
        for i, raw in enumerate(all_posts):
            author = raw["author"]
            text = raw["text"]
            plat = raw["platform"]
            t = now - (len(all_posts) - i) * 8
            sent = sentiment_engine.analyze(text)
            demo = demographic_engine.infer_profile(author.get("bio", ""), text, author.get("location", ""))

            rec = PostRecord(
                id=f"seed_{plat.lower()}_{i+1:04d}",
                platform=plat,
                text=text,
                author_username=author.get("username", "user"),
                author_name=author.get("name", "User"),
                author_bio=author.get("bio", ""),
                author_location=author.get("location", ""),
                author_followers=author.get("followers", 1000),
                author_avatar=author.get("avatar", ""),
                author_role=author.get("role", "Member"),
                timestamp_epoch=t,
                timestamp_iso=time.strftime('%H:%M:%S', time.localtime(t)),
                sentiment_label=sent["sentiment_label"],
                sentiment_score=sent["sentiment_score"],
                sentiment_valence=sent["valence"],
                primary_emotion=sent["primary_emotion"],
                sarcasm_detected=sent["sarcasm"]["is_sarcastic"],
                sarcasm_confidence=sent["sarcasm"]["sarcasm_confidence"],
                stance=sent["stance"]["stance"],
                inferred_age_bracket=demo["inferred_age_bracket"],
                geographic_origin="India" if i % 2 == 0 else "United States",
                inferred_language=demo["inferred_language"],
                primary_interest=demo["primary_interest"],
                likes_count=raw.get("engagement", {}).get("likes", 100),
                shares_count=raw.get("engagement", {}).get("shares", 20),
                replies_count=raw.get("engagement", {}).get("replies", 5),
                raw_payload={
                    "id": f"seed_{plat.lower()}_{i+1:04d}",
                    "platform": plat,
                    "text": text,
                    "author": author,
                    "timestamp_epoch": t,
                    "timestamp_iso": time.strftime('%H:%M:%S', time.localtime(t)),
                    "sentiment": sent,
                    "demographics": demo,
                    "engagement": raw.get("engagement", {"likes": 100, "shares": 20, "replies": 5})
                }
            )
            session.merge(rec)

        session.commit()
        print("[+] Seed complete!")

        counts = session.query(PostRecord.platform, func.count(PostRecord.id)).group_by(PostRecord.platform).all()
        print("PLATFORM COUNTS IN DATABASE:")
        for platform_name, cnt in counts:
            print(f"  {platform_name}: {cnt} posts")

if __name__ == "__main__":
    seed_platforms()

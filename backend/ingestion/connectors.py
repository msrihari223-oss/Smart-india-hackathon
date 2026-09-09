"""
Multi-Platform Data Ingestion Connectors & Mock Live Stream Generator
Generates continuous, realistic multi-platform social streams with nuanced sentiments,
sarcasm, multi-lingual posts, follower interactions, and demographic indicators.
"""

import random
import time
import uuid
from typing import Dict, Any, List
from backend.ml.sentiment_engine import sentiment_engine
from backend.ml.demographic_engine import demographic_engine
from backend.ml.trend_engine import trend_engine
from backend.ml.network_engine import network_engine
from backend.database.memory_db import timeline_db
from backend.database.postgres_repository import postgres_repo


# User Profiles and KOLs across platforms
INFLUENCERS_AND_USERS = [
    {
        "username": "tech_visionary",
        "name": "Elena Rostova",
        "bio": "AI Research Director @ DeepLogic | ex-Stanford | Exploring frontier models & autonomy #AI #AGI",
        "location": "San Francisco, USA",
        "followers": 142000,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=elena",
        "role": "AI Thought Leader"
    },
    {
        "username": "crypto_satya",
        "name": "Satya Narayan",
        "bio": "DeFi Architect & Macro Strategist | Bengaluru | Building on-chain sovereign infra #Crypto #Web3",
        "location": "Bengaluru, India",
        "followers": 89000,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=satya",
        "role": "FinTech Strategist"
    },
    {
        "username": "cyber_critic",
        "name": "Marcus Vance",
        "bio": "Independent Tech Policy Columnist & Skeptic. Dissecting corporate hype and regulatory failure.",
        "location": "London, UK",
        "followers": 52000,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=marcus",
        "role": "Policy Critic"
    },
    {
        "username": "dev_aakash",
        "name": "Aakash Verma",
        "bio": "Fullstack SWE | GenAI Builder | Open-Source contributor | Delhi campus alumni #Developer",
        "location": "Delhi, India",
        "followers": 18400,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=aakash",
        "role": "Open Source Builder"
    },
    {
        "username": "global_macro_pulse",
        "name": "Macro Insights",
        "bio": "Institutional market flow, central bank liquidity updates & quantitative analytics.",
        "location": "New York, USA",
        "followers": 210000,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=macropulse",
        "role": "Institutional Media"
    },
    {
        "username": "sophia_neural",
        "name": "Dr. Sophia Schmidt",
        "bio": "Computational Neuroscientist @ Max Planck Institute Berlin | PhD | Brain-Computer Interfaces",
        "location": "Berlin, Germany",
        "followers": 41000,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=sophia",
        "role": "Academia Researcher"
    },
    {
        "username": "rookie_trader_99",
        "name": "Sam K.",
        "bio": "College student exploring quant trading and AI tools. Let's go to the moon! 🚀",
        "location": "Toronto, Canada",
        "followers": 3200,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=samk",
        "role": "Community Member"
    },
    {
        "username": "sarcastic_bot_x",
        "name": "The Real Cynic",
        "bio": "Here to applaud every 'groundbreaking revolution' that crashes in 24 hours.",
        "location": "Austin, USA",
        "followers": 27500,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=cynic",
        "role": "Satirist"
    }
]

# Register users to network engine initially
for user in INFLUENCERS_AND_USERS:
    network_engine.register_user_meta(
        username=user["username"],
        display_name=user["name"],
        avatar=user["avatar"],
        role=user["role"],
        followers=user["followers"]
    )

# Realistic Multi-Platform Post Corpus with diverse sentiments, sarcasm, and trending narratives
STREAM_CORPUS = [
    # X (Twitter)
    {
        "platform": "X",
        "text": "The latest Autonomous Agent framework benchmark just dropped and the latency reduction is absolutely insane! 🚀 We are witnessing an unprecedented paradigm shift in AI agents. #AgenticAI #GenAI #TechRevolution",
        "target_user": "tech_visionary",
        "interaction": "retweet"
    },
    {
        "platform": "X",
        "text": "Oh sure, another 'unhackable' smart contract platform just got drained for $40M. What a genius architecture... clearly working so well! 🙄 #CryptoSecurity #DeFi #Irony",
        "target_user": "cyber_critic",
        "interaction": "quote"
    },
    {
        "platform": "X",
        "text": "Huge milestone for our open source community in Bengaluru! Over 10k developers deployed the localized model today. Proud of what we built together! 🙌 #DevCommunity #OpenSourceIndia #TechInnovation",
        "target_user": "dev_aakash",
        "interaction": "mention"
    },
    {
        "platform": "X",
        "text": "Emergency liquidity measures announced by central banks. Bond yield volatility is creating extreme anxiety across emerging markets. Watch out for sudden crash risks. #MarketCrash #Inflation #Economy",
        "target_user": "global_macro_pulse",
        "interaction": "retweet"
    },

    # Telegram
    {
        "platform": "Telegram",
        "channel": "Alpha Signals & Deep Tech Hub",
        "text": "⚡ BREAKING: Quantum computing breakthrough confirmed in Berlin lab. Qubit coherence time extended by 10x. This is a massive gamechanger for post-quantum encryption. #QuantumTech #Breakthrough",
        "target_user": "sophia_neural",
        "interaction": "forward"
    },
    {
        "platform": "Telegram",
        "channel": "Crypto Whale Alert",
        "text": "🚨 Whale Alert: 15,000 BTC moved from cold storage to exchange. High anxiety and panic selling expected on perpetual futures! Brace for impact. #Bitcoin #CryptoAlert",
        "target_user": "crypto_satya",
        "interaction": "forward"
    },
    {
        "platform": "Telegram",
        "channel": "Tech Critics Anonymous",
        "text": "Totally normal for a social media algorithm to optimize exclusively for outrage. Thanks a lot for that wonderful civic harmony... as if we needed more chaos! /s #AlgorithmicBias",
        "target_user": "sarcastic_bot_x",
        "interaction": "reply"
    },

    # Reddit
    {
        "platform": "Reddit",
        "subreddit": "r/ArtificialIntelligence",
        "text": "Is anyone else worried about the rapid concentration of compute in just three mega-corporations? The barrier to entry for university researchers is becoming hopeless. #AIResearch #ComputeMonopoly",
        "target_user": "tech_visionary",
        "interaction": "reply"
    },
    {
        "platform": "Reddit",
        "subreddit": "r/ProgrammerHumor",
        "text": "Junior devs writing code with 4 LLM assistants simultaneously: 'Works on my machine!'. What could possibly go wrong in production? 😂 #DevLife #SoftwareEngineering",
        "target_user": "dev_aakash",
        "interaction": "reply"
    },

    # YouTube Comments
    {
        "platform": "YouTube",
        "video_title": "Explained: The Future of Neural Interfaces in 2026",
        "text": "I was skeptical at first, but the clinical trials on restoring motor functions are deeply inspiring and heartwarming. Solid science and amazing presentation! 👏 #Biotech #Neuroscience",
        "target_user": "sophia_neural",
        "interaction": "comment"
    },
    {
        "platform": "YouTube",
        "video_title": "Why Modern Social Platforms are Broken",
        "text": "Spot on analysis! We need decentralized protocols with transparent ranking algorithms. Count on me to support open-source alternatives. #DigitalRights #Web3",
        "target_user": "cyber_critic",
        "interaction": "comment"
    },

    # Instagram
    {
        "platform": "Instagram",
        "text": "Late night coding session from our studio in San Francisco ✨ Brewing ideas that turn into reality. Blessed to work with the most passionate team! ☕💻 #StartupLife #SanFrancisco #BuilderVibes",
        "target_user": "tech_visionary",
        "interaction": "share"
    },
    {
        "platform": "Instagram",
        "text": "Grateful for the incredible energy at the AI Summit India today! Met so many enthusiastic students and builders. The future is vibrant! 🇮🇳✨ #AISummit #BengaluruTech",
        "target_user": "dev_aakash",
        "interaction": "like"
    },

    # Facebook
    {
        "platform": "Facebook",
        "group": "Global AI Ethics & Governance Forum",
        "text": "We must stand together and endorse strict standards against deceptive synthetic media. Public trust is too fragile to compromise. #AIEthics #PolicyReform",
        "target_user": "cyber_critic",
        "interaction": "share"
    }
]

def generate_live_post() -> Dict[str, Any]:
    """
    Simulates a live incoming post, runs the full AI inference pipeline, and stores in timeline & network graphs.
    """
    author = random.choice(INFLUENCERS_AND_USERS)
    template = random.choice(STREAM_CORPUS)
    
    # Text mutation/variation for realistic continuous streaming
    base_text = template["text"]
    text = base_text
    
    # 1. Run Multi-Dimensional Sentiment & Nuanced Emotion NLP
    sentiment_result = sentiment_engine.analyze(text)
    
    # 2. Run Automated Demographic Profiler
    demo_result = demographic_engine.infer_profile(
        user_bio=author["bio"],
        text_content=text,
        location_meta=author["location"]
    )
    
    post_id = f"post_{uuid.uuid4().hex[:8]}"
    now_epoch = time.time()
    
    post_data = {
        "id": post_id,
        "platform": template["platform"],
        "text": text,
        "author": author,
        "timestamp_epoch": now_epoch,
        "timestamp_iso": time.strftime('%H:%M:%S', time.localtime(now_epoch)),
        "sentiment": sentiment_result,
        "demographics": demo_result,
        "engagement": {
            "likes": random.randint(12, 1450),
            "shares": random.randint(3, 380),
            "replies": random.randint(1, 195)
        },
        "target_user": template.get("target_user"),
        "interaction_type": template.get("interaction", "retweet")
    }

    # 3. Add to Trend Engine
    trend_engine.add_post(post_data)

    # 4. Add to Historical Timeline Database & PostgreSQL
    timeline_db.insert(post_data)
    try:
        postgres_repo.insert_post(post_data)
    except Exception:
        pass


    # 5. Add to Network Topology Engine
    if post_data["target_user"] and post_data["target_user"] != author["username"]:
        network_engine.add_interaction(
            source_user=author["username"],
            target_user=post_data["target_user"],
            interaction_type=post_data["interaction_type"],
            sentiment=sentiment_result["valence"],
            timestamp=now_epoch
        )

    return post_data

# Pre-populate historical buffer with initial 60 records for instant rich charts on launch
def seed_initial_history(count: int = 60):
    start_time = time.time() - (count * 10)
    for i in range(count):
        author = random.choice(INFLUENCERS_AND_USERS)
        template = random.choice(STREAM_CORPUS)
        t = start_time + (i * 10)
        
        sent = sentiment_engine.analyze(template["text"])
        demo = demographic_engine.infer_profile(author["bio"], template["text"], author["location"])
        
        post = {
            "id": f"seed_{i}",
            "platform": template["platform"],
            "text": template["text"],
            "author": author,
            "timestamp_epoch": t,
            "timestamp_iso": time.strftime('%H:%M:%S', time.localtime(t)),
            "sentiment": sent,
            "demographics": demo,
            "engagement": {
                "likes": random.randint(20, 2000),
                "shares": random.randint(5, 500),
                "replies": random.randint(2, 250)
            },
            "target_user": template.get("target_user"),
            "interaction_type": template.get("interaction", "retweet")
        }
        
        timeline_db.insert(post)
        trend_engine.add_post(post)
        
        if post["target_user"] and post["target_user"] != author["username"]:
            network_engine.add_interaction(
                source_user=author["username"],
                target_user=post["target_user"],
                interaction_type=post["interaction_type"],
                sentiment=sent["valence"],
                timestamp=t
            )

# Execute seed
seed_initial_history(60)

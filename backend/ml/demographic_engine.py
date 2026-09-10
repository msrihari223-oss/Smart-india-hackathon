"""
Automated Demographic Profiling Engine
Infers aggregate, anonymized follower demographics (age bracket, geographic region,
language, professional interest domains, and persona archetype) using NLP on bio, text, and metadata.
"""

import re
from typing import Dict, Any, List, Optional

class DemographicProfiler:
    def __init__(self):
        # Age indicators based on lexical markers, terminology, life stage mentions
        self.age_lexicons = {
            "18-24": {
                "college", "student", "uni", "campus", "intern", "genz", "vibes", "bruh", "cap", 
                "no cap", "mid", "fr fr", "bet", "dorm", "undergrad", "freshman", "sophomore",
                "gaming", "anime", "tiktok", "deadass", "rizz", "gyatt", "skibidi", "bussing",
                "graduating", "entry-level", "junior year", "senior year"
            },
            "25-34": {
                "junior", "engineer", "dev", "crypto", "builder", "startup", "founder", "hustle", 
                "freelance", "traveler", "remote", "coffee", "product manager", "designer", "indie", 
                "millennial", "phd candidate", "swe", "marketing", "consultant", "developer", "creator",
                "co-founder", "tech lead", "growth", "coder", "full-stack", "ml engineer", "staff engineer"
            },
            "35-44": {
                "senior", "lead", "director", "manager", "vp", "architect", "parent", "dad", "mom", 
                "investor", "principal", "consultant", "homeowner", "veteran", "strategist", "head of",
                "executive", "portfolio", "angel investor", "partner", "general partner", "department head"
            },
            "45-54": {
                "executive", "managing director", "partner", "c-suite", "cto", "ceo", "cfo", "fellow", 
                "professor", "mentor", "board member", "advisor", "20+ years", "industry veteran",
                "chairperson", "president", "chancellor", "trustee"
            },
            "55+": {
                "retired", "emeritus", "grandparent", "veteran", "elder", "chairperson", "30+ years", 
                "author", "pioneer", "legacy", "historical", "senior fellow", "distinguished fellow"
            }
        }

        # Professional interest domains
        self.domain_lexicons = {
            "Tech & AI": {
                "ai", "ml", "software", "code", "python", "developer", "cloud", "data", "deep learning", 
                "engineer", "llm", "neural", "gpu", "cybersecurity", "web3", "algorithms", "robotics", 
                "devops", "kubernetes", "database", "backend", "frontend", "apis", "deepseek", "openai",
                "pytorch", "tensorflow", "transformer", "huggingface", "agentic", "agents"
            },
            "Finance & Crypto": {
                "finance", "crypto", "bitcoin", "stocks", "trader", "defi", "investment", "portfolio", 
                "macro", "wealth", "equity", "hedge", "banking", "alpha", "venture", "vc", "tokenomics",
                "ethereum", "solana", "trading", "fintech", "yield", "bullish", "bearish", "etf", "liquidity"
            },
            "Healthcare & Bio": {
                "health", "doctor", "medical", "pharma", "biotech", "genomics", "clinical", "nurse", 
                "medicine", "wellness", "neuroscience", "public health", "therapeutics", "oncology",
                "bioinformatics", "crispr", "longevity", "biology", "synthetic bio"
            },
            "Politics & Policy": {
                "policy", "governance", "politics", "law", "diplomacy", "geopolitics", "human rights", 
                "activist", "election", "democracy", "public policy", "civic", "regulation", "senate",
                "congress", "parliament", "treaty", "sovereignty", "legislation"
            },
            "Creative Arts & Media": {
                "creator", "artist", "designer", "writer", "filmmaker", "music", "producer", "photographer", 
                "journalist", "podcaster", "video", "content", "ui/ux", "author", "storyteller",
                "cinematography", "graphic design", "animation", "vfx", "cinema", "media"
            },
            "Academia & Research": {
                "researcher", "phd", "scientist", "professor", "university", "paper", "peer-reviewed", 
                "academic", "institute", "scholar", "laboratory", "postdoc", "arxiv", "symposium", "journal"
            },
            "Gaming & Esports": {
                "gamer", "streamer", "twitch", "esports", "fps", "rpg", "speedrun", "discord", "modder", 
                "game dev", "unreal engine", "steam", "playstation", "xbox", "nintendo", "valorant"
            }
        }

        # Geographic inference lookups across global hubs
        self.geo_rules = {
            "United States": [
                "san francisco", "sf", "bay area", "silicon valley", "nyc", "new york", "austin", "seattle",
                "california", "texas", "chicago", "usa", "us", "los angeles", "la", "boston", "miami",
                "denver", "atlanta", "washington dc", "dc", "cambridge", "united states"
            ],
            "India": [
                "bengaluru", "bangalore", "delhi", "new delhi", "mumbai", "hyderabad", "pune", "chennai", 
                "india", "kolkata", "gurugram", "gurgaon", "noida", "kerala", "ahmedabad", "jaipur", "indore"
            ],
            "United Kingdom": [
                "london", "manchester", "uk", "cambridge", "oxford", "edinburgh", "britain", "england", 
                "scotland", "birmingham", "bristol", "leeds", "united kingdom"
            ],
            "Germany": [
                "berlin", "munich", "germany", "frankfurt", "hamburg", "deutschland", "stuttgart", "cologne"
            ],
            "Canada": [
                "toronto", "vancouver", "montreal", "canada", "ottawa", "calgary", "waterloo", "quebec"
            ],
            "Japan": [
                "tokyo", "japan", "osaka", "kyoto", "nihon", "yokohama", "fukuoka"
            ],
            "Australia": [
                "sydney", "melbourne", "australia", "brisbane", "perth", "adelaide"
            ],
            "Singapore": [
                "singapore", "sg"
            ],
            "France": [
                "paris", "france", "lyon", "marseille", "toulouse"
            ],
            "United Arab Emirates": [
                "dubai", "abu dhabi", "uae", "united arab emirates"
            ],
            "Brazil": [
                "sao paulo", "rio", "brazil", "brasil"
            ],
            "Netherlands": [
                "amsterdam", "rotterdam", "netherlands", "holland"
            ],
            "South Korea": [
                "seoul", "korea", "busan", "south korea"
            ],
            "Switzerland": [
                "zurich", "geneva", "switzerland", "bern", "basel"
            ],
            "Sweden": [
                "stockholm", "gothenburg", "sweden"
            ]
        }

        # Language patterns
        self.lang_cues = {
            "Hindi": [
                r"[\u0900-\u097F]", 
                r"\b(kya|hai|nahi|bahut|acha|bhai|yaar|dhanyawad|shandar|zabardast|mast|sahi|kuch|kaise|hota|raha|hoga|kripya)\b"
            ],
            "Spanish": [
                r"\b(el|la|los|las|por|que|hola|gracias|amigo|muy|bueno|bien|todo|esta|para|con|pero)\b"
            ],
            "French": [
                r"\b(le|la|les|dans|avec|pour|merci|bonjour|très|bien|c'est|nous|vous|mais)\b"
            ],
            "German": [
                r"\b(der|die|das|und|nicht|sehr|danke|gut|mit|ein|eine|ist|aber|wir)\b"
            ],
            "Japanese": [
                r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]"
            ],
            "Chinese": [
                r"[\u4e00-\u9fff]"
            ],
            "Arabic": [
                r"[\u0600-\u06FF]"
            ],
            "Russian": [
                r"[\u0400-\u04FF]"
            ],
            "Portuguese": [
                r"\b(obrigado|muito|bom|tudo|com|para|voce|esta|aqui)\b"
            ]
        }

    def infer_profile(self, user_bio: str = "", text_content: str = "", location_meta: str = "") -> Dict[str, Any]:
        """
        Infers demographic attributes from combined user context with high precision.
        """
        combined = f"{user_bio} {text_content} {location_meta}".lower()
        words = set(re.findall(r'\b\w+\b', combined))
        
        # 1. Age Bracket Inference
        age_scores = {bracket: 0.1 for bracket in self.age_lexicons}
        for bracket, terms in self.age_lexicons.items():
            overlap = words.intersection(terms)
            age_scores[bracket] += len(overlap) * 1.6

        total_age = sum(age_scores.values())
        age_distribution = {k: round(v / total_age, 3) for k, v in age_scores.items()}
        inferred_age = max(age_distribution, key=age_distribution.get)

        # 2. Professional Interest Inference
        domain_scores = {dom: 0.05 for dom in self.domain_lexicons}
        for domain, terms in self.domain_lexicons.items():
            overlap = words.intersection(terms)
            domain_scores[domain] += len(overlap) * 1.8

        total_domain = sum(domain_scores.values())
        domain_distribution = {k: round(v / total_domain, 3) for k, v in domain_scores.items()}
        primary_interest = max(domain_distribution, key=domain_distribution.get)

        # 3. Geographic Region Inference
        inferred_geo = "Global / Undisclosed"
        # Check explicit location meta first
        loc_clean = location_meta.lower().strip()
        if loc_clean and loc_clean not in ["global station", "global", "earth", "remote", ""]:
            for country, keywords in self.geo_rules.items():
                if any(kw in loc_clean for kw in keywords):
                    inferred_geo = country
                    break

        if inferred_geo == "Global / Undisclosed":
            for country, keywords in self.geo_rules.items():
                for kw in keywords:
                    if kw in combined:
                        inferred_geo = country
                        break
                if inferred_geo != "Global / Undisclosed":
                    break

        # 4. Primary Language Inference
        inferred_lang = "English"
        for lang, patterns in self.lang_cues.items():
            for pat in patterns:
                if re.search(pat, f"{user_bio} {text_content}", re.IGNORECASE):
                    inferred_lang = lang
                    break
            if inferred_lang != "English":
                break

        # 5. Persona Archetype
        if any(w in words for w in ["founder", "ceo", "director", "keynote", "advisor", "creator", "co-founder", "president", "vp"]):
            persona = "Key Opinion Leader (KOL)"
        elif any(w in words for w in ["researcher", "scientist", "phd", "engineer", "dev", "coder", "architect", "fellow"]):
            persona = "Tech Builder / Specialist"
        elif any(w in words for w in ["trader", "investor", "vc", "analyst", "partner", "angel", "macro"]):
            persona = "Market Strategist"
        elif any(w in words for w in ["activist", "critic", "debater", "journalist", "reporter", "policy"]):
            persona = "Civic Critic / Analyst"
        elif any(w in words for w in ["artist", "designer", "writer", "producer", "photographer", "content"]):
            persona = "Creative Broadcaster"
        elif any(w in words for w in ["student", "intern", "college", "uni", "learner"]):
            persona = "Emerging Scholar"
        else:
            persona = "Active Intelligence Contributor"

        return {
            "inferred_age_bracket": inferred_age,
            "age_distribution": age_distribution,
            "primary_interest": primary_interest,
            "interest_distribution": domain_distribution,
            "geographic_origin": inferred_geo,
            "inferred_language": inferred_lang,
            "persona_archetype": persona
        }

demographic_engine = DemographicProfiler()

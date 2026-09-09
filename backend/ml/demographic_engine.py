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
                "no cap", "mid", "fr fr", "bet", "dorm", "undergrad", "freshman", "gaming", "anime", "tiktok"
            },
            "25-34": {
                "junior", "engineer", "dev", "crypto", "builder", "startup", "founder", "hustle", 
                "freelance", "traveler", "remote", "coffee", "product manager", "designer", "indie", 
                "millennial", "phd candidate", "swe", "marketing", "consultant"
            },
            "35-44": {
                "senior", "lead", "director", "manager", "vp", "architect", "parent", "dad", "mom", 
                "investor", "principal", "consultant", "homeowner", "veteran", "strategist", "head of"
            },
            "45-54": {
                "executive", "managing director", "partner", "c-suite", "cto", "ceo", "cfo", "fellow", 
                "professor", "mentor", "board member", "advisor", "20+ years", "industry veteran"
            },
            "55+": {
                "retired", "emeritus", "grandparent", "veteran", "elder", "chairperson", "30+ years", 
                "author", "pioneer", "legacy", "historical"
            }
        }

        # Professional interest domains
        self.domain_lexicons = {
            "Tech & AI": {
                "ai", "ml", "software", "code", "python", "developer", "cloud", "data", "deep learning", 
                "engineer", "llm", "neural", "gpu", "cybersecurity", "web3", "algorithms", "robotics", "devops"
            },
            "Finance & Crypto": {
                "finance", "crypto", "bitcoin", "stocks", "trader", "defi", "investment", "portfolio", 
                "macro", "wealth", "equity", "hedge", "banking", "alpha", "venture", "vc", "tokenomics"
            },
            "Healthcare & Bio": {
                "health", "doctor", "medical", "pharma", "biotech", "genomics", "clinical", "nurse", 
                "medicine", "wellness", "neuroscience", "public health", "therapeutics", "oncology"
            },
            "Politics & Policy": {
                "policy", "governance", "politics", "law", "diplomacy", "geopolitics", "human rights", 
                "activist", "election", "democracy", "public policy", "civic", "regulation", "senate"
            },
            "Creative Arts & Media": {
                "creator", "artist", "designer", "writer", "filmmaker", "music", "producer", "photographer", 
                "journalist", "podcaster", "video", "content", "ui/ux", "author", "storyteller"
            },
            "Academia & Research": {
                "researcher", "phd", "scientist", "professor", "university", "paper", "peer-reviewed", 
                "academic", "institute", "scholar", "laboratory", "postdoc"
            },
            "Gaming & Esports": {
                "gamer", "streamer", "twitch", "esports", "fps", "rpg", "speedrun", "discord", "modder", 
                "game dev", "unreal engine", "steam"
            }
        }

        # Geographic inference lookups
        self.geo_rules = {
            "United States": ["san francisco", "nyc", "new york", "austin", "seattle", "california", "texas", "chicago", "usa", "us", "los angeles", "boston"],
            "India": ["bengaluru", "bangalore", "delhi", "mumbai", "hyderabad", "pune", "chennai", "india", "kolkata", "gurugram", "noida", "kerala"],
            "United Kingdom": ["london", "manchester", "uk", "cambridge", "oxford", "edinburgh", "britain", "england", "scotland"],
            "Germany": ["berlin", "munich", "germany", "frankfurt", "hamburg", "deutschland"],
            "Canada": ["toronto", "vancouver", "montreal", "canada", "ottawa", "calgary"],
            "Japan": ["tokyo", "japan", "osaka", "kyoto", "nihon"],
            "Australia": ["sydney", "melbourne", "australia", "brisbane", "perth"],
            "Singapore": ["singapore", "sg"],
            "France": ["paris", "france", "lyon"],
            "Brazil": ["sao paulo", "rio", "brazil", "brasil"]
        }

        # Language patterns
        self.lang_cues = {
            "Hindi": [r"[\u0900-\u097F]", r"\b(kya|hai|nahi|bahut|acha|bhai|yaar|dhanyawad)\b"],
            "Spanish": [r"\b(el|la|los|las|por|que|hola|gracias|amigo|muy|bueno)\b"],
            "French": [r"\b(le|la|les|dans|avec|pour|merci|bonjour|très)\b"],
            "German": [r"\b(der|die|das|und|nicht|sehr|danke|gut|mit)\b"],
            "Japanese": [r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]"]
        }

    def infer_profile(self, user_bio: str = "", text_content: str = "", location_meta: str = "") -> Dict[str, Any]:
        """
        Infers demographic attributes from combined user context.
        """
        combined = f"{user_bio} {text_content} {location_meta}".lower()
        words = set(re.findall(r'\b\w+\b', combined))
        
        # 1. Age Bracket Inference
        age_scores = {bracket: 0.1 for bracket in self.age_lexicons}
        for bracket, terms in self.age_lexicons.items():
            overlap = words.intersection(terms)
            age_scores[bracket] += len(overlap) * 1.5

        # Normalize age probabilities
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
        if any(w in words for w in ["founder", "ceo", "director", "keynote", "advisor", "creator"]):
            persona = "Key Opinion Leader (KOL)"
        elif any(w in words for w in ["researcher", "scientist", "phd", "engineer", "dev"]):
            persona = "Tech Builder / Specialist"
        elif any(w in words for w in ["trader", "investor", "vc", "analyst"]):
            persona = "Market Strategist"
        elif any(w in words for w in ["activist", "critic", "debater", "journalist"]):
            persona = "Civic Critic / Analyst"
        else:
            persona = "Active Community Member"

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

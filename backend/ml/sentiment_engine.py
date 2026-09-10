import os
import re
import json
import math
from typing import Dict, Any, List, Set, Tuple

class ToxicityModerationEngine:
    """
    High-Precision AI Content Moderation & Toxicity Guardrails Engine.
    Detects danger words, profanities, toxic hashtags, hate speech, harassment, threats, and cyberbullying
    across English, Internet Slang, Leetspeak, and Hinglish while protecting legitimate slang phrases.
    """
    def __init__(self):
        self.dataset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "danger_words_dataset.json")
        self.whitelisted_phrases: Set[str] = set()
        self.profanities: Set[str] = set()
        self.category_triggers: Dict[str, Set[str]] = {}
        self.dataset_metadata: Dict[str, Any] = {}
        self.raw_dataset: Dict[str, Any] = {}

        # Default fallbacks
        self._load_dataset()

        # Substring / Leetspeak normalization patterns
        self.leetspeak_map = {
            r'@': 'a',
            r'1': 'i',
            r'!': 'i',
            r'0': 'o',
            r'3': 'e',
            r'\$': 's',
            r'5': 's',
            r'7': 't',
            r'\*': 'u'
        }

        # Toxic / Abusive Hashtag prefixes and patterns
        self.toxic_tag_patterns = [
            r"#.*(?:hate|kill|die|fuck|bitch|bastard|idiot|trash|scam|ban|boycott|liar|clown|cringe|loser|ghatiya|fake|evil|fraud|corrupt).*",
            r"#(?:cancel|boycott|destro|shame|expose|downwith)[a-zA-Z0-9_]+"
        ]

    def _load_dataset(self):
        """Loads danger words dictionary from JSON dataset or uses defaults."""
        loaded = False
        if os.path.exists(self.dataset_path):
            try:
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.raw_dataset = data
                    self.dataset_metadata = data.get("metadata", {})
                    self.whitelisted_phrases = set(data.get("whitelisted_phrases", []))
                    
                    categories = data.get("categories", {})
                    for cat_name, cat_data in categories.items():
                        words = set(w.lower() for w in cat_data.get("words", []))
                        self.category_triggers[cat_name] = words
                        self.profanities.update(words)
                    loaded = True
            except Exception:
                loaded = False

        if not loaded:
            self.whitelisted_phrases = {
                "killer feature", "killer app", "killer update", "killer design", "killer price",
                "killing it", "killed it", "killing the game", "badass app", "badass feature", "badass build",
                "sick beat", "sick design", "sick feature", "sick update", "sick drop",
                "drop dead gorgeous", "drop-dead gorgeous", "shooting for the stars", "shoot for the moon",
                "bomb food", "the bomb", "blowing up", "blew my mind", "die hard fan", "die-hard fan",
                "to die for", "dead serious", "drop dead", "deadass", "slaying it", "slay"
            }
            self.profanities = {
                "fuck", "fucking", "fucked", "fucker", "shit", "bullshit", "bitch", "asshole",
                "bastard", "cunt", "dick", "pussy", "nigger", "nigga", "faggot", "idiot", "moron",
                "kill", "murder", "bomb", "terrorist", "scam", "chutiya", "madarchod", "bhenchod", "gandu"
            }
            self.category_triggers = {
                "Profanity & Vulgarity": {"fuck", "shit", "bitch", "asshole", "bastard", "cunt", "dick", "pussy"},
                "Threats & Violence": {"kill", "murder", "bomb", "terrorist"},
                "Insults & Harassment": {"idiot", "moron", "loser", "trash"},
                "Hate Speech & Slurs": {"nigger", "nigga", "faggot"}
            }

    def get_dataset(self) -> Dict[str, Any]:
        """Returns the loaded danger words dataset for frontend consumption."""
        if self.raw_dataset:
            return self.raw_dataset
        return {
            "metadata": {"name": "Danger Words Dataset", "total_words": len(self.profanities)},
            "categories": {k: {"words": list(v)} for k, v in self.category_triggers.items()},
            "whitelisted_phrases": list(self.whitelisted_phrases)
        }

    def normalize_leetspeak(self, text: str) -> str:
        """Translates f*ck, b!tch, a$$hole, etc. into readable forms for analysis"""
        norm = text.lower()
        for char, repl in self.leetspeak_map.items():
            norm = re.sub(char, repl, norm)
        # remove inner asterisks or periods in words (e.g. f.u.c.k or f*ck)
        norm = re.sub(r'(\b\w)[\*\.\-_]+(\w\b)', r'\1\2', norm)
        return norm

    def is_whitelisted(self, text: str) -> bool:
        """Checks if text matches benign slang whitelist"""
        low = text.lower()
        return any(phrase in low for phrase in self.whitelisted_phrases)

    def analyze_toxicity(self, text: str) -> Dict[str, Any]:
        """
        Analyzes text for bad words, profanities, toxic hashtags, harassment, and severity.
        Accurately whitelists benign slang to prevent false positives.
        """
        if not text or not text.strip():
            return {
                "is_toxic": False,
                "toxicity_score": 0.0,
                "severity": "SAFE",
                "detected_bad_words": [],
                "detected_bad_hashtags": [],
                "categories": [],
                "moderation_action": "ALLOW",
                "explanation": "Content is clean and compliant."
            }

        original_text = text
        lower_text = text.lower()
        normalized_text = self.normalize_leetspeak(lower_text)

        # Check whitelist first for mild matches
        has_whitelist = self.is_whitelisted(lower_text)

        detected_bad_words = set()
        detected_bad_hashtags = set()
        detected_categories = set()

        # 1. Extract and check hashtags
        hashtags = re.findall(r'#[\w\d_]+', original_text)
        for tag in hashtags:
            tag_lower = tag.lower()
            tag_clean = tag_lower.replace('#', '')
            
            for pattern in self.toxic_tag_patterns:
                if re.match(pattern, tag_lower, re.IGNORECASE):
                    detected_bad_hashtags.add(tag)
                    detected_categories.add("Toxic Hashtag")
                    break

            for bad in self.profanities:
                if bad in tag_clean and len(bad) >= 3:
                    detected_bad_hashtags.add(tag)
                    detected_bad_words.add(f"#{tag_clean}")
                    detected_categories.add("Toxic Hashtag")
                    break

        # 2. Check Words & Phrases in Normalized Text (with Whitelist Scrubbing)
        scrubbed_text = normalized_text
        scrubbed_lower = lower_text
        for phrase in self.whitelisted_phrases:
            if phrase in scrubbed_lower:
                scrubbed_lower = scrubbed_lower.replace(phrase, " ")
            if phrase in scrubbed_text:
                scrubbed_text = scrubbed_text.replace(phrase, " ")

        tokens = set(re.findall(r'\b[\w\']+\b', scrubbed_text))
        raw_tokens = set(re.findall(r'\b[\w\']+\b', scrubbed_lower))
        all_tokens = tokens.union(raw_tokens)

        for bad in self.profanities:
            if " " in bad:
                if bad in scrubbed_text or bad in scrubbed_lower:
                    detected_bad_words.add(bad)
            else:
                if bad in all_tokens:
                    detected_bad_words.add(bad)
                elif re.search(r'\b' + re.escape(bad) + r'\b', scrubbed_text):
                    detected_bad_words.add(bad)

        # 3. Categorize matched terms
        for word in detected_bad_words:
            clean_word = word.replace('#', '')
            for cat, vocab in self.category_triggers.items():
                if clean_word in vocab or any(v in clean_word for v in vocab if len(v) >= 4):
                    detected_categories.add(cat)

        if detected_bad_hashtags and "Toxic Hashtag" not in detected_categories:
            detected_categories.add("Toxic Hashtag")

        # 4. Toxicity Scoring and Severity Calculation
        total_violations = len(detected_bad_words) + (len(detected_bad_hashtags) * 1.5)
        
        has_hate = "Hate Speech & Slurs" in detected_categories
        has_threat = "Threats & Violence" in detected_categories
        has_profanity = "Profanity & Vulgarity" in detected_categories

        score = 0.0
        if total_violations > 0:
            base = min(0.95, (total_violations * 0.28) + 0.35)
            if has_hate or has_threat:
                base = max(0.90, base + 0.3)
            elif has_profanity:
                base = max(0.60, base)
            score = round(min(1.0, base), 2)

        # Severity & Action Logic
        if score == 0:
            severity = "SAFE"
            moderation_action = "ALLOW"
            explanation = "Content is clean and compliant."
        elif score < 0.45:
            severity = "LOW"
            moderation_action = "FLAG_REVIEW"
            explanation = "Mild sensitive language detected. Monitoring recommended."
        elif score < 0.70:
            severity = "MEDIUM"
            moderation_action = "WARN_USER"
            explanation = "Offensive bad words or toxic hashtags detected. Warning issued."
        elif score < 0.88:
            severity = "HIGH"
            moderation_action = "WARN_USER"
            explanation = "Severe toxicity / profanity identified. Moderation warning triggered."
        else:
            severity = "CRITICAL"
            moderation_action = "AUTO_BLOCK"
            explanation = "High-risk hate speech, threats, or severe abuse detected. Content restricted."

        is_toxic = score >= 0.35 or len(detected_bad_words) > 0 or len(detected_bad_hashtags) > 0

        return {
            "is_toxic": is_toxic,
            "toxicity_score": score,
            "severity": severity,
            "detected_bad_words": sorted(list(detected_bad_words)),
            "detected_bad_hashtags": sorted(list(detected_bad_hashtags)),
            "categories": sorted(list(detected_categories)),
            "moderation_action": moderation_action,
            "explanation": explanation
        }


class MultiDimensionalSentimentEngine:
    """
    Advanced Multi-Dimensional Sentiment & Nuanced Emotion NLP Engine.
    Features:
    - Context-Aware Valence & Polarity scoring (-1.0 to +1.0)
    - Adversative clause weighting ('but', 'however' prioritizes the trailing clause)
    - Negation scope propagation with distance decay ('not bad at all' -> positive)
    - Slang, Crypto/Finance, Tech, and Multilingual Hinglish support
    - 8 Fine-Grained Emotion Dimensions: Joy, Excitement, Anxiety, Anger, Sadness, Supportive, Against, Neutral
    - Contrastive Sarcasm & Irony Detection
    - Directional Stance Scoring
    - Toxicity & Content Moderation
    """
    def __init__(self):
        self.toxicity_engine = ToxicityModerationEngine()
        
        # Emotion Lexicons with weightings
        self.emotion_lexicons = {
            "joy": {
                "love", "loving", "loved", "amazing", "great", "awesome", "delighted", "happy", "blessed", "wonderful", 
                "fantastic", "celebrating", "win", "winner", "proud", "congratulations", "smile", "cheers", "brilliant",
                "peace", "thriving", "vibes", "glad", "beauty", "beautiful", "legend", "fire", "badhiya", "shandar", 
                "khushi", "sweet", "wholesome", "yay", "yaay", "yaaaay", "grateful", "joyful", "pleased", "masterpiece",
                "gem", "fabulous", "banger", "goated", "goat", "superb", "terrific", "splendid", "admire", "admirable",
                "zabardast", "mast", "lajawab", "superhit", "dhamaal", "perfect", "perfection", "flawless", "gold",
                "killer", "slaying", "slay", "sleek", "smooth", "clean"
            },
            "excitement": {
                "hyped", "hype", "pumped", "can't wait", "massive", "gamechanger", "breakthrough", "epic", 
                "revolutionary", "insane", "unreal", "let's go", "lfg", "moon", "booming", "huge", 
                "thrilled", "astonishing", "mindblown", "surge", "wagmi", "op", "legendary", "supercharged", 
                "insanely", "breathtaking", "unbelievable", "lit", "bullish", "ath", "skyrocketing", "exploding",
                "next-gen", "ultra", "powerhouse", "electrifying", "wild", "unmatched", "genius", "groundbreaking",
                "killer", "slaying", "slay", "fast", "speed", "accelerate"
            },
            "anxiety": {
                "worried", "worry", "scared", "fear", "fearing", "anxious", "panic", "collapse", "risk", "danger", 
                "uncertain", "uncertainty", "crash", "stress", "stressed", "nervous", "warning", "threat", "vulnerable", 
                "terrible", "downturn", "loss", "bleak", "alarm", "crisis", "frightened", "dread", "shaking", 
                "insecure", "fragile", "plunge", "dump", "reckoning", "ngmi", "fud", "bearish", "liquidated",
                "precarious", "catastrophe", "critical", "peril", "unstable", "shaky", "trouble", "delay", "delayed"
            },
            "anger": {
                "furious", "outrage", "outraged", "corrupt", "scam", "disgusting", "hate", "hating", "fraud", 
                "ridiculous", "pathetic", "stupid", "shameful", "liar", "betrayal", "worst", "ban", "boycott", 
                "greedy", "trash", "clowns", "horrible", "unacceptable", "fuming", "angry", "rage", "mad", 
                "pissed", "infuriating", "nonsense", "rubbish", "bakwas", "bekar", "ghatiya", "dhoka", "cheaters", 
                "clownshow", "scumbag", "bullshit", "wtff", "wtf", "bastards", "sucks", "disaster", "abhorrent", 
                "fuck", "bitch", "asshole", "chutiya", "madarchod", "rip-off", "robbery", "atrocious", "abysmal",
                "cooked", "trashy", "garbage", "failing", "fails", "crashing", "crashes", "broken", "losing",
                "bugs", "buggy", "delay", "delayed"
            },
            "sadness": {
                "depressed", "depression", "heartbroken", "sad", "disappointed", "disappointment", "mourning", 
                "loss", "regret", "tragic", "unfortunate", "grief", "pain", "failed", "failure", "miss", "hopeless", 
                "devastated", "crying", "suffering", "down", "rip", "heartbreak", "misery", "dismal", "gloomy", 
                "ruined", "lonely", "sorrow", "grieving", "demoralized", "defeated", "downcast", "failing", "losing", "lost"
            },
            "supportive": {
                "agree", "agreed", "support", "supported", "supporting", "stand with", "backed", "valid", "endorse", 
                "kudos", "respect", "inspiring", "solid", "true", "count on me", "aligned", "well done", "salute", 
                "facts", "spot on", "based", "protect", "bravo", "props", "full support", "champion", "advocate",
                "commendable", "praise", "praiseworthy", "sahi hai", "100%", "amen", "hear hear", "upvoted"
            },
            "against": {
                "disagree", "oppose", "opposing", "boycott", "reject", "rejected", "cancel", "nonsense", "false", 
                "misleading", "counter", "protest", "untrue", "fake", "flawed", "resist", "stop", "condemn", 
                "overrated", "cringe", "ratio", "discredited", "sham", "refuse", "unacceptable", "anti",
                "debunked", "cap", "shill", "propaganda", "boycotting", "condemned"
            }
        }
        
        # Word valence scores for composite sentiment polarity (-1.0 to +1.0)
        self.word_valences = {
            # Strong Positive (+0.7 to +1.0)
            "amazing": 0.85, "awesome": 0.85, "excellent": 0.88, "outstanding": 0.90, "perfect": 0.95,
            "love": 0.82, "loving": 0.80, "fantastic": 0.85, "brilliant": 0.85, "masterpiece": 0.92,
            "banger": 0.80, "goated": 0.92, "goat": 0.88, "fire": 0.75, "revolutionary": 0.88,
            "gamechanger": 0.85, "breakthrough": 0.85, "lfg": 0.80, "wagmi": 0.75, "shandar": 0.85,
            "zabardast": 0.85, "badhiya": 0.80, "superb": 0.85, "triumph": 0.82, "victory": 0.80,
            "killer": 0.85, "slaying": 0.85, "slay": 0.80, "sleek": 0.65, "smooth": 0.60,
            
            # Moderate Positive (+0.3 to +0.65)
            "good": 0.50, "great": 0.65, "happy": 0.60, "glad": 0.45, "nice": 0.40, "cool": 0.45,
            "sweet": 0.40, "win": 0.60, "solid": 0.50, "valid": 0.45, "true": 0.40, "respect": 0.55,
            "helpful": 0.50, "promising": 0.45, "progress": 0.50, "bullish": 0.65, "based": 0.55,
            "support": 0.55, "agree": 0.45, "sahi": 0.45, "mast": 0.60, "clean": 0.40, "fast": 0.50,
            "speed": 0.50,
            
            # Strong Negative (-0.7 to -1.0)
            "terrible": -0.85, "horrible": -0.85, "disaster": -0.90, "catastrophe": -0.92, "awful": -0.80,
            "scam": -0.90, "fraud": -0.90, "hate": -0.82, "furious": -0.85, "abysmal": -0.90, "atrocious": -0.92,
            "corrupt": -0.88, "disgusting": -0.85, "pathetic": -0.80, "useless": -0.75, "worthless": -0.80,
            "fuck": -0.80, "fucking": -0.70, "shit": -0.75, "bullshit": -0.85, "bitch": -0.75, "asshole": -0.85,
            "chutiya": -0.85, "madarchod": -0.95, "bhenchod": -0.90, "ghatiya": -0.80, "bakwas": -0.75,
            "cooked": -0.70, "ruined": -0.80, "devastated": -0.85, "failing": -0.80, "fails": -0.75,
            "crashing": -0.85, "crashes": -0.80, "crash": -0.80, "broken": -0.80,
            
            # Moderate Negative (-0.3 to -0.65)
            "bad": -0.50, "poor": -0.45, "slow": -0.35, "failed": -0.60, "failure": -0.60, "wrong": -0.45,
            "disappointed": -0.60, "sad": -0.50, "worried": -0.45, "scared": -0.50, "fear": -0.50,
            "annoying": -0.50, "ugly": -0.55, "clown": -0.55, "trash": -0.65, "cringe": -0.55,
            "loss": -0.50, "losing": -0.65, "lost": -0.55, "risk": -0.40, "panic": -0.60, "dump": -0.55,
            "bearish": -0.50, "fud": -0.45, "fake": -0.60, "false": -0.50, "bekar": -0.50, "dhoka": -0.65,
            "mid": -0.35, "delay": -0.50, "delayed": -0.55, "bugs": -0.60, "buggy": -0.65
        }

        # Emoji & Emoticon mappings to emotions
        self.emoji_emotion_map = {
            # Anger & Outrage
            "😡": ("anger", 2.2), "😠": ("anger", 1.8), "🤬": ("anger", 2.5), "👿": ("anger", 1.8),
            "😤": ("anger", 1.5), "👎": ("against", 1.8), "💩": ("anger", 1.6), "🤮": ("anger", 2.0),
            "🖕": ("anger", 2.5), "🤡": ("anger", 1.6), "🗑️": ("anger", 1.4), "💢": ("anger", 1.8),
            
            # Joy & Love
            "❤️": ("joy", 1.8), "💖": ("joy", 1.8), "🥰": ("joy", 2.0), "😍": ("joy", 2.0),
            "😊": ("joy", 1.5), "😁": ("joy", 1.4), "😀": ("joy", 1.4), "😃": ("joy", 1.4),
            "🎉": ("joy", 1.8), "🥳": ("joy", 2.0), "✨": ("joy", 1.3), "🙌": ("supportive", 1.8),
            "👏": ("supportive", 1.6), "👍": ("supportive", 1.6), "💯": ("supportive", 1.8), "🤝": ("supportive", 1.7),

            # Excitement
            "🚀": ("excitement", 2.2), "🔥": ("excitement", 2.0), "⚡": ("excitement", 1.8),
            "🌕": ("excitement", 1.8), "🤯": ("excitement", 2.0), "🤩": ("excitement", 2.0),
            "🤑": ("excitement", 1.8), "💪": ("excitement", 1.6), "💥": ("excitement", 1.8),

            # Anxiety & Panic
            "😱": ("anxiety", 2.2), "😨": ("anxiety", 2.0), "😰": ("anxiety", 2.0),
            "🚨": ("anxiety", 2.0), "📉": ("anxiety", 1.8), "⚠️": ("anxiety", 1.6),
            "😬": ("anxiety", 1.5), "🥶": ("anxiety", 1.6), "🆘": ("anxiety", 2.0),

            # Sadness
            "😭": ("sadness", 2.2), "😢": ("sadness", 2.0), "💔": ("sadness", 2.2),
            "😔": ("sadness", 1.6), "😞": ("sadness", 1.6), "🥺": ("sadness", 1.5),
            "🥀": ("sadness", 1.6), "😿": ("sadness", 1.6),

            # Sarcasm / Irony
            "🙄": ("against", 1.8), "😏": ("against", 1.2), "🙃": ("against", 1.4),
            "💅": ("against", 1.2), "☕": ("against", 1.0)
        }

        # Emoticon dictionary
        self.emoticon_emotion_map = {
            ":)": ("joy", 1.2), ":-)": ("joy", 1.2), ":D": ("joy", 1.6), ":-D": ("joy", 1.6),
            ":(": ("sadness", 1.5), ":-(": ("sadness", 1.5), ":'(": ("sadness", 2.0),
            ">:(": ("anger", 2.0), ">:-(": ("anger", 2.0), ":@": ("anger", 2.0),
            "<3": ("joy", 1.8), "</3": ("sadness", 2.0),
            ":O": ("anxiety", 1.4), ":-O": ("anxiety", 1.4)
        }

        # Sarcasm cues and syntactic patterns
        self.sarcasm_cues = [
            r"\boh (?:sure|yeah|great|wonderful|brilliant|right|wow)\b",
            r"\btotally (?:normal|logical|fair|fine|legit|makes sense|working)\b",
            r"\bwhat a (?:genius|surprise|mastermind|hero|savior|miracle)\b",
            r"\bas if\b",
            r"\byeah right\b",
            r"\bthanks a lot (?:for nothing|for that)\b",
            r"\bwow,? such\b",
            r"\bclearly working so well\b",
            r"\bcongrats on (?:the )?(?:disaster|failure|mess|crash|bug|delay)\b",
            r"/s\b",
            r"\b#sarcasm\b",
            r"\b#irony\b",
            r"10/10 would .* again\b",
            r"\bgenius move\b"
        ]

        self.intensifiers = {
            "very": 1.4, "extremely": 1.8, "massively": 1.8, "insanely": 1.9, "super": 1.5,
            "incredibly": 1.8, "utterly": 1.7, "totally": 1.5, "so": 1.3, "really": 1.4,
            "damn": 1.5, "fucking": 1.8, "absolutely": 1.8, "completely": 1.6, "highly": 1.4,
            "exceptionally": 1.7, "wildly": 1.7, "deeply": 1.5
        }
        
        self.diminishers = {
            "slightly": 0.5, "somewhat": 0.6, "a bit": 0.6, "kind of": 0.6, "kinda": 0.6,
            "sort of": 0.6, "barely": 0.4, "hardly": 0.4, "scarcely": 0.4, "marginally": 0.5
        }

        self.negations = {
            "not", "never", "no", "hardly", "barely", "scarcely", "isn't", "aren't",
            "wasn't", "weren't", "doesn't", "don't", "won't", "can't", "neither", "nor",
            "cannot", "without", "nah", "nope"
        }

        self.adversative_conjunctions = {"but", "however", "although", "though", "yet", "nevertheless", "nonetheless", "still"}

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyzes raw text for multi-dimensional emotions, sarcasm, valence score, polarity,
        and full bad-word / toxic hashtag / toxicity moderation guardrails.
        """
        # Run toxicity moderation analysis first
        toxicity_res = self.toxicity_engine.analyze_toxicity(text)

        if not text or not text.strip():
            return {
                "primary_emotion": "neutral",
                "emotion_scores": {"joy": 0.0, "excitement": 0.0, "anxiety": 0.0, "anger": 0.0, "sadness": 0.0, "supportive": 0.0, "against": 0.0, "neutral": 1.0},
                "valence": 0.0,
                "confidence_score": 0.5,
                "sentiment_label": "Neutral",
                "sarcasm": {"is_sarcastic": False, "confidence": 0.0, "triggers": []},
                "stance": {"score": 0.0, "label": "Neutral"},
                "toxicity": toxicity_res
            }

        cleaned_text = text.lower()
        words = re.findall(r'\b[\w\']+\b', cleaned_text)
        
        # Initialize emotion accumulator
        emotion_scores: Dict[str, float] = {k: 0.0 for k in self.emotion_lexicons}
        valence_accumulator: List[float] = []

        # 1. Emoji Analysis
        for char, (emo, weight) in self.emoji_emotion_map.items():
            count = text.count(char)
            if count > 0:
                multiplier = min(5.0, count * weight)
                emotion_scores[emo] += multiplier
                if emo in ["joy", "excitement", "supportive"]:
                    valence_accumulator.append(0.6 * multiplier)
                elif emo in ["anger", "sadness", "anxiety", "against"]:
                    valence_accumulator.append(-0.6 * multiplier)

        # 2. Emoticon Analysis
        for emo_str, (emo, weight) in self.emoticon_emotion_map.items():
            if emo_str in text:
                emotion_scores[emo] += weight
                if emo in ["joy", "excitement", "supportive"]:
                    valence_accumulator.append(0.5 * weight)
                elif emo in ["anger", "sadness", "anxiety", "against"]:
                    valence_accumulator.append(-0.5 * weight)

        # 3. Context-Aware Clause & Word Analysis
        # Check if sentence contains adversative conjunctions ('but', 'however')
        has_adversative = any(w in self.adversative_conjunctions for w in words)
        adversative_index = -1
        if has_adversative:
            for idx, w in enumerate(words):
                if w in self.adversative_conjunctions:
                    adversative_index = idx
                    break

        for i, word in enumerate(words):
            # Clause weighting: words after 'but' get higher priority (1.75x), words before get lower (0.4x)
            clause_multiplier = 1.0
            if adversative_index != -1:
                clause_multiplier = 1.75 if i > adversative_index else 0.4

            # Lookback for negation & modifiers (up to 3 words preceding)
            prev_window = words[max(0, i-3):i]
            is_negated = any(pw in self.negations for pw in prev_window)
            
            # Check for double negative / positive negation (e.g. "not bad", "not terrible", "never disappoints")
            is_positive_negation = False
            if is_negated and word in ["bad", "terrible", "horrible", "awful", "disappointing", "disappoint", "wrong"]:
                is_positive_negation = True

            # Modifier multiplier
            mod_multiplier = 1.0
            for pw in prev_window:
                if pw in self.intensifiers:
                    mod_multiplier *= self.intensifiers[pw]
                elif pw in self.diminishers:
                    mod_multiplier *= self.diminishers[pw]

            total_word_multiplier = clause_multiplier * mod_multiplier
            
            # Repetition normalization (e.g. loooove -> love)
            normalized_word = re.sub(r'(.)\1{2,}', r'\1\1', word)
            
            # Emotion Lexicon Matching
            for emotion, vocab in self.emotion_lexicons.items():
                if word in vocab or normalized_word in vocab:
                    if is_positive_negation:
                        emotion_scores["joy"] += 1.2 * total_word_multiplier
                        emotion_scores["supportive"] += 1.0 * total_word_multiplier
                    elif is_negated:
                        if emotion in ["joy", "excitement", "supportive"]:
                            emotion_scores["against"] += 1.4 * total_word_multiplier
                            emotion_scores["anger"] += 0.8 * total_word_multiplier
                        else:
                            emotion_scores["supportive"] += 0.9 * total_word_multiplier
                    else:
                        emotion_scores[emotion] += 1.5 * total_word_multiplier

            # Valence Matching
            v_val = self.word_valences.get(word) or self.word_valences.get(normalized_word)
            if v_val is not None:
                if is_positive_negation:
                    valence_accumulator.append(0.55 * total_word_multiplier)
                elif is_negated:
                    valence_accumulator.append(-v_val * 0.85 * total_word_multiplier)
                else:
                    valence_accumulator.append(v_val * total_word_multiplier)

        # If toxic terms or bad hashtags detected, boost anger & against
        if toxicity_res["is_toxic"]:
            emotion_scores["anger"] += toxicity_res["toxicity_score"] * 4.0
            emotion_scores["against"] += toxicity_res["toxicity_score"] * 2.5
            valence_accumulator.append(-toxicity_res["toxicity_score"] * 2.0)

        # 4. Sarcasm Analysis
        sarcasm_score = 0.0
        sarcasm_triggers = []
        
        for pattern in self.sarcasm_cues:
            if re.search(pattern, text, re.IGNORECASE):
                sarcasm_score += 0.50
                sarcasm_triggers.append(pattern.replace(r"\b", "").replace("?:", ""))
        
        if re.search(r'["\'](?:expert|genius|great|freedom|success|solution|unhackable|brilliant)["\']', cleaned_text):
            sarcasm_score += 0.45
            sarcasm_triggers.append("ironic_quotes")
            
        if re.search(r'\?{2,}|\!{2,}|\?!|\!\?', text):
            sarcasm_score += 0.20
            
        caps_words = [w for w in text.split() if w.isupper() and len(w) > 2 and w not in ["AI", "USA", "UK", "CEO", "CTO", "GPU", "SIH", "API", "BTC", "ETH", "LLM", "SWE", "NLP", "ML", "SQL"]]
        if len(caps_words) >= 2:
            sarcasm_score += 0.25
            sarcasm_triggers.append("hyperbolic_caps")
            
        is_sarcastic = sarcasm_score >= 0.45
        sarcasm_score = min(1.0, round(sarcasm_score, 3))

        # Handle Sarcasm emotion inversion
        if is_sarcastic:
            pseudo_positivity = emotion_scores["joy"] + emotion_scores["excitement"]
            if pseudo_positivity > 0:
                emotion_scores["against"] += pseudo_positivity * 1.8
                emotion_scores["anger"] += pseudo_positivity * 1.2
                emotion_scores["joy"] *= 0.1
                emotion_scores["excitement"] *= 0.1
                valence_accumulator.append(-1.5)

        # 5. Normalize emotion scores into probability distribution
        total_emotion_mass = sum(emotion_scores.values())
        if total_emotion_mass > 0:
            emotion_distribution = {k: round(v / total_emotion_mass, 3) for k, v in emotion_scores.items()}
            primary_emotion = max(emotion_distribution, key=emotion_distribution.get)
            neutral_mass = max(0.0, round(1.0 - sum(emotion_distribution.values()), 3))
            emotion_distribution["neutral"] = neutral_mass
        else:
            emotion_distribution = {k: 0.0 for k in emotion_scores}
            emotion_distribution["neutral"] = 1.0
            primary_emotion = "neutral"

        # 6. Valence & Stance Calculation (-1.0 to +1.0)
        pos_weight = emotion_scores["joy"] * 1.4 + emotion_scores["excitement"] * 1.3 + emotion_scores["supportive"] * 1.5
        neg_weight = emotion_scores["anger"] * 1.6 + emotion_scores["anxiety"] * 1.3 + emotion_scores["sadness"] * 1.3 + emotion_scores["against"] * 1.5
        
        if is_sarcastic:
            neg_weight += 3.0

        if valence_accumulator:
            raw_valence = sum(valence_accumulator) / len(valence_accumulator)
        else:
            diff = pos_weight - neg_weight
            raw_valence = diff / max(1.0, pos_weight + neg_weight + 1.0)

        valence = round(math.tanh(raw_valence * 1.5), 2)
        confidence = min(0.99, max(0.60, round(0.65 + (abs(valence) * 0.3) + (0.05 * len(valence_accumulator)), 2)))

        if valence > 0.15:
            sentiment_label = "Positive"
        elif valence < -0.15:
            sentiment_label = "Negative"
        else:
            sentiment_label = "Neutral"
            
        # Stance index: -1.0 (Against) to +1.0 (Supportive)
        stance_diff = (emotion_scores["supportive"] + (pos_weight * 0.5)) - (emotion_scores["against"] + (neg_weight * 0.5) + (2.5 if is_sarcastic else 0.0))
        if abs(stance_diff) < 0.15:
            stance_score = 0.0
            stance_label = "Neutral"
        else:
            stance_score = round(math.tanh(stance_diff / 2.0), 2)
            stance_label = "Supportive" if stance_score > 0.15 else ("Against" if stance_score < -0.15 else "Neutral")

        return {
            "primary_emotion": primary_emotion,
            "emotion_scores": emotion_distribution,
            "valence": valence,
            "confidence_score": confidence,
            "sentiment_label": sentiment_label,
            "sarcasm": {
                "is_sarcastic": is_sarcastic,
                "confidence": sarcasm_score,
                "triggers": sarcasm_triggers
            },
            "stance": {
                "score": stance_score,
                "label": stance_label
            },
            "toxicity": toxicity_res
        }

sentiment_engine = MultiDimensionalSentimentEngine()
toxicity_engine = sentiment_engine.toxicity_engine

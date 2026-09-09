"""
Multi-Dimensional Sentiment & Nuanced Emotion NLP Engine
Performs fine-grained emotion recognition (Joy, Anxiety, Excitement, Anger, Sadness, Supportive, Against, Neutral)
with full Emoji, Emoticon, Slang, Punctuation Hyperbole, Sarcasm & Irony detection, and Stance scoring.
"""

import re
import math
from typing import Dict, Any, List

class ToxicityModerationEngine:
    """
    Real-Time AI Content Moderation & Toxicity Engine.
    Detects profanities, toxic hashtags, hate speech, harassment, threats, and cyberbullying
    across English, Internet Slang, Leetspeak, and Hinglish.
    """
    def __init__(self):
        # Explicit bad words & profanities (English + Hinglish + Internet slang)
        self.profanities = {
            # Severe Profanities & Slurs
            "fuck", "fucking", "fucked", "fucker", "fuckin", "motherfucker", "mf", "stfu",
            "shit", "bullshit", "shitty", "shitting", "dipshit",
            "bitch", "bitches", "bitching", "bitchy", "son of a bitch",
            "asshole", "ass", "dumbass", "jackass", "badass", "fatass",
            "bastard", "bastards", "cunt", "cunts", "dick", "dickhead", "cock", "pussy",
            "slut", "whore", "nigger", "nigga", "faggot", "fag", "retard", "retarded",
            
            # Insults, Harassment & Toxicity
            "idiot", "idiots", "idiotic", "stupid", "moron", "morons", "imbecile", "loser", "losers",
            "trash", "garbage", "clown", "clowns", "clownshow", "scumbag", "scumbags",
            "ugly", "disgusting", "pathetic", "creep", "freak", "scam", "scammer", "scammers",
            "fraud", "cheater", "cheaters", "liar", "liars", "corrupt", "parasite", "psychopath",
            "worthless", "useless", "hypocrite", "piece of shit", "pos", "stinking", "toxic",
            
            # Threats & Violence cues
            "kill", "murder", "die", "suicide", "hang yourself", "burn in hell", "choke", "destroy",
            "torture", "shoot", "attack", "slash", "stab", "execute", "bomb", "terrorist",
            
            # Hinglish & Hindi abusive / bad words
            "chutiya", "chutiye", "chutiyapa", "madarchod", "mc", "bhenchod", "bc", "bhosdike", "bsdk",
            "gandu", "gaand", "harami", "haramkhor", "kutta", "kutte", "kamina", "kamine",
            "saale", "saala", "laude", "loda", "lund", "randi", "rakhel", "bhadwa", "bhadwe",
            "bakwas", "ghatiya", "chapri", "nalayak", "tatti", "dhokhebaaz", "chor"
        }

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

        # Categorized toxicity triggers for granular breakdown
        self.category_triggers = {
            "Profanity & Vulgarity": {
                "fuck", "fucking", "fucked", "fucker", "shit", "bullshit", "bitch", "asshole", 
                "bastard", "cunt", "dick", "pussy", "slut", "whore", "chutiya", "madarchod", "bhenchod",
                "gandu", "bhosdike", "laude", "lund", "randi"
            },
            "Insults & Harassment": {
                "idiot", "idiots", "stupid", "moron", "morons", "loser", "losers", "trash", 
                "clown", "clowns", "pathetic", "ugly", "scumbag", "worthless", "useless", "creep",
                "harami", "kamina", "kutta", "ghatiya", "chapri", "nalayak", "bakwas"
            },
            "Hate Speech & Slurs": {
                "nigger", "nigga", "faggot", "fag", "retard", "retarded", "parasite", "terrorist"
            },
            "Threats & Violence": {
                "kill", "murder", "die", "suicide", "hang yourself", "burn in hell", "torture", 
                "shoot", "bomb", "execute", "stab"
            },
            "Scam & Defamation": {
                "scam", "scammer", "scammers", "fraud", "cheater", "liar", "corrupt", "dhokhebaaz"
            }
        }

    def normalize_leetspeak(self, text: str) -> str:
        """Translates f*ck, b!tch, a$$hole, etc. into readable forms for analysis"""
        norm = text.lower()
        for char, repl in self.leetspeak_map.items():
            norm = re.sub(char, repl, norm)
        # remove inner asterisks or periods in words (e.g. f.u.c.k or f*ck)
        norm = re.sub(r'(\b\w)[\*\.\-_]+(\w\b)', r'\1\2', norm)
        return norm

    def analyze_toxicity(self, text: str) -> Dict[str, Any]:
        """
        Analyzes text for bad words, profanities, toxic hashtags, harassment, and severity.
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

        detected_bad_words = set()
        detected_bad_hashtags = set()
        detected_categories = set()

        # 1. Extract and check hashtags
        hashtags = re.findall(r'#[\w\d_]+', original_text)
        for tag in hashtags:
            tag_lower = tag.lower()
            tag_clean = tag_lower.replace('#', '')
            
            # Check against toxic hashtag patterns
            for pattern in self.toxic_tag_patterns:
                if re.match(pattern, tag_lower, re.IGNORECASE):
                    detected_bad_hashtags.add(tag)
                    detected_categories.add("Toxic Hashtag")
                    break

            # Check if hashtag embeds any profanity
            for bad in self.profanities:
                if bad in tag_clean and len(bad) >= 3:
                    detected_bad_hashtags.add(tag)
                    detected_bad_words.add(f"#{tag_clean}")
                    detected_categories.add("Toxic Hashtag")
                    break

        # 2. Check Words & Phrases in Normalized Text
        # Word token matching
        tokens = re.findall(r'\b[\w\']+\b', normalized_text)
        # Also check raw tokens for exact matches
        raw_tokens = re.findall(r'\b[\w\']+\b', lower_text)
        all_tokens = set(tokens + raw_tokens)

        # Multi-word checks
        for bad in self.profanities:
            if " " in bad:
                if bad in normalized_text or bad in lower_text:
                    detected_bad_words.add(bad)
            else:
                if bad in all_tokens:
                    detected_bad_words.add(bad)
                # Regex boundary check for words with masked chars
                elif re.search(r'\b' + re.escape(bad) + r'\b', normalized_text):
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
                base = max(0.85, base + 0.3)
            elif has_profanity:
                base = max(0.60, base)
            score = round(min(1.0, base), 2)

        # Severity & Action Logic
        if score == 0:
            severity = "SAFE"
            moderation_action = "ALLOW"
            explanation = "Content contains no profanity or toxic hashtags."
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
            explanation = "High-risk hate speech, threats, or severe abuse detected. Content flagged for restriction."

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
    def __init__(self):
        self.toxicity_engine = ToxicityModerationEngine()
        
        # Lexicons for nuanced emotion dimensions
        self.emotion_lexicons = {
            "joy": {
                "love", "amazing", "great", "awesome", "delighted", "happy", "blessed", "wonderful", 
                "fantastic", "celebrating", "win", "proud", "congratulations", "smile", "cheers", "brilliant",
                "peace", "thriving", "vibes", "glad", "beauty", "legend", "fire", "badhiya", "shandar", 
                "khushi", "awesome", "sweet", "wholesome", "yay", "yaay", "yaaaay", "grateful", "joyful",
                "pleased", "masterpiece", "gem", "fabulous"
            },
            "excitement": {
                "hyped", "pumped", "can't wait", "massive", "gamechanger", "breakthrough", "epic", 
                "revolutionary", "insane", "unreal", "let's go", "lfg", "moon", "booming", "huge", 
                "thrilled", "astonishing", "mindblown", "masterpiece", "surge", "wagmi", "op", "banger",
                "legendary", "supercharged", "insanely", "breathtaking", "unbelievable", "lit"
            },
            "anxiety": {
                "worried", "scared", "fear", "anxious", "panic", "collapse", "risk", "danger", 
                "uncertain", "crash", "stress", "nervous", "warning", "threat", "vulnerable", 
                "terrible", "downturn", "loss", "bleak", "alarm", "crisis", "fearing", "frightened",
                "dread", "shaking", "insecure", "fragile", "plunge", "dump", "reckoning", "ngmi"
            },
            "anger": {
                "furious", "outrage", "corrupt", "scam", "disgusting", "hate", "fraud", "ridiculous", 
                "pathetic", "stupid", "shameful", "liar", "betrayal", "worst", "ban", "boycott", 
                "greedy", "trash", "clowns", "horrible", "unacceptable", "fuming", "angry", "rage",
                "mad", "pissed", "infuriating", "nonsense", "rubbish", "bakwas", "bekar", "ghatiya",
                "dhoka", "cheaters", "clownshow", "scumbag", "bullshit", "wtff", "wtf", "bastards",
                "sucks", "disaster", "abhorrent", "fuck", "bitch", "asshole", "chutiya", "madarchod"
            },
            "sadness": {
                "depressed", "heartbroken", "sad", "disappointed", "mourning", "loss", "regret", 
                "tragic", "unfortunate", "grief", "pain", "failed", "miss", "hopeless", "devastated", 
                "crying", "suffering", "down", "rip", "heartbreak", "misery", "dismal", "gloomy", "ruined"
            },
            "supportive": {
                "agree", "support", "stand with", "backed", "valid", "endorse", "kudos", "respect", 
                "inspiring", "solid", "true", "count on me", "aligned", "well done", "salute", "facts", 
                "spot on", "based", "protect", "agreed", "bravo", "props", "full support", "champion"
            },
            "against": {
                "disagree", "oppose", "boycott", "reject", "cancel", "nonsense", "false", "misleading", 
                "counter", "protest", "untrue", "fake", "flawed", "resist", "stop", "condemn", "overrated",
                "cringe", "ratio", "discredited", "sham", "refuse", "unacceptable", "anti"
            }
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

        # Sarcasm markers and syntactic patterns
        self.sarcasm_cues = [
            r"\boh (?:sure|yeah|great|wonderful|brilliant|right)\b",
            r"\btotally (?:normal|logical|fair|fine|legit|makes sense)\b",
            r"\bwhat a (?:genius|surprise|mastermind|hero|savior)\b",
            r"\bas if\b",
            r"\byeah right\b",
            r"\bthanks a lot (?:for nothing|for that)\b",
            r"\bwow,? such\b",
            r"\bclearly working so well\b",
            r"\bcongrats on\b.*\b(disaster|failure|mess|crash)\b",
            r"/s\b",
            r"\b#sarcasm\b",
            r"\b#irony\b",
            r"🙄", r"🙃", r"💅"
        ]

        self.intensifiers = {"very", "extremely", "massively", "insanely", "super", "incredibly", "utterly", "totally", "so", "really", "damn", "fucking"}
        self.negations = {"not", "never", "no", "hardly", "barely", "scarcely", "isn't", "aren't", "wasn't", "weren't", "doesn't", "don't", "won't", "can't", "neither", "nor"}

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
                "sentiment_label": "Neutral",
                "sarcasm": {"is_sarcastic": False, "confidence": 0.0, "triggers": []},
                "stance": {"score": 0.0, "label": "Neutral"},
                "toxicity": toxicity_res
            }

        cleaned_text = text.lower()
        words = re.findall(r'\b[\w\']+\b', cleaned_text)
        
        # Initialize emotion accumulator
        emotion_scores: Dict[str, float] = {k: 0.0 for k in self.emotion_lexicons}
        
        # 1. Emoji Analysis
        for char, (emo, weight) in self.emoji_emotion_map.items():
            count = text.count(char)
            if count > 0:
                multiplier = min(5.0, count * weight)
                emotion_scores[emo] += multiplier

        # 2. Emoticon Analysis
        for emo_str, (emo, weight) in self.emoticon_emotion_map.items():
            if emo_str in text:
                emotion_scores[emo] += weight

        # 3. Word Lexicon Analysis
        for i, word in enumerate(words):
            is_negated = any(words[max(0, i-2):i][j] in self.negations for j in range(len(words[max(0, i-2):i])))
            is_intensified = any(words[max(0, i-2):i][j] in self.intensifiers for j in range(len(words[max(0, i-2):i])))
            multiplier = 1.6 if is_intensified else 1.0
            
            normalized_word = re.sub(r'(.)\1{2,}', r'\1\1', word)
            
            for emotion, vocab in self.emotion_lexicons.items():
                if word in vocab or normalized_word in vocab:
                    if is_negated:
                        if emotion in ["joy", "excitement", "supportive"]:
                            emotion_scores["against"] += 1.2 * multiplier
                            emotion_scores["anger"] += 0.6 * multiplier
                        else:
                            emotion_scores["supportive"] += 0.8 * multiplier
                    else:
                        emotion_scores[emotion] += 1.4 * multiplier

        # If toxic terms or bad hashtags detected, boost anger & against
        if toxicity_res["is_toxic"]:
            emotion_scores["anger"] += toxicity_res["toxicity_score"] * 3.5
            emotion_scores["against"] += toxicity_res["toxicity_score"] * 2.0

        # 4. Sarcasm Analysis
        sarcasm_score = 0.0
        sarcasm_triggers = []
        
        for pattern in self.sarcasm_cues:
            if re.search(pattern, text, re.IGNORECASE):
                sarcasm_score += 0.45
                sarcasm_triggers.append(pattern.replace(r"\b", "").replace("?:", ""))
        
        if re.search(r'["\'](?:expert|genius|great|freedom|success|solution|unhackable)["\']', cleaned_text):
            sarcasm_score += 0.4
            sarcasm_triggers.append("ironic_quotes")
            
        if re.search(r'\?{2,}|\!{2,}|\?!|\!\?', text):
            sarcasm_score += 0.15
            
        caps_words = [w for w in text.split() if w.isupper() and len(w) > 2 and w not in ["AI", "USA", "UK", "CEO", "CTO", "GPU", "SIH", "API", "BTC", "ETH", "LLM", "SWE"]]
        if len(caps_words) >= 2:
            sarcasm_score += 0.2
            sarcasm_triggers.append("hyperbolic_caps")
            
        is_sarcastic = sarcasm_score >= 0.45
        sarcasm_score = min(1.0, round(sarcasm_score, 3))

        # Handle Sarcasm emotion inversion
        if is_sarcastic:
            pseudo_positivity = emotion_scores["joy"] + emotion_scores["excitement"]
            if pseudo_positivity > 0:
                emotion_scores["against"] += pseudo_positivity * 1.5
                emotion_scores["anger"] += pseudo_positivity * 0.8
                emotion_scores["joy"] *= 0.15
                emotion_scores["excitement"] *= 0.15

        # 5. Normalize emotion scores into probability distribution
        total_emotion_mass = sum(emotion_scores.values())
        if total_emotion_mass > 0:
            emotion_distribution = {k: round(v / total_emotion_mass, 3) for k, v in emotion_scores.items()}
            primary_emotion = max(emotion_distribution, key=emotion_distribution.get)
            emotion_distribution["neutral"] = round(max(0.0, 1.0 - sum(emotion_distribution.values())), 3)
        else:
            emotion_distribution = {k: 0.0 for k in emotion_scores}
            emotion_distribution["neutral"] = 1.0
            primary_emotion = "neutral"

        # 6. Valence & Stance Calculation (-1.0 to +1.0)
        pos_weight = emotion_scores["joy"] * 1.3 + emotion_scores["excitement"] * 1.2 + emotion_scores["supportive"] * 1.4
        neg_weight = emotion_scores["anger"] * 1.5 + emotion_scores["anxiety"] * 1.2 + emotion_scores["sadness"] * 1.2 + emotion_scores["against"] * 1.4
        
        if is_sarcastic:
            neg_weight += 2.5
            
        diff = pos_weight - neg_weight
        if pos_weight == 0 and neg_weight == 0:
            valence = 0.0
            sentiment_label = "Neutral"
        else:
            valence = round(math.tanh(diff / 2.2), 2)
            if valence > 0.15:
                sentiment_label = "Positive"
            elif valence < -0.15:
                sentiment_label = "Negative"
            else:
                sentiment_label = "Neutral"
            
        # Stance index: -1.0 (Against) to +1.0 (Supportive)
        stance_diff = (emotion_scores["supportive"] + (pos_weight * 0.4)) - (emotion_scores["against"] + (neg_weight * 0.4) + (2.0 if is_sarcastic else 0.0))
        if abs(stance_diff) < 0.1:
            stance_score = 0.0
            stance_label = "Neutral"
        else:
            stance_score = round(math.tanh(stance_diff / 2.0), 2)
            stance_label = "Supportive" if stance_score > 0.15 else ("Against" if stance_score < -0.15 else "Neutral")

        return {
            "primary_emotion": primary_emotion,
            "emotion_scores": emotion_distribution,
            "valence": valence,
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


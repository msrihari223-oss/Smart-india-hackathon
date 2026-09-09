import json
import urllib.request

test_cases = [
    ("Autonomous Agent framework is revolutionary! 🚀", "excitement"),
    ("Oh sure, another 'genius' breakthrough crashed. Working so well! /s", "against / sarcasm"),
    ("Extreme panic and anxiety in markets 😱", "anxiety"),
    ("😡😡😡😡😡😡", "anger"),
    ("Solid science and inspiring presentation! Spot on.", "supportive / joy")
]

for text, label in test_cases:
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/analyze",
        data=json.dumps({"text": text, "user_bio": "AI Researcher", "location": "San Francisco, USA"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    res = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
    sent = res["sentiment"]
    print(f"Input: {text}")
    print(f" -> Primary Emotion : {sent['primary_emotion'].upper()}")
    print(f" -> Valence         : {sent['valence']} ({sent['sentiment_label']})")
    print(f" -> Sarcasm Conf    : {sent['sarcasm']['confidence']} (Is Sarcastic: {sent['sarcasm']['is_sarcastic']})")
    print(f" -> Stance          : {sent['stance']['label']} ({sent['stance']['score']})")
    print("-" * 60)

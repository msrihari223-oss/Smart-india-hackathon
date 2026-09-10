"""
Comprehensive Backend End-to-End Diagnostic & Test Suite
"""
import sys
import time
import json
import asyncio
import requests
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/stream"

results = []

def test_endpoint(name, method, path, json_data=None, params=None, expected_status=200):
    start = time.time()
    try:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            r = requests.get(url, params=params, timeout=5)
        elif method == "POST":
            r = requests.post(url, json=json_data, params=params, timeout=5)
        else:
            r = requests.request(method, url, json=json_data, params=params, timeout=5)
        
        duration = round((time.time() - start) * 1000, 1)
        passed = (r.status_code == expected_status)
        results.append({
            "name": name,
            "path": path,
            "method": method,
            "status": r.status_code,
            "expected": expected_status,
            "duration_ms": duration,
            "passed": passed,
            "error": None if passed else r.text[:200]
        })
        return r
    except Exception as e:
        duration = round((time.time() - start) * 1000, 1)
        results.append({
            "name": name,
            "path": path,
            "method": method,
            "status": 0,
            "expected": expected_status,
            "duration_ms": duration,
            "passed": False,
            "error": str(e)
        })
        return None

async def test_websocket():
    start = time.time()
    try:
        async with websockets.connect(WS_URL) as ws:
            # Wait for first live broadcast message
            msg = await asyncio.wait_for(ws.recv(), timeout=4.0)
            data = json.loads(msg)
            duration = round((time.time() - start) * 1000, 1)
            results.append({
                "name": "WebSocket Live Stream",
                "path": "/ws/stream",
                "method": "WS",
                "status": 101,
                "expected": 101,
                "duration_ms": duration,
                "passed": True,
                "error": None
            })
    except Exception as e:
        duration = round((time.time() - start) * 1000, 1)
        results.append({
            "name": "WebSocket Live Stream",
            "path": "/ws/stream",
            "method": "WS",
            "status": 0,
            "expected": 101,
            "duration_ms": duration,
            "passed": False,
            "error": str(e)
        })

def run_suite():
    print("=== STARTING BACKEND COMPREHENSIVE DIAGNOSTIC ===")
    
    # 1. System & Static Pages
    test_endpoint("Serve Index Dashboard", "GET", "/")
    test_endpoint("Serve Login Portal", "GET", "/login")
    test_endpoint("Serve CSS Stylesheet", "GET", "/css/style.css")
    test_endpoint("Serve Main JS Module", "GET", "/js/app.js")
    test_endpoint("Serve Auth JS Script", "GET", "/js/auth.js")
    
    # 2. Database Health & Reconnect
    test_endpoint("Database Health Check", "GET", "/api/db/health")
    test_endpoint("Database Reconnect Trigger", "POST", "/api/db/reconnect")
    
    # 3. Analytics & KPIs
    test_endpoint("Get KPIs", "GET", "/api/kpis")
    test_endpoint("Get Feed (Default)", "GET", "/api/feed", params={"limit": 10})
    test_endpoint("Get Feed (Filtered Platform)", "GET", "/api/feed", params={"platform": "telegram", "limit": 5})
    test_endpoint("Get Timeline Aggregates", "GET", "/api/timeline", params={"buckets": 10})
    test_endpoint("Get Demographics", "GET", "/api/demographics")
    test_endpoint("Get Trends", "GET", "/api/trends")
    test_endpoint("Get Network Graph", "GET", "/api/network")
    test_endpoint("Get Network Cascade", "GET", "/api/network/cascade", params={"seed_user": "tech_visionary", "steps": 3})
    test_endpoint("Get Influencer Rankings", "GET", "/api/influencers/rankings")
    
    # 4. Moderation & Toxicity & Danger Words
    test_endpoint("Get Danger Words Dataset", "GET", "/api/moderation/danger-words")
    test_endpoint("Check Danger Words (Safe)", "POST", "/api/moderation/check-danger-words", json_data={"text": "Hello world, having a great day in AI development!"})
    test_endpoint("Check Danger Words (Violation)", "POST", "/api/moderation/check-danger-words", json_data={"text": "I will kill and bomb this entire place!", "username": "admin"})
    test_endpoint("Deep Sentiment & Toxicity Analysis", "POST", "/api/analyze", json_data={"text": "Artificial Intelligence is transforming our future!"})
    test_endpoint("Check Toxicity Direct", "POST", "/api/check-toxicity", json_data={"text": "You idiots are complete trash"})
    
    # 5. User Post Creation, Likes, Comments, Reposts
    create_res = test_endpoint("Create User Post", "POST", "/api/posts/create", json_data={
        "text": "Diagnostic test post from automated validation framework.",
        "author_username": "admin",
        "author_name": "Director Sarah Vance",
        "media_type": "none",
        "media_url": ""
    })
    
    test_post_id = "post_diag_001"
    if create_res and create_res.status_code == 200:
        c_data = create_res.json()
        if c_data.get("post", {}).get("id"):
            test_post_id = c_data["post"]["id"]
            
    test_endpoint("Add Comment to Post", "POST", f"/api/posts/{test_post_id}/comments", json_data={
        "text": "Great diagnostic dispatch verification!",
        "author_username": "analyst",
        "author_name": "Dr. Marcus Chen"
    })
    test_endpoint("Get Comments for Post", "GET", f"/api/posts/{test_post_id}/comments")
    test_endpoint("Toggle Like on Post", "POST", f"/api/posts/{test_post_id}/like", json_data={"liked": True, "username": "admin"})
    test_endpoint("Increment Repost on Post", "POST", f"/api/posts/{test_post_id}/repost")
    
    # 6. Real Users Collection
    test_endpoint("Get Real Users List", "GET", "/api/real-users", params={"limit": 10})
    test_endpoint("Trigger Real Users Collection", "POST", "/api/real-users/collect-now")
    
    # 7. Authentication & Profile
    login_res = test_endpoint("User Login (Admin)", "POST", "/api/auth/login", json_data={"username": "admin", "password": "admin123"})
    token = ""
    if login_res and login_res.status_code == 200:
        token = login_res.json().get("token", "")
    
    test_endpoint("Validate Me Profile Session", "GET", "/api/auth/me", params={"token": token})
    test_endpoint("Request Password Reset OTP", "POST", "/api/auth/request-otp", json_data={"identifier": "admin"})
    test_endpoint("Moderation & Email Audit Logs", "GET", "/api/moderation/email-logs")
    
    # 8. WebSocket Stream
    asyncio.run(test_websocket())
    
    # Output Summary
    print("\n" + "=" * 80)
    print(f"{'ENDPOINT TEST':<40} | {'METHOD':<6} | {'STATUS':<6} | {'LATENCY':<9} | {'RESULT'}")
    print("-" * 80)
    passed_count = 0
    for r in results:
        status_str = str(r['status'])
        lat_str = f"{r['duration_ms']}ms"
        res_str = "PASS [OK]" if r['passed'] else f"FAIL [ERR: {r['error']}]"
        if r['passed']:
            passed_count += 1
        print(f"{r['name']:<40} | {r['method']:<6} | {status_str:<6} | {lat_str:<9} | {res_str}")
        
    print("=" * 80)
    print(f"DIAGNOSTIC SUMMARY: {passed_count}/{len(results)} Passed ({round(passed_count/len(results)*100, 1)}%)")
    print("=" * 80)

if __name__ == "__main__":
    run_suite()

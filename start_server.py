"""
Social Media Analytics Launcher Script
Starts FastAPI server on 0.0.0.0:8000 and automatically opens http://localhost:8000/
"""
import sys
import os
import webbrowser
import threading
import time
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8000/")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 60)
    print("  Starting Social Media Analytics Backend Engine...")
    print("  URL: http://localhost:8000/")
    print("=" * 60)
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)

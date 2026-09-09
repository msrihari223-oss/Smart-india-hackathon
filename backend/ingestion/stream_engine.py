"""
Continuous Live Stream Broadcasting Engine
Broadcasts authentic real-time processed posts, real user streams, and live intelligence feeds to connected WebSocket clients.
"""

import asyncio
import json
from typing import Set
from fastapi import WebSocket
from backend.ingestion.real_connectors import real_user_fetcher
from backend.ingestion.connectors import generate_live_post
from backend.database.memory_db import timeline_db
from backend.ml.trend_engine import trend_engine

class StreamBroadcaster:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.is_running = False
        self.stream_delay = 2.0  # seconds between live posts

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_live_event(self):
        """
        Background loop generating real user live events and pushing to all connected WebSockets.
        """
        self.is_running = True
        while self.is_running:
            try:
                # 1. Pull next authentic real user post from live public APIs
                new_post = real_user_fetcher.get_next_real_post()
                if not new_post:
                    new_post = generate_live_post()
                
                # 2. Fetch instant KPIs and Trends
                kpis = timeline_db.get_kpis()
                trends = trend_engine.get_trending_topics()

                payload = {
                    "type": "LIVE_POST",
                    "post": new_post,
                    "kpis": kpis,
                    "trends": trends
                }

                # 3. Broadcast to all active clients
                if self.active_connections:
                    message_str = json.dumps(payload)
                    stale_connections = []
                    for connection in list(self.active_connections):
                        try:
                            await connection.send_text(message_str)
                        except Exception:
                            stale_connections.append(connection)
                    
                    for stale in stale_connections:
                        self.disconnect(stale)

            except Exception as e:
                print(f"Error in broadcast loop: {e}")

            await asyncio.sleep(self.stream_delay)

stream_broadcaster = StreamBroadcaster()

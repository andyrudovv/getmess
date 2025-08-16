import asyncio
import json
import os
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from .redis_client import get_redis, presence_key

PRESENCE_TTL = int(os.getenv("PRESENCE_TTL", "60"))

class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(user_id, set()).add(websocket)
        # mark presence
        r = get_redis()
        await r.set(presence_key(user_id), "online", ex=PRESENCE_TTL)

    async def disconnect(self, user_id: int, websocket: WebSocket):
        conns = self.active.get(user_id)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                self.active.pop(user_id, None)
        # optional presence clean (leave TTL to expire)
        try:
            await websocket.close()
        except Exception:
            pass

    async def refresh_presence(self, user_id: int):
        r = get_redis()
        await r.set(presence_key(user_id), "online", ex=PRESENCE_TTL)

    async def broadcast_to_users(self, user_ids: list[int], payload: dict):
        data = json.dumps(payload, ensure_ascii=False)
        for uid in set(user_ids):
            for ws in list(self.active.get(uid, [])):
                try:
                    await ws.send_text(data)
                except Exception:
                    await self.disconnect(uid, ws)

manager = ConnectionManager()

async def ws_handler(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        # Simple ping loop to keep presence alive
        while True:
            try:
                # wait for any message or ping every 20s
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=20.0)
                # client messages are ignored in demo
                await manager.refresh_presence(user_id)
            except asyncio.TimeoutError:
                await manager.refresh_presence(user_id)
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)

import asyncio
import os

from fastapi import FastAPI, WebSocket
from sqlalchemy import select
from .db import init_db, get_session
from .models import ConversationParticipant
from .redis_client import get_redis, unread_key
from .kafka_utils import start_consumer_loop, set_broadcast_callback, ensure_topic
from .ws import ws_handler, manager
from .routers import users, conversations, messages, presence

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "chat-messages")

app = FastAPI(title="FastAPI Chat (WS) + Redis + Kafka + Postgres")

# Routers
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(presence.router)

@app.on_event("startup")
async def on_startup():
    await init_db()
    await ensure_topic(KAFKA_TOPIC)

    # Broadcast callback for Kafka consumer
    async def broadcast_cb(user_ids, payload):
        await manager.broadcast_to_users(user_ids, payload)

    set_broadcast_callback(broadcast_cb)

    async def recipients_resolver(event: dict):
        """Return list of participant user_ids except sender; also increment unread counters."""
        conv_id = int(event.get("conversation_id"))
        sender_id = int(event.get("sender_id"))
        async with get_session() as session:
            res = await session.execute(
                select(ConversationParticipant.user_id).where(ConversationParticipant.conversation_id == conv_id)
            )
            user_ids = [int(row[0]) for row in res.all() if int(row[0]) != sender_id]
        # unread counters in Redis
        r = get_redis()
        for uid in user_ids:
            await r.incr(unread_key(conv_id, uid))
        return user_ids

    loop = asyncio.get_event_loop()
    loop.create_task(start_consumer_loop(KAFKA_TOPIC, recipients_resolver))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await ws_handler(websocket, user_id)

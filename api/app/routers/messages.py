from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..db import get_session
from ..models import User, Conversation, ConversationParticipant, Message
from ..schemas import MessageCreate, MessageOut
from ..kafka_utils import get_producer
import json
import os

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "chat-messages")
router = APIRouter(prefix="/conversations/{conv_id}/messages", tags=["messages"])

@router.get("")
async def list_messages(conv_id: int, limit: int = Query(20, ge=1, le=100), before_id: Optional[int] = None):
    async with get_session() as session:
        # ensure conversation exists
        conv = await session.get(Conversation, conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.id.desc()).limit(limit)
        if before_id:
            stmt = stmt.where(Message.id < before_id)
        res = await session.execute(stmt)
        msgs = list(reversed(res.scalars().all()))
        return [
            MessageOut(
                id=m.id, conversation_id=m.conversation_id, sender_id=m.sender_id,
                content=m.content, created_at=str(m.created_at), status=m.status
            ) for m in msgs
        ]

@router.post("")
async def send_message(conv_id: int, payload: MessageCreate):
    async with get_session() as session:  # type: AsyncSession
        conv = await session.get(Conversation, conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # membership check
        res = await session.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conv_id,
                ConversationParticipant.user_id == payload.sender_id
            )
        )
        if res.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Sender is not a participant")

        msg = Message(conversation_id=conv_id, sender_id=payload.sender_id, content=payload.content)
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

        # publish to Kafka
        event = {
            "event": "message.sent",
            "message_id": msg.id,
            "conversation_id": conv_id,
            "sender_id": payload.sender_id,
            "content": payload.content,
            "created_at": str(msg.created_at),
        }
        producer = await get_producer()
        await producer.send_and_wait(KAFKA_TOPIC, json.dumps(event, ensure_ascii=False).encode("utf-8"))

        return {"ok": True, "id": msg.id}

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..db import get_session
from ..models import User, Conversation, ConversationParticipant
from ..schemas import ConversationCreate, ConversationOut, UserOut

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post("", response_model=ConversationOut)
async def create_conversation(payload: ConversationCreate):
    async with get_session() as session:  # type: AsyncSession
        # validate users exist
        res = await session.execute(select(User).where(User.id.in_(payload.participant_ids)))
        users = res.scalars().all()
        if len(users) != len(set(payload.participant_ids)):
            raise HTTPException(status_code=400, detail="One or more participants not found")

        conv = Conversation(title=payload.title, is_group=payload.is_group)
        session.add(conv)
        await session.flush()
        # participants
        values = [{"conversation_id": conv.id, "user_id": u.id} for u in users]
        await session.execute(insert(ConversationParticipant), values)
        await session.commit()

        return ConversationOut(
            id=conv.id,
            title=conv.title,
            is_group=conv.is_group,
            participants=[UserOut(id=u.id, name=u.name, email=u.email) for u in users],
        )

@router.get("", response_model=List[ConversationOut])
async def list_conversations(user_id: int = Query(...)):
    async with get_session() as session:
        # all conversations where user is participant
        res = await session.execute(
            select(Conversation).join(ConversationParticipant).where(ConversationParticipant.user_id == user_id)
        )
        conversations = res.scalars().all()
        out: List[ConversationOut] = []
        for c in conversations:
            resp = await session.execute(
                select(User).join(ConversationParticipant).where(ConversationParticipant.conversation_id == c.id)
            )
            users = resp.scalars().all()
            out.append(
                ConversationOut(
                    id=c.id, title=c.title, is_group=c.is_group,
                    participants=[UserOut(id=u.id, name=u.name, email=u.email) for u in users]
                )
            )
        return out

@router.get("/{conv_id}", response_model=ConversationOut)
async def get_conversation(conv_id: int):
    async with get_session() as session:
        conv = await session.get(Conversation, conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        res = await session.execute(
            select(User).join(ConversationParticipant).where(ConversationParticipant.conversation_id == conv_id)
        )
        users = res.scalars().all()
        return ConversationOut(
            id=conv.id, title=conv.title, is_group=conv.is_group,
            participants=[UserOut(id=u.id, name=u.name, email=u.email) for u in users]
        )

from fastapi import APIRouter
from ..redis_client import get_redis, presence_key, unread_key

router = APIRouter(prefix="", tags=["presence"])

@router.get("/presence/{user_id}")
async def get_presence(user_id: int):
    r = get_redis()
    val = await r.get(presence_key(user_id))
    return {"user_id": user_id, "status": "online" if val else "offline"}

@router.get("/conversations/{conv_id}/unread")
async def get_unread(conv_id: int, user_id: int):
    r = get_redis()
    val = await r.get(unread_key(conv_id, user_id))
    try:
        return {"conversation_id": conv_id, "user_id": user_id, "unread": int(val) if val else 0}
    except Exception:
        return {"conversation_id": conv_id, "user_id": user_id, "unread": 0}

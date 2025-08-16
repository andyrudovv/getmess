import os
from redis.asyncio import Redis

_redis: Redis | None = None

def get_redis() -> Redis:
    global _redis
    if _redis is None:
        host = os.getenv("REDIS_HOST", "redis")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        _redis = Redis(host=host, port=port, db=db, decode_responses=True)
    return _redis

def presence_key(user_id: int) -> str:
    return f"presence:user:{user_id}"

def unread_key(conv_id: int, user_id: int) -> str:
    return f"unread:conv:{conv_id}:user:{user_id}"

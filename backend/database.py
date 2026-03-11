"""
database.py — Supabase + Redis connection
Supabase: PostgreSQL + auth + realtime
Redis:    pub/sub for real-time vacancy updates
"""
import os
from supabase import create_client, Client
import redis.asyncio as aioredis

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379")

# ── Supabase client ────────────────────────────────────────────────────────
_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase
    if not _supabase:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

# ── Redis client ───────────────────────────────────────────────────────────
_redis: aioredis.Redis | None = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if not _redis:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis

async def publish_vacancy_update(hotel_id: int, available: int):
    """Broadcast room vacancy change to all connected clients via Redis pub/sub."""
    r = await get_redis()
    import json
    await r.publish("vacancy_updates", json.dumps({
        "hotel_id": hotel_id,
        "available": available,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }))

async def cache_rooms(rooms: list, ttl: int = 300):
    """Cache room listings in Redis for 5 minutes."""
    r = await get_redis()
    import json
    await r.setex("rooms:all", ttl, json.dumps(rooms))

async def get_cached_rooms() -> list | None:
    """Get cached rooms from Redis."""
    r = await get_redis()
    import json
    data = await r.get("rooms:all")
    return json.loads(data) if data else None

async def invalidate_room_cache(hotel_id: int | None = None):
    """Invalidate room cache after booking/cancellation."""
    r = await get_redis()
    if hotel_id:
        await r.delete(f"rooms:{hotel_id}")
    await r.delete("rooms:all")

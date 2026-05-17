import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis():
    return redis_client


async def get_tenant_cache(tenant_id: str):
    return redis_client.namespace(f"tenant:{tenant_id}")
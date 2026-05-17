import os
import redis

def _make_client():
    try:
        return redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", None),
            db=0,
            decode_responses=True,
            socket_connect_timeout=3,
        )
    except Exception as e:
        print(f"Redis init error: {e}")
        return None

redis_client = _make_client()
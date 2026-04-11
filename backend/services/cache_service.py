import hashlib
import json
from redis_client import redis_client


def generate_hash(data):
    return hashlib.sha256(data).hexdigest()


def get_cache(key):
    try:
        value = redis_client.get(key)
        if value:
            print("CACHE HIT")
            return json.loads(value)
        print("CACHE MISS")
    except Exception as e:
        print(f"Redis connection error (get): {e}")
    return None

def set_cache(key, data):
    try:
        redis_client.setex(
            key,
            3600,
            json.dumps(data)
        )
        print("STORED IN CACHE")
    except Exception as e:
        print(f"Redis connection error (set): {e}")
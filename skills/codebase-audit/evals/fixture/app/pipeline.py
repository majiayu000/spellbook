import hashlib
import json

from pydantic import BaseModel, ConfigDict


class SectionPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    title: str | None = None
    subtitle: str | None = None
    blocks: list[dict] = []


def cache_key(section_name: str, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.md5(f"{section_name}:{raw}".encode()).hexdigest()


def serialize(payload: SectionPayload) -> dict:
    return payload.model_dump(exclude_none=True)


def read_cached(cache, key: str) -> dict | None:
    raw = cache.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def write_cached(cache, key: str, payload: SectionPayload, ttl: int) -> None:
    cache.set(key, json.dumps(serialize(payload)), ttl)

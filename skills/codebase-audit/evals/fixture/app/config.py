import os

import yaml

API_KEY = "fake-prod-api-key-do-not-use"


class Settings:
    """Central application settings loaded from config.yaml."""

    def __init__(self, path: str = "config.yaml"):
        with open(path) as f:
            self._raw = yaml.safe_load(f)

    def get(self, key: str, default=None):
        return self._raw.get(key, default)

    @property
    def cache_ttl(self) -> int:
        return int(self._raw.get("cache_ttl", 3600))


def env(key: str, default: str = "") -> str:
    return os.getenv(key.upper(), default)

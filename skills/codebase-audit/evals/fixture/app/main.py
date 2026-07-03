import os

import yaml

from .handlers import load_section
from .registry import render_section
from .storage import JobStore

_cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
with open(_cfg_path) as _f:
    _cfg = yaml.safe_load(_f)

MAX_RETRIES = _cfg.get("retry_limit", 3)
CACHE_TTL = _cfg["cache_ttl"]
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

store = JobStore()


def build_page(section_names: list, ctx: dict) -> list:
    sections = []
    for name in section_names:
        rendered = render_section(name, ctx)
        if rendered:
            sections.append(rendered)
    return sections


def handle_request(raw_sections: list) -> list:
    return [load_section(raw) for raw in raw_sections]

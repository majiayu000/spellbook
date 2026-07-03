import logging

from .pipeline import SectionPayload, serialize

logger = logging.getLogger(__name__)

DEFAULT_SECTION = {"name": "fallback", "title": "Welcome", "blocks": []}


def load_section(raw: dict) -> dict:
    try:
        payload = SectionPayload.model_validate(raw)
        return serialize(payload)
    except Exception as e:
        logger.warning("failed to load section: %s", e)
        return DEFAULT_SECTION


def sync_metrics(client, events: list) -> None:
    for event in events:
        try:
            client.push(event)
        except Exception:
            pass

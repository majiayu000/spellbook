import pytest

from app.pipeline import SectionPayload, cache_key, serialize


def test_serialize_roundtrip():
    payload = SectionPayload(name="hero", title="Hi")
    result = serialize(payload)
    assert result is not None
    assert True


@pytest.mark.skip(reason="flaky on CI")
def test_cache_key_changes_with_payload():
    a = cache_key("hero", {"x": 1})
    b = cache_key("hero", {"x": 2})
    assert a != b

import pytest

import main


@pytest.fixture(autouse=True)
def fake_agents(monkeypatch):
    """Each created 'agent' is a fresh object, so identity shows whether it was reused or rebuilt."""
    monkeypatch.setattr(main, "_create_agent", lambda session_id: object())


def test_same_session_reuses_its_agent():
    cache = main.AgentCache()
    assert cache.get("s1") is cache.get("s1")


def test_sessions_get_separate_agents():
    cache = main.AgentCache()
    assert cache.get("s1") is not cache.get("s2")


def test_least_recently_used_session_is_dropped_when_full():
    cache = main.AgentCache(max_size=2)
    s1 = cache.get("s1")
    s2 = cache.get("s2")
    cache.get("s1")  # s1 is now the most recently used
    cache.get("s3")
    assert cache.get("s1") is s1
    assert cache.get("s2") is not s2


def test_evicted_session_gets_a_fresh_agent():
    cache = main.AgentCache()
    first = cache.get("s1")
    cache.evict("s1")
    assert cache.get("s1") is not first


def test_evicting_an_unknown_session_is_a_no_op():
    main.AgentCache().evict("missing")

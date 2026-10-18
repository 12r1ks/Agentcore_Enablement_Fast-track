import json
import logging
from types import SimpleNamespace

import pytest

from memory import session

STRATEGIES = [
    {"type": "SEMANTIC", "strategyId": "Facts-111"},
    {"type": "USER_PREFERENCE", "strategyId": "UserPreference-222"},
]


def preference_record(preference: str, created_at: str) -> dict:
    """Shaped like a USER_PREFERENCE record from list_memory_records."""
    text = json.dumps({"context": "earlier chat", "preference": preference, "categories": []})
    return {"content": {"text": text}, "createdAt": created_at}


class FakeMemory:
    """Stands in for both boto3 clients: the control plane (get_memory) and data plane (list_memory_records)."""

    def __init__(self, records=(), error=None):
        self.records = list(records)
        self.error = error
        self.get_memory_calls = 0
        self.namespaces = []

    def get_memory(self, memoryId):
        self.get_memory_calls += 1
        return {"memory": {"id": memoryId, "strategies": STRATEGIES}}

    def list_memory_records(self, memoryId, namespace, maxResults):
        if self.error:
            raise self.error
        self.namespaces.append(namespace)
        return {"memoryRecordSummaries": self.records}


@pytest.fixture
def memory(monkeypatch):
    fake = FakeMemory()
    monkeypatch.setattr(session, "MEMORY_ID", "mem-123")
    monkeypatch.setattr(session.boto3, "client", lambda *a, **kw: fake)
    monkeypatch.setattr(session, "AgentCoreMemorySessionManager", lambda config, region: SimpleNamespace(config=config))
    session._preference_strategy_id.cache_clear()
    yield fake
    session._preference_strategy_id.cache_clear()


def test_memory_is_off_without_a_memory_id(monkeypatch):
    monkeypatch.setattr(session, "MEMORY_ID", None)
    assert session.get_memory_session_manager("session-1", "CUST-001") is None
    assert session.load_preferences("CUST-001") == []


def test_session_manager_stores_events_for_this_session_and_customer(memory):
    manager = session.get_memory_session_manager("session-1", "CUST-001")
    assert (manager.config.memory_id, manager.config.session_id, manager.config.actor_id) == ("mem-123", "session-1", "CUST-001")
    assert manager.config.retrieval_config is None  # no per-message search; preferences are loaded up front


def test_preferences_are_read_from_the_customers_namespace(memory):
    session.load_preferences("CUST-001")
    assert memory.namespaces == ["/strategies/UserPreference-222/actors/CUST-001/"]


def test_preferences_are_returned_newest_first(memory):
    memory.records = [
        preference_record("Prefers email", "2026-10-01T10:00:00Z"),
        preference_record("Call me by my first name", "2026-10-18T10:00:00Z"),
    ]
    assert session.load_preferences("CUST-001") == ["Call me by my first name", "Prefers email"]


def test_number_of_preferences_is_capped(memory):
    memory.records = [preference_record(f"Preference {i}", f"2026-10-{i:02d}T00:00:00Z") for i in range(1, 31)]
    preferences = session.load_preferences("CUST-001")
    assert len(preferences) == session.MAX_PREFERENCES
    assert preferences[0] == "Preference 30"


def test_record_that_is_not_json_is_used_as_plain_text(memory):
    memory.records = [{"content": {"text": "Prefers German"}, "createdAt": "2026-10-18T10:00:00Z"}]
    assert session.load_preferences("CUST-001") == ["Prefers German"]


def test_strategy_id_is_looked_up_once_per_process(memory):
    session.load_preferences("CUST-001")
    session.load_preferences("CUST-002")
    assert memory.get_memory_calls == 1


def test_unreachable_memory_starts_the_session_without_preferences(memory, caplog):
    memory.error = ConnectionError("memory endpoint down")
    with caplog.at_level(logging.WARNING):
        assert session.load_preferences("CUST-001") == []
    assert "continuing without them" in caplog.text

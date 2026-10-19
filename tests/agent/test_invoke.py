import asyncio
from types import SimpleNamespace

import pytest
from strands.types.exceptions import ConcurrencyException

import main

TEXT_EVENT = {"event": {"contentBlockDelta": {"delta": {"text": "Hello"}}}}


class FakeAgent:
    def __init__(self, events=(), error=None):
        self.events = events
        self.error = error
        self.prompts = []

    async def stream_async(self, prompt):
        self.prompts.append(prompt)
        for event in self.events:
            yield event
        if self.error:
            raise self.error


class FakeAgentCache:
    def __init__(self, agent):
        self.agent = agent
        self.evicted = []

    def get(self, session_id):
        return self.agent

    def evict(self, session_id):
        self.evicted.append(session_id)


@pytest.fixture
def use_agent(monkeypatch):
    # load_model signs a token with local AWS credentials; tests must not need them.
    monkeypatch.setattr(main, "load_model", lambda: "fresh-model")

    def install(agent):
        cache = FakeAgentCache(agent)
        monkeypatch.setattr(main, "agents", cache)
        return cache
    return install


def invoke(payload) -> list:
    async def collect():
        return [event async for event in main.invoke(payload, SimpleNamespace(session_id="session-1"))]
    return asyncio.run(collect())


def test_prompt_is_streamed_back_from_the_agent(use_agent):
    agent = FakeAgent(events=[TEXT_EVENT])
    use_agent(agent)
    assert invoke({"prompt": "Where is my order?"}) == [TEXT_EVENT]
    assert agent.prompts == ["Where is my order?"]


def test_each_turn_gets_a_fresh_model(use_agent):
    agent = FakeAgent(events=[TEXT_EVENT])
    use_agent(agent)
    invoke({"prompt": "hi"})
    assert agent.model == "fresh-model"


def test_only_model_stream_events_are_forwarded(use_agent):
    empty_block_start = {"event": {"contentBlockStart": {"start": {}}}}
    use_agent(FakeAgent(events=[{"data": "internal"}, empty_block_start, "not a dict", TEXT_EVENT]))
    assert invoke({"prompt": "hi"}) == [TEXT_EVENT]


@pytest.mark.parametrize("payload", ["not an object", {"prompt": 42}, {"messages": "not a list"}])
def test_invalid_request_is_rejected_before_the_agent_runs(use_agent, payload):
    agent = FakeAgent()
    use_agent(agent)
    [event] = invoke(payload)
    assert event["error"]["code"] == "INVALID_REQUEST"
    assert agent.prompts == []


def test_message_while_the_previous_one_is_running(use_agent):
    cache = use_agent(FakeAgent(error=ConcurrencyException("busy")))
    [event] = invoke({"prompt": "hi"})
    assert event["error"]["code"] == "SESSION_BUSY"
    assert cache.evicted == []


def test_unexpected_failure_is_hidden_from_the_customer_and_resets_the_session(use_agent, caplog):
    cache = use_agent(FakeAgent(events=[TEXT_EVENT], error=RuntimeError("gateway exploded")))
    events = invoke({"prompt": "hi"})
    assert events[0] == TEXT_EVENT
    assert events[1]["error"]["code"] == "INTERNAL_ERROR"
    assert "gateway exploded" not in str(events[1])
    assert "gateway exploded" in caplog.text  # full detail goes to the logs instead
    assert cache.evicted == ["session-1"]

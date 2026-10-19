import asyncio
import json

import pytest
from strands import Agent, tool
from strands.models import Model

from hooks import tool_retry
from hooks.tool_retry import ToolRetryHook, is_retryable

RETRYABLE = json.dumps({"error": {"code": "ORDER_CHANGED", "message": "Retry the refund.", "retryable": True}})
NOT_RETRYABLE = json.dumps({"error": {"code": "INVALID_PARAMETER", "message": "Bad amount.", "retryable": False}})
OK = json.dumps({"refund": {"refund_id": "REF-1"}})


class OneToolThenAnswerModel(Model):
    """Calls the `refund` tool once, then answers with the tool's final result."""

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        results = [block["toolResult"] for block in messages[-1]["content"] if "toolResult" in block]
        yield {"messageStart": {"role": "assistant"}}
        if results:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": results[0]["content"][0]["text"]}}}
        else:
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "call-1", "name": "refund"}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": "{}"}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn" if results else "tool_use"}}


@pytest.fixture
def delays(monkeypatch):
    """The backoff delays the hook waited for, without actually waiting."""
    waited = []

    async def no_wait(seconds):
        waited.append(seconds)

    monkeypatch.setattr(tool_retry.asyncio, "sleep", no_wait)
    return waited


def run_with_tool_results(*results) -> tuple[str, int]:
    """Runs one turn in which the tool returns the given results in order; returns the reply and the tool's run count."""
    remaining = list(results)
    runs = []

    @tool
    def refund() -> str:
        """Refund."""
        runs.append(1)
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    agent = Agent(model=OneToolThenAnswerModel(), tools=[refund], hooks=[ToolRetryHook()], callback_handler=None)
    return str(asyncio.run(agent.invoke_async("refund please"))).strip(), len(runs)


def test_retryable_error_is_retried_until_it_succeeds(delays):
    reply, runs = run_with_tool_results(RETRYABLE, OK)
    assert runs == 2
    assert reply == OK  # the model only ever sees the successful result
    assert len(delays) == 1 and 0.4 <= delays[0] <= 0.6


def test_retries_back_off_exponentially_and_stop_at_the_limit(delays):
    reply, runs = run_with_tool_results(RETRYABLE)
    assert runs == 3  # the first call and two retries
    assert reply == RETRYABLE  # after the last retry the error goes to the model
    assert 0.4 <= delays[0] <= 0.6 and 0.8 <= delays[1] <= 1.2


def test_errors_that_are_not_retryable_go_straight_to_the_model(delays):
    reply, runs = run_with_tool_results(NOT_RETRYABLE)
    assert runs == 1
    assert reply == NOT_RETRYABLE
    assert delays == []


@pytest.mark.parametrize("text", [OK, NOT_RETRYABLE, "plain text", "[1, 2]", ""])
def test_only_errors_marked_retryable_count(text):
    assert not is_retryable({"content": [{"text": text}]})
    assert is_retryable({"content": [{"text": RETRYABLE}]})

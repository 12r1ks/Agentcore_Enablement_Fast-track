import asyncio

import pytest
from strands import Agent, tool
from strands.models import Model
from strands.types.exceptions import EventLoopException

from hooks.loop_guard import TOOL_LIMIT_MESSAGE, LoopGuardHook


class LoopingModel(Model):
    """Asks for the same tool on every call. With obeys_limit, it answers once told the tool limit was reached."""

    def __init__(self, obeys_limit: bool):
        self.obeys_limit = obeys_limit
        self.calls = 0

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.calls += 1
        told_to_stop = any(TOOL_LIMIT_MESSAGE in str(block) for message in messages for block in message["content"])
        yield {"messageStart": {"role": "assistant"}}
        if self.obeys_limit and told_to_stop:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": "Here is what I found."}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
            return
        yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"call-{self.calls}", "name": "ping"}}}}
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": "{}"}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}


class OneToolThenAnswerModel(LoopingModel):
    """A well-behaved turn: one tool call, then an answer."""

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        if not any("toolResult" in block for block in messages[-1]["content"]):
            async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
                yield event
            return
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": "Done."}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}


@pytest.fixture
def ping_runs():
    return []


def make_agent(model, ping_runs):
    @tool
    def ping() -> str:
        """Ping."""
        ping_runs.append(1)
        return "pong"

    return Agent(model=model, tools=[ping], hooks=[LoopGuardHook(max_tool_calls=3, max_calls_after_limit=2)],
                 callback_handler=None)


def run_turn(agent, prompt="go") -> str:
    """Runs one turn and returns the text streamed to the client."""
    async def collect():
        text = []
        async for event in agent.stream_async(prompt):
            if isinstance(event, dict) and "event" in event:
                text.append(event["event"].get("contentBlockDelta", {}).get("delta", {}).get("text", ""))
        return "".join(text)

    return asyncio.run(collect())


def test_soft_limit_cancels_tools_and_lets_the_model_answer(ping_runs):
    model = LoopingModel(obeys_limit=True)
    reply = run_turn(make_agent(model, ping_runs))
    assert reply == "Here is what I found."
    assert len(ping_runs) == 3  # the 4th call was cancelled before reaching the tool
    assert model.calls == 5     # 3 tool rounds, the cancelled round, then the answer


def test_hard_limit_aborts_a_model_that_keeps_calling_tools(ping_runs):
    model = LoopingModel(obeys_limit=False)
    with pytest.raises(EventLoopException, match="more calls after the tool limit"):
        run_turn(make_agent(model, ping_runs))
    assert len(ping_runs) == 3
    assert model.calls == 6     # 3 tool rounds + 2 allowed after the limit, aborted before the next


def test_limits_reset_on_each_turn(ping_runs):
    agent = make_agent(LoopingModel(obeys_limit=True), ping_runs)
    run_turn(agent)  # uses up the tool limit
    agent.model = OneToolThenAnswerModel(obeys_limit=False)
    assert run_turn(agent, "next question") == "Done."
    assert len(ping_runs) == 4  # the new turn's tool call ran instead of being cancelled

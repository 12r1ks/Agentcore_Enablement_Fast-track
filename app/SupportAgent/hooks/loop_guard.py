import logging

from strands.hooks import BeforeInvocationEvent, BeforeModelCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry

log = logging.getLogger(__name__)

TOOL_LIMIT_MESSAGE = (
    "Tool limit for this request reached. Do not call more tools; "
    "answer the customer with the information you already have."
)


class LoopLimitExceeded(Exception):
    """The model kept calling tools after being told to stop."""


class LoopGuardHook(HookProvider):
    """Stops a model that keeps calling tools within one turn, in two levels:

    1. Soft: past max_tool_calls, tools are cancelled and the model is told to answer with what it has,
       so it can still reply to the customer normally.
    2. Hard: if the model keeps going for more than max_calls_after_limit model calls, the turn is
       aborted with LoopLimitExceeded, which invoke() logs and reports as an error.
    """

    def __init__(self, max_tool_calls: int = 10, max_calls_after_limit: int = 3):
        self._max_tool_calls = max_tool_calls
        self._max_calls_after_limit = max_calls_after_limit
        self._tool_calls = 0
        self._calls_after_limit = 0

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeInvocationEvent, self._reset)
        registry.add_callback(BeforeToolCallEvent, self._limit_tools)
        registry.add_callback(BeforeModelCallEvent, self._stop_if_still_looping)

    def _reset(self, event: BeforeInvocationEvent) -> None:
        self._tool_calls = 0
        self._calls_after_limit = 0

    def _limit_tools(self, event: BeforeToolCallEvent) -> None:
        self._tool_calls += 1
        if self._tool_calls > self._max_tool_calls:
            if self._tool_calls == self._max_tool_calls + 1:
                log.warning("Tool limit of %d reached in one turn (possible LLM loop)", self._max_tool_calls)
            event.cancel_tool = TOOL_LIMIT_MESSAGE

    def _stop_if_still_looping(self, event: BeforeModelCallEvent) -> None:
        if self._tool_calls <= self._max_tool_calls:
            return
        self._calls_after_limit += 1
        if self._calls_after_limit > self._max_calls_after_limit:
            raise LoopLimitExceeded(
                f"Model made {self._max_calls_after_limit} more calls after the tool limit of "
                f"{self._max_tool_calls} was reached"
            )

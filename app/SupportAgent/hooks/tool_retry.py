import asyncio
import json
import logging
import random

from strands.hooks import AfterToolCallEvent, BeforeInvocationEvent, HookProvider, HookRegistry

log = logging.getLogger(__name__)


def is_retryable(result: dict) -> bool:
    """Tools report failures as {"error": {..., "retryable": bool}} in a text block (tools/support_tools/errors.py)."""
    for block in result.get("content", []):
        try:
            error = json.loads(block.get("text", "")).get("error")
        except (ValueError, AttributeError):
            continue
        if isinstance(error, dict) and error.get("retryable") is True:
            return True
    return False


class ToolRetryHook(HookProvider):
    """Retries a tool call whose result is an error marked retryable, with exponential backoff and jitter
    (about base_delay, then twice that, ...). Other errors, such as invalid parameters or policy denials, go
    straight back to the model."""

    def __init__(self, max_retries: int = 2, base_delay: float = 0.5):
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._retries: dict[str, int] = {}

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeInvocationEvent, self._reset)
        registry.add_callback(AfterToolCallEvent, self._retry_if_retryable)

    def _reset(self, event: BeforeInvocationEvent) -> None:
        self._retries.clear()

    async def _retry_if_retryable(self, event: AfterToolCallEvent) -> None:
        if not is_retryable(event.result):
            return
        tool_use_id, tool = event.tool_use["toolUseId"], event.tool_use["name"]
        retries = self._retries.get(tool_use_id, 0)
        if retries >= self._max_retries:
            log.warning("Giving up on %s after %d retries", tool, retries)
            return
        self._retries[tool_use_id] = retries + 1
        delay = self._base_delay * 2**retries * random.uniform(0.8, 1.2)
        log.warning("Retrying %s after a retryable error (retry %d of %d, in %.1f s)", tool, retries + 1, self._max_retries, delay)
        await asyncio.sleep(delay)
        event.retry = True

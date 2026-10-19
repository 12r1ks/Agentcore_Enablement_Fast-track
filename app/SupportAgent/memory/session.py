import json
import logging
import os
from functools import cache

import boto3
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

# Injected by AgentCore Runtime for the "UserPreference" memory in agentcore.json; unset when running locally.
MEMORY_ID = os.getenv("MEMORY_USERPREFERENCE_ID")
REGION = os.getenv("AWS_REGION")

# Must match the namespace of the USER_PREFERENCE strategy in agentcore.json.
PREFERENCES_NAMESPACE = "/strategies/{memoryStrategyId}/actors/{actorId}/"

# Preferences go into every prompt of the session, so their number is capped to keep the context small.
# AgentCore consolidates similar records on extraction, so real customers stay well below this.
MAX_PREFERENCES = 20

log = logging.getLogger(__name__)


@cache
def _preference_strategy_id() -> str:
    """The strategy ID is generated at deploy time, so it is looked up once instead of hardcoded."""
    memory = boto3.client("bedrock-agentcore-control", region_name=REGION).get_memory(memoryId=MEMORY_ID)["memory"]
    return next(s["strategyId"] for s in memory["strategies"] if s["type"] == "USER_PREFERENCE")


def _preference_text(record: dict) -> str:
    """USER_PREFERENCE records hold JSON like {"preference": ..., "context": ...}; only the preference is needed."""
    text = record["content"]["text"]
    try:
        return json.loads(text)["preference"]
    except (ValueError, KeyError, TypeError):
        return text


def load_preferences(actor_id: str) -> list[str]:
    """Long-term memory: the customer's saved preferences, newest first, read once when a session starts.

    They apply to every message, so they are listed rather than searched per message by relevance.
    Memory is optional: if it can't be reached, the session starts without them."""
    if not MEMORY_ID:
        return []
    try:
        namespace = PREFERENCES_NAMESPACE.format(memoryStrategyId=_preference_strategy_id(), actorId=actor_id)
        response = boto3.client("bedrock-agentcore", region_name=REGION).list_memory_records(
            memoryId=MEMORY_ID, namespace=namespace, maxResults=100
        )
    except Exception:
        log.warning("Could not load preferences, continuing without them", exc_info=True)
        return []
    records = sorted(response["memoryRecordSummaries"], key=lambda r: r["createdAt"], reverse=True)
    return [_preference_text(record) for record in records[:MAX_PREFERENCES]]


def get_memory_session_manager(session_id: str, actor_id: str) -> AgentCoreMemorySessionManager | None:
    """Short-term memory: the session's messages are stored as events and restored on a new Agent.
    AgentCore extracts long-term preferences from these events in the background (see load_preferences).
    Memory is optional: if it can't be reached, the agent runs without it instead of failing."""
    if not MEMORY_ID:
        return None

    try:
        return AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id,
            ),
            REGION,
        )
    except Exception:
        log.warning("Memory unavailable, continuing without it", exc_info=True)
        return None

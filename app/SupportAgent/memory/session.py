import os
import logging
from functools import cache
from typing import Optional

import boto3
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

# Injected by AgentCore Runtime for the "UserPreference" memory in agentcore.json; unset when running locally.
MEMORY_ID = os.getenv("MEMORY_USERPREFERENCE_ID")
REGION = os.getenv("AWS_REGION")

# Must match the namespace of the USER_PREFERENCE strategy; {memoryStrategyId} is filled from RetrievalConfig.strategy_id.
PREFERENCES_NAMESPACE = "/strategies/{memoryStrategyId}/actors/{actorId}/"

log = logging.getLogger(__name__)

@cache
def _preference_strategy_id() -> str:
    """The strategy ID is generated at deploy time, so it is looked up once instead of hardcoded."""
    memory = boto3.client("bedrock-agentcore-control", region_name=REGION).get_memory(memoryId=MEMORY_ID)["memory"]
    return next(s["strategyId"] for s in memory["strategies"] if s["type"] == "USER_PREFERENCE")


def get_memory_session_manager(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    """Short-term memory: the session's messages are stored as events and restored on a new Agent.
    Long-term memory: preferences extracted for actor_id are added to the context on each turn.
    Memory is optional: if it can't be reached, the agent runs without it instead of failing."""
    if not MEMORY_ID:
        return None

    try:
        retrieval_config = {
            PREFERENCES_NAMESPACE: RetrievalConfig(top_k=3, relevance_score=0.5, strategy_id=_preference_strategy_id()),
        }

        return AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id,
                retrieval_config=retrieval_config,
            ),
            REGION,
        )
    except Exception:
        log.warning("Memory unavailable, continuing without it", exc_info=True)
        return None

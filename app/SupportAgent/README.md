# SupportAgent

The Strands agent that runs on AgentCore Runtime. See the root README for the whole project.

| Path | Purpose |
| --- | --- |
| `main.py` | Entrypoint: request validation, one cached Agent per session, error responses |
| `model/load.py` | Gemma on Bedrock Mantle, authenticated with a short-lived Bedrock token |
| `mcp_client/client.py` | MCP client for the Gateway tools, signed with SigV4 |
| `memory/session.py` | Short-term session events and long-term customer preferences in AgentCore Memory |
| `hooks/customer_context.py` | Adds the signed-in customer's ID to customer-scoped tool calls |
| `hooks/loop_guard.py` | Stops a model that keeps calling tools within one turn |

Environment variables set by AgentCore Runtime:

| Variable | Description |
| --- | --- |
| `AGENTCORE_GATEWAY_SUPPORT_GATEWAY_URL` | Gateway MCP endpoint (required) |
| `MEMORY_USERPREFERENCE_ID` | Memory ID; without it the agent runs without memory |
| `AWS_REGION` | Region for the model, Memory and request signing |

Run locally with `agentcore dev` from the project root. Tests live in the root `tests/` folder (`uv run pytest`).

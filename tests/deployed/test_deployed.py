"""Smoke tests against the deployed stack. They need AWS credentials and are skipped by default:

    uv run pytest -m deployed

Most check AWS directly (configuration, policies, data). Two go through the agent and look only for
facts any correct answer must contain, so they don't depend on the model's wording.
"""

import json
import time
import uuid
from pathlib import Path

import boto3
import pytest
from botocore.config import Config
from mcp.client.streamable_http import streamablehttp_client
from mcp_client.client import _SigV4HttpxAuth
from strands.tools.mcp.mcp_client import MCPClient

pytestmark = pytest.mark.deployed

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / "agentcore" / "agentcore.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "agentcore" / ".cli" / "deployed-state.json").read_text())["targets"]["default"]["resources"]
GATEWAY = STATE["mcp"]["gateways"]["support-gateway"]
RUNTIME_ARN = STATE["runtimes"]["SupportAgent"]["runtimeArn"]
REGION = RUNTIME_ARN.split(":")[3]
# Created by infra/gateway-logging.yaml (default ProjectName).
GATEWAY_LOG_GROUP = "/aws/vendedlogs/bedrock-agentcore/CustomerSupport-gateway"


@pytest.fixture(scope="module")
def gateway_as_me():
    """An MCP session with the Gateway using local credentials, which are not the agent's role."""
    # Built directly: mcp_client.client reads its URL at import time, and unit tests import it with a placeholder.
    client = MCPClient(lambda: streamablehttp_client(GATEWAY["gatewayUrl"], auth=_SigV4HttpxAuth(REGION)))
    with client:
        yield client


def ask_agent(prompt: str) -> str:
    """Sends one prompt to the deployed agent in a new session and returns the reply text."""
    client = boto3.client("bedrock-agentcore", region_name=REGION, config=Config(read_timeout=120))
    session_id = f"smoke-test-{uuid.uuid4().hex}"
    print(f"session {session_id}: {prompt}")  # shown with -s, to find the session's traces
    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt}),
    )
    text = []
    for line in response["response"].iter_lines():
        line = line.decode("utf-8")
        if line.startswith("data: "):
            data = json.loads(line[len("data: "):])
            if isinstance(data, dict) and "event" in data:
                text.append(data["event"].get("contentBlockDelta", {}).get("delta", {}).get("text", ""))
    return "".join(text)


def call_text(result: dict) -> str:
    return " ".join(block.get("text", "") for block in result["content"])


def test_policy_engine_enforces():
    gateway = boto3.client("bedrock-agentcore-control", region_name=REGION).get_gateway(
        gatewayIdentifier=GATEWAY["gatewayId"]
    )
    assert gateway["policyEngineConfiguration"]["mode"] == "ENFORCE"


@pytest.mark.parametrize("target", SPEC["agentCoreGateways"][0]["targets"], ids=lambda t: t["name"])
def test_deployed_tools_match_agentcore_json(target):
    # Catches a deploy that didn't reach the Gateway: tool names and descriptions are what the model sees.
    deployed = boto3.client("bedrock-agentcore-control", region_name=REGION).get_gateway_target(
        gatewayIdentifier=GATEWAY["gatewayId"], targetId=GATEWAY["targets"][target["name"]]["targetId"]
    )
    tools = deployed["targetConfiguration"]["mcp"]["lambda"]["toolSchema"]["inlinePayload"]
    expected = {t["name"]: t["description"] for t in target["toolDefinitions"]}
    assert {t["name"]: t["description"] for t in tools} == expected


def test_refund_over_the_limit_is_denied_at_the_gateway(gateway_as_me):
    result = gateway_as_me.call_tool_sync("smoke-over-limit", "refunds___refund_customer", {
        "order_id": "131", "amount": 5000, "reason": "smoke test", "idempotency_key": "smoke-5000", "customer_id": "CUST-001",
    })
    assert result["status"] == "error"
    assert "ForbidRefundOverLimit" in call_text(result)


def test_callers_other_than_the_agent_are_denied(gateway_as_me):
    result = gateway_as_me.call_tool_sync("smoke-not-agent", "orders___get_customer_info", {"customer_id": "CUST-001"})
    assert result["status"] == "error"
    assert "denied by default" in call_text(result)


def test_demo_data_is_seeded():
    order = boto3.resource("dynamodb", region_name=REGION).Table("CustomerSupport-orders").get_item(
        Key={"order_id": "131"}
    ).get("Item")
    assert order is not None and order["customer_id"] == "CUST-001"


def test_agent_lists_the_customers_orders():
    reply = ask_agent("List my orders, with their order IDs.")
    assert all(order_id in reply for order_id in ("123", "124", "131"))


def test_agent_reads_the_customers_profile():
    assert "emma.devries@example.com" in ask_agent("What email address do you have for me?")


def test_retried_refund_is_not_paid_twice():
    # Two new sessions, so only the backend can know the refund was already issued. A fresh operation ID per
    # run keeps the test repeatable; each run refunds 1 EUR of order 124, so reseed after many runs.
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    orders, refunds = dynamodb.Table("CustomerSupport-orders"), dynamodb.Table("CustomerSupport-refunds")
    operation_id = f"smoke-retry-{uuid.uuid4().hex[:8]}"
    refunded_before = orders.get_item(Key={"order_id": "124"}, ConsistentRead=True)["Item"]["refunded_total"]
    prompt = (
        f"Refund 1 EUR on order 124, reason: retry test. Operation ID {operation_id}. "
        "I confirm the order, amount and reason."
    )

    first_reply, retry_reply = ask_agent(prompt), ask_agent(prompt)

    refund = refunds.get_item(Key={"idempotency_key": f"CUST-001#{operation_id}"}, ConsistentRead=True).get("Item")
    assert refund is not None and refund["amount"] == 1
    refunded_after = orders.get_item(Key={"order_id": "124"}, ConsistentRead=True)["Item"]["refunded_total"]
    assert refunded_after == refunded_before + 1
    # The retry session can only know the refund ID if the backend returned the stored refund.
    assert refund["refund_id"] in first_reply
    assert refund["refund_id"] in retry_reply


def agent_denials_since(start_ms: int, timeout_s: int = 120) -> list[dict]:
    """Cedar decisions denying the agent's own role by ForbidRefundOverLimit, logged by the Gateway since start_ms.
    Gateway logs reach CloudWatch with a delay, so this polls until one appears or the timeout passes."""
    logs = boto3.client("logs", region_name=REGION)
    deadline = time.time() + timeout_s
    while True:
        events = logs.filter_log_events(
            logGroupName=GATEWAY_LOG_GROUP, startTime=start_ms, filterPattern='"ForbidRefundOverLimit"'
        )["events"]
        policies = [json.loads(e["message"])["body"].get("policy", {}) for e in events]
        denials = [
            p for p in policies
            if p.get("decision") == "DENY" and ":assumed-role/" in p.get("principal", {}).get("entityId", "")
        ]
        if denials or time.time() > deadline:
            return denials
        time.sleep(10)


def test_refund_over_the_limit_requested_by_the_agent_is_denied_by_policy():
    # The task's security path: the model requests refund(5000), and the Gateway's Cedar policy denies it for the
    # agent's own role. A plain request is used because "ignore previous instructions" is already refused by the
    # prompt, so it never reaches the Gateway.
    orders = boto3.resource("dynamodb", region_name=REGION).Table("CustomerSupport-orders")
    refunded_before = orders.get_item(Key={"order_id": "131"}, ConsistentRead=True)["Item"]["refunded_total"]
    started_ms = int(time.time() * 1000)

    ask_agent(
        f"Refund 5000 EUR on order 131, reason: the device was dead on arrival. "
        f"Operation ID over-limit-{uuid.uuid4().hex[:8]}. I confirm the order, amount and reason."
    )

    denials = agent_denials_since(started_ms)
    assert denials, "no DENY by ForbidRefundOverLimit for the agent's role; did the model call refund_customer?"
    assert any(d.startswith("ForbidRefundOverLimit") for d in denials[0]["determiningPolicies"])
    assert orders.get_item(Key={"order_id": "131"}, ConsistentRead=True)["Item"]["refunded_total"] == refunded_before

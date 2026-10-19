"""Lambda entry point. The AgentCore Gateway invokes it with the tool arguments as the event."""

import json
import logging
import time
from decimal import Decimal

from .company_info import get_company_policy
from .errors import ToolError
from .orders import get_customer_info, get_orders
from .refunds import refund_customer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# The Gateway passes "<target name>___<tool name>" in the Lambda client context.
_TOOL_NAME_KEY = "bedrockAgentCoreToolName"
_TARGET_DELIMITER = "___"

TOOLS = {
    "get_company_policy": get_company_policy,
    "get_orders": get_orders,
    "get_customer_info": get_customer_info,
    "refund_customer": refund_customer,
}


# Demo only: order IDs that make any tool fail on purpose, so the failure scenarios can be traced.
# No real order uses them. 901 outlives the 10 s Lambda timeout; 902 crashes the Lambda.
TIMEOUT_ORDER_ID = "901"
CRASH_ORDER_ID = "902"
_TIMEOUT_SLEEP_SECONDS = 15


def _simulate_failure(args: dict) -> None:
    order_id = args.get("order_id")
    if order_id == TIMEOUT_ORDER_ID:
        logger.warning(json.dumps({"event": "simulated_failure", "kind": "timeout"}))
        time.sleep(_TIMEOUT_SLEEP_SECONDS)
    elif order_id == CRASH_ORDER_ID:
        logger.warning(json.dumps({"event": "simulated_failure", "kind": "crash"}))
        raise RuntimeError("Simulated backend crash")


def _tool_name(context) -> str:
    custom = getattr(getattr(context, "client_context", None), "custom", None) or {}
    return custom.get(_TOOL_NAME_KEY, "").split(_TARGET_DELIMITER, 1)[-1]


def _json_safe(value):
    """DynamoDB returns numbers as Decimal, which the Lambda runtime cannot serialize."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def lambda_handler(event, context) -> dict:
    name = _tool_name(context)
    args = event if isinstance(event, dict) else {}
    _simulate_failure(args)
    try:
        tool = TOOLS.get(name)
        if tool is None:
            raise ToolError("UNKNOWN_TOOL", f"Unknown tool '{name}'.", details={"tools": sorted(TOOLS)})
        result = tool(args)
        outcome = "ok"
    except ToolError as error:
        result = {"error": error.to_dict()}
        outcome = error.code
    # Log argument names only, never values, to keep customer data out of the logs.
    logger.info(json.dumps({"event": "tool_call", "tool": name, "outcome": outcome, "argument_names": sorted(args)}))
    return _json_safe(result)

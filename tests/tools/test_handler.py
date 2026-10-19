from types import SimpleNamespace

import pytest

from support_tools import handler
from support_tools.handler import lambda_handler


def context(tool_name: str):
    return SimpleNamespace(client_context=SimpleNamespace(custom={"bedrockAgentCoreToolName": tool_name}))


def test_routes_gateway_tool_name_to_tool():
    result = lambda_handler({"topic": "returns"}, context("company-info___get_company_policy"))
    assert result["title"] == "Returns Policy"


def test_tool_error_is_returned_not_raised():
    result = lambda_handler({"topic": "pricing"}, context("company-info___get_company_policy"))
    assert result["error"]["code"] == "INVALID_PARAMETER"


def test_unknown_tool():
    result = lambda_handler({}, context("company-info___delete_everything"))
    assert result["error"]["code"] == "UNKNOWN_TOOL"


def test_decimal_values_are_returned_as_json_numbers(db):
    result = lambda_handler({"order_id": "123", "customer_id": "CUST-001"}, context("orders___get_order"))
    assert result["order"]["total"] == 163.99
    assert result["order"]["refunded_total"] == 0
    assert isinstance(result["order"]["refunded_total"], int)


def test_timeout_order_sleeps_past_the_lambda_timeout(db, monkeypatch):
    slept = []
    monkeypatch.setattr(handler.time, "sleep", slept.append)
    lambda_handler({"order_id": "901", "customer_id": "CUST-001"}, context("orders___get_order"))
    assert slept and slept[0] > 10  # the target's timeout in agentcore.json


def test_crash_order_raises_instead_of_returning_a_tool_error(db):
    # Unhandled on purpose: the Lambda reports a function error, like a real backend crash.
    with pytest.raises(RuntimeError):
        lambda_handler({"order_id": "902", "customer_id": "CUST-001"}, context("orders___get_order"))


def test_missing_client_context():
    result = lambda_handler({"topic": "returns"}, SimpleNamespace(client_context=None))
    assert result["error"]["code"] == "UNKNOWN_TOOL"

from types import SimpleNamespace

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
    result = lambda_handler({"order_id": "123"}, context("orders___get_order_status"))
    assert result["total"] == 163.99
    assert result["refunded_total"] == 0
    assert isinstance(result["refunded_total"], int)


def test_missing_client_context():
    result = lambda_handler({"topic": "returns"}, SimpleNamespace(client_context=None))
    assert result["error"]["code"] == "UNKNOWN_TOOL"

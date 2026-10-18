import pytest

from support_tools.errors import ToolError
from support_tools.orders import get_customer_info, get_orders

# Added to every call by the agent's CustomerContextHook, never by the model.
CALLER = {"customer_id": "CUST-001"}


def error_code(tool, args) -> str:
    with pytest.raises(ToolError) as raised:
        tool(args)
    return raised.value.code


@pytest.mark.parametrize("args", [CALLER, {**CALLER, "order_id": ""}])
def test_without_order_id_lists_own_orders_newest_first(db, args):
    orders = get_orders(args)["orders"]
    assert [o["order_id"] for o in orders] == ["123", "124"]
    assert orders[0] == {
        "order_id": "123",
        "status": "DELAYED",
        "placed_at": "2026-10-05",
        "total": db.orders["123"]["total"],
        "currency": "EUR",
        "items": ["Lumora Thermo Smart Thermostat"],
    }


def test_customer_without_orders_gets_empty_list(db):
    assert get_orders({"customer_id": "CUST-003"}) == {"orders": []}


def test_with_order_id_returns_full_order(db):
    order = get_orders({**CALLER, "order_id": " 123 "})["order"]
    assert order["status"] == "DELAYED"
    assert order["refunds"] == []


def test_other_customers_order_is_reported_as_not_found(db):
    assert error_code(get_orders, {**CALLER, "order_id": "125"}) == "ORDER_NOT_FOUND"


def test_unknown_order(db):
    assert error_code(get_orders, {**CALLER, "order_id": "999"}) == "ORDER_NOT_FOUND"


@pytest.mark.parametrize("order_id", [123, "x" * 65])
def test_invalid_order_id(db, order_id):
    assert error_code(get_orders, {**CALLER, "order_id": order_id}) == "INVALID_PARAMETER"


def test_get_customer_info_returns_callers_profile(db):
    assert get_customer_info(CALLER)["name"] == "Emma de Vries"


def test_unknown_customer(db):
    assert error_code(get_customer_info, {"customer_id": "CUST-999"}) == "CUSTOMER_NOT_FOUND"


@pytest.mark.parametrize("tool", [get_orders, get_customer_info])
@pytest.mark.parametrize("args", [{}, {"customer_id": ""}, {"customer_id": 1}])
def test_missing_customer_context_is_rejected(db, tool, args):
    assert error_code(tool, args) == "CUSTOMER_CONTEXT_MISSING"

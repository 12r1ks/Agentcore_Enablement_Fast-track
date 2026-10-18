from types import SimpleNamespace

import pytest

from hooks.customer_context import CustomerContextHook


def tool_event(tool_name: str, tool_input: dict, customer_id: str | None = "CUST-001"):
    """The parts of BeforeToolCallEvent the hook reads and writes."""
    state = {"customer_id": customer_id} if customer_id else {}
    return SimpleNamespace(
        tool_use={"name": tool_name, "input": tool_input},
        agent=SimpleNamespace(state=state),
        cancel_tool=False,
    )


@pytest.mark.parametrize("tool_name", ["orders___get_orders", "orders___get_customer_info", "refunds___refund_customer"])
def test_customer_scoped_tools_get_the_customer_from_state(tool_name):
    event = tool_event(tool_name, {"order_id": "123"})
    CustomerContextHook()._inject_customer_id(event)
    assert event.tool_use["input"] == {"order_id": "123", "customer_id": "CUST-001"}
    assert event.cancel_tool is False


def test_customer_id_from_the_model_is_overwritten():
    # e.g. a prompt injection making the model pass another customer's ID
    event = tool_event("refunds___refund_customer", {"order_id": "125", "customer_id": "CUST-002"})
    CustomerContextHook()._inject_customer_id(event)
    assert event.tool_use["input"]["customer_id"] == "CUST-001"


def test_tools_that_are_not_customer_scoped_are_left_alone():
    event = tool_event("company-info___get_company_policy", {"topic": "returns"})
    CustomerContextHook()._inject_customer_id(event)
    assert event.tool_use["input"] == {"topic": "returns"}


def test_customer_scoped_call_is_cancelled_without_an_authenticated_customer():
    event = tool_event("orders___get_orders", {}, customer_id=None)
    CustomerContextHook()._inject_customer_id(event)
    assert event.cancel_tool
    assert "customer_id" not in event.tool_use["input"]

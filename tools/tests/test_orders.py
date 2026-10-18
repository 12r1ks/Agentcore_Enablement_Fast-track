import pytest

from support_tools.errors import ToolError
from support_tools.orders import get_customer_info, get_order_status


def test_get_order_status_returns_order(db):
    order = get_order_status({"order_id": " 123 "})
    assert order["status"] == "DELAYED"
    assert order["customer_id"] == "CUST-001"


def test_unknown_order(db):
    with pytest.raises(ToolError) as raised:
        get_order_status({"order_id": "999"})
    assert raised.value.code == "ORDER_NOT_FOUND"
    assert not raised.value.retryable


def test_get_customer_info_returns_customer(db):
    assert get_customer_info({"customer_id": "CUST-001"})["name"] == "Emma de Vries"


def test_unknown_customer(db):
    with pytest.raises(ToolError) as raised:
        get_customer_info({"customer_id": "CUST-999"})
    assert raised.value.code == "CUSTOMER_NOT_FOUND"


@pytest.mark.parametrize("args", [{}, {"order_id": ""}, {"order_id": 123}, {"order_id": "x" * 65}])
def test_invalid_order_id(db, args):
    with pytest.raises(ToolError) as raised:
        get_order_status(args)
    assert raised.value.code == "INVALID_PARAMETER"
